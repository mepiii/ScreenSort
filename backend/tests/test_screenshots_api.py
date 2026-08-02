"""Purpose: screenshot API behavior tests. Callers: pytest. Deps: FastAPI TestClient, PIL, app factory/models. API: test_* cases and fixtures. Side effects: writes temp SQLite/upload files."""
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.config import AppSettings
from app.main import create_app
from app.models import ClassificationResult


class FakeClassifier:
    def __init__(self, tags=None):
        self.tags = tags or ["terminal", "error"]

    def classify(self, image_path):
        return ClassificationResult(category="code", confidence=0.93, tags=self.tags)


class FailingClassifier:
    def classify(self, image_path):
        raise RuntimeError("classification failed")


class FakeOcrExtractor:
    def __init__(self, text="visible OCR text"):
        self.text = text

    def extract(self, image_path):
        return self.text


class FailingOcrExtractor:
    def extract(self, image_path):
        raise RuntimeError("ocr failed")


def image_bytes(image_format: str = "PNG") -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (8, 8), color="red").save(buffer, format=image_format)
    return buffer.getvalue()


def make_client(tmp_path, classifier=None, ocr_extractor=None, raise_server_exceptions=True, settings=None):
    return TestClient(
        create_app(
            db_path=tmp_path / "screenshots.db",
            upload_dir=tmp_path / "uploads",
            classifier=classifier or FakeClassifier(),
            ocr_extractor=ocr_extractor or FakeOcrExtractor(),
            settings=settings,
        ),
        raise_server_exceptions=raise_server_exceptions,
    )


def upload_png(client: TestClient, filename: str = "shot.png", headers: dict[str, str] | None = None):
    return client.post(
        "/api/screenshots",
        files={"file": (filename, image_bytes(), "image/png")},
        headers=headers,
    )


def test_health_check_returns_ok(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_key_is_optional_by_default(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/api/screenshots")

    assert response.status_code == 200


def test_api_key_protects_screenshot_routes(tmp_path):
    client = make_client(tmp_path, settings=AppSettings(api_key="secret"))

    assert client.get("/api/health").status_code == 200
    assert client.get("/api/screenshots").status_code == 401
    assert client.get("/api/screenshots", headers={"X-API-Key": "secret"}).status_code == 200


def test_api_key_query_parameter_allows_image_requests(tmp_path):
    client = make_client(tmp_path, settings=AppSettings(api_key="secret"))
    record = upload_png(client, headers={"X-API-Key": "secret"}).json()

    blocked = client.get(f"/api/screenshots/{record['id']}/image")
    allowed = client.get(f"/api/screenshots/{record['id']}/image", params={"api_key": "secret"})

    assert blocked.status_code == 401
    assert allowed.status_code == 200


def test_upload_and_list_persist_metadata(tmp_path):
    client = make_client(tmp_path)

    uploaded = upload_png(client)
    listed = client.get("/api/screenshots")

    assert uploaded.status_code == 200
    record = uploaded.json()
    assert record["original_filename"] == "shot.png"
    assert record["category"] == "code"
    assert record["confidence"] == 0.93
    assert record["tags"] == ["terminal", "error"]
    assert record["ingest_method"] == "upload"
    assert record["ocr_text"] == "visible OCR text"
    assert listed.status_code == 200
    assert listed.json() == [record]


def test_upload_rejects_invalid_non_image(tmp_path):
    client = make_client(tmp_path)

    response = client.post(
        "/api/screenshots",
        files={"file": ("bad.png", b"not an image", "image/png")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid image file"


def test_upload_rejects_oversized_file(tmp_path):
    client = make_client(tmp_path, settings=AppSettings(max_upload_bytes=4))

    response = upload_png(client)

    assert response.status_code == 413
    assert response.json()["detail"] == "Upload exceeds size limit."


def test_upload_rejects_image_over_pixel_limit_and_removes_file(tmp_path):
    client = make_client(tmp_path, settings=AppSettings(max_image_pixels=4))

    response = upload_png(client)

    assert response.status_code == 400
    assert response.json()["detail"] == "Image dimensions exceed limit."
    assert list((tmp_path / "uploads").glob("*")) == []


def test_list_supports_query_category_and_tag_filters(tmp_path):
    client = make_client(tmp_path)
    upload_png(client, "terminal-error.png")
    chatter_client = make_client(tmp_path, FakeClassifier(["chatter"]))
    upload_png(chatter_client, "chatter.png")

    assert len(client.get("/api/screenshots", params={"query": "terminal"}).json()) == 1
    assert len(client.get("/api/screenshots", params={"category": "code"}).json()) == 2
    assert len(client.get("/api/screenshots", params={"tag": "error"}).json()) == 1
    assert client.get("/api/screenshots", params={"tag": "chat"}).json() == []
    assert client.get("/api/screenshots", params={"category": "finance"}).json() == []


def test_get_screenshot_and_stream_image(tmp_path):
    client = make_client(tmp_path)
    record = upload_png(client).json()

    metadata = client.get(f"/api/screenshots/{record['id']}")
    image = client.get(f"/api/screenshots/{record['id']}/image")
    missing = client.get("/api/screenshots/9999")

    assert metadata.status_code == 200
    assert metadata.json() == record
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"
    assert image.content.startswith(b"\x89PNG")
    assert missing.status_code == 404


def test_upload_removes_file_when_classifier_fails(tmp_path):
    client = make_client(tmp_path, FailingClassifier(), raise_server_exceptions=False)

    response = upload_png(client)

    assert response.status_code == 500
    assert list((tmp_path / "uploads").glob("*")) == []


def test_upload_removes_file_when_ocr_fails(tmp_path):
    client = make_client(tmp_path, ocr_extractor=FailingOcrExtractor(), raise_server_exceptions=False)

    response = upload_png(client)

    assert response.status_code == 500
    assert list((tmp_path / "uploads").glob("*")) == []


def test_stream_image_returns_404_when_file_removed(tmp_path):
    client = make_client(tmp_path)
    record = upload_png(client).json()
    (tmp_path / "uploads" / record["stored_filename"]).unlink()

    response = client.get(f"/api/screenshots/{record['id']}/image")

    assert response.status_code == 404


def test_delete_screenshot_removes_record_image_and_search_index(tmp_path):
    client = make_client(tmp_path)
    record = upload_png(client, "terminal-error.png").json()
    stored_path = tmp_path / "uploads" / record["stored_filename"]

    response = client.delete(f"/api/screenshots/{record['id']}")

    assert response.status_code == 200
    assert response.json() == {"deleted": True}
    assert stored_path.exists() is False
    assert client.get(f"/api/screenshots/{record['id']}").status_code == 404
    assert client.get("/api/screenshots", params={"query": "terminal"}).json() == []


def test_delete_screenshot_returns_404_for_missing_record(tmp_path):
    client = make_client(tmp_path)

    response = client.delete("/api/screenshots/999")

    assert response.status_code == 404
