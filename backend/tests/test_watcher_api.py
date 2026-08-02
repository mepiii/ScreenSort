"""Purpose: watcher API behavior tests. Callers: pytest. Deps: FastAPI TestClient, PIL, app factory/config/models. API: test_* cases and fixtures. Side effects: writes temp SQLite/upload/source files."""
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from app.api import watcher
from app.config import AppSettings
from app.main import create_app
from app.models import ClassificationResult


class FakeClassifier:
    def classify(self, image_path: Path):
        return ClassificationResult(category="code", confidence=0.93, tags=["terminal", "error"])


class FakeOcrExtractor:
    def extract(self, image_path: Path) -> str:
        return "watcher OCR text"


def write_png(path: Path) -> None:
    buffer = BytesIO()
    Image.new("RGB", (8, 8), color="black").save(buffer, format="PNG")
    path.write_bytes(buffer.getvalue())


def make_client(tmp_path, settings, ocr_extractor=None, **client_kwargs):
    return TestClient(
        create_app(
            db_path=tmp_path / "screenshots.db",
            upload_dir=tmp_path / "uploads",
            classifier=FakeClassifier(),
            ocr_extractor=ocr_extractor,
            settings=settings,
        ),
        **client_kwargs,
    )


def test_status_returns_config_and_source_exists(tmp_path):
    source_dir = tmp_path / "screenshots"
    organized_dir = tmp_path / "organized"
    source_dir.mkdir()
    client = make_client(
        tmp_path,
        AppSettings(screenshots_dir=source_dir, organized_dir=organized_dir, organize_mode="move"),
    )

    response = client.get("/api/watcher/status")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {
        "screenshots_dir": str(source_dir),
        "organized_dir": str(organized_dir),
        "organize_mode": "move",
        "source_exists": True,
    }


def test_api_key_protects_watcher_routes(tmp_path):
    source_dir = tmp_path / "screenshots"
    source_dir.mkdir()
    client = make_client(tmp_path, AppSettings(screenshots_dir=source_dir, api_key="secret"))

    assert client.get("/api/watcher/status").status_code == 401
    assert client.get("/api/watcher/status", headers={"X-API-Key": "secret"}).status_code == 200
    assert client.post("/api/watcher/scan").status_code == 401


def test_scan_endpoint_ingests_folder(tmp_path):
    source_dir = tmp_path / "screenshots"
    source_dir.mkdir()
    write_png(source_dir / "shot.png")
    client = make_client(tmp_path, AppSettings(screenshots_dir=source_dir))

    response = client.post("/api/watcher/scan")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    assert body["seen"] == 1
    assert body["ingested"] == 1
    assert body["skipped"] == 0
    assert body["failed"] == 0
    assert body["records"][0]["source_path"] == str((source_dir / "shot.png").resolve())


def test_scan_endpoint_accepts_source_folder_override(tmp_path):
    default_dir = tmp_path / "default"
    custom_dir = tmp_path / "custom"
    default_dir.mkdir()
    custom_dir.mkdir()
    write_png(custom_dir / "custom-shot.png")
    client = make_client(tmp_path, AppSettings(screenshots_dir=default_dir))

    response = client.post("/api/watcher/scan", json={"screenshots_dir": str(custom_dir)})

    assert response.status_code == 200
    body = response.json()
    assert body["seen"] == 1
    assert body["records"][0]["source_path"] == str((custom_dir / "custom-shot.png").resolve())


def test_scan_endpoint_passes_ocr_extractor(tmp_path):
    source_dir = tmp_path / "screenshots"
    source_dir.mkdir()
    write_png(source_dir / "shot.png")
    client = make_client(tmp_path, AppSettings(screenshots_dir=source_dir), FakeOcrExtractor())

    response = client.post("/api/watcher/scan")

    assert response.status_code == 200
    assert response.json()["records"][0]["ocr_text"] == "watcher OCR text"


def test_scan_missing_source_returns_400(tmp_path):
    client = make_client(tmp_path, AppSettings(screenshots_dir=tmp_path / "missing"))

    response = client.post("/api/watcher/scan")

    assert response.status_code == 400
    assert response.json()["detail"] == "Screenshot source folder does not exist."


def test_scan_default_string_source_path_returns_400(tmp_path):
    client = make_client(tmp_path, AppSettings())

    response = client.post("/api/watcher/scan")

    assert response.status_code == 400
    assert response.json()["detail"] == "Screenshot source folder does not exist."


def test_scan_internal_missing_file_is_not_remapped_to_source_400(tmp_path, monkeypatch):
    source_dir = tmp_path / "screenshots"
    source_dir.mkdir()

    def fail_scan(*args, **kwargs):
        raise FileNotFoundError("internal file missing")

    monkeypatch.setattr(watcher, "scan_folder_once", fail_scan)
    client = make_client(
        tmp_path,
        AppSettings(screenshots_dir=source_dir),
        raise_server_exceptions=False,
    )

    response = client.post("/api/watcher/scan")

    assert response.status_code == 500
