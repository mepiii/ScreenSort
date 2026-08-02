"""Purpose: ingest service tests. Callers: pytest. Deps: pathlib, PIL, app services. API: test functions. Side effects: creates temporary files and SQLite DBs."""
from io import BytesIO
import sqlite3
from pathlib import Path

import pytest
from PIL import Image

from app.config import AppSettings
from app.db import init_db, list_screenshots
from app.models import ClassificationResult
from app.services.ingest import scan_folder_once


class FakeClassifier:
    def classify(self, image_path: Path):
        return ClassificationResult(category="code", confidence=0.93, tags=["terminal", "error"])


class WeirdClassifier:
    def classify(self, image_path: Path):
        return ClassificationResult(category="Work Notes!", confidence=0.8, tags=[])


class FailingClassifier:
    def classify(self, image_path: Path):
        raise RuntimeError("classifier failed")


class FakeOcrExtractor:
    def extract(self, image_path: Path) -> str:
        return "visible OCR text"


class FailingOcrExtractor:
    def extract(self, image_path: Path) -> str:
        raise RuntimeError("ocr failed")


def write_png(path: Path, size: tuple[int, int] = (8, 8)) -> None:
    buffer = BytesIO()
    Image.new("RGB", size, color="black").save(buffer, format="PNG")
    path.write_bytes(buffer.getvalue())


def test_scan_folder_ingests_image_in_copy_mode(tmp_path):
    source_dir = tmp_path / "screenshots"
    upload_dir = tmp_path / "uploads"
    db_path = tmp_path / "screenshots.db"
    source_dir.mkdir()
    source = source_dir / "shot.png"
    write_png(source)
    init_db(db_path)

    summary = scan_folder_once(db_path, upload_dir, FakeClassifier(), AppSettings(screenshots_dir=source_dir))

    assert summary.seen == 1
    assert summary.ingested == 1
    assert summary.skipped == 0
    assert summary.failed == 0
    assert source.exists()
    assert len(summary.records) == 1
    records = list_screenshots(db_path)
    assert records[0].source_path == str(source.resolve())
    assert records[0].ingest_method == "scan"
    assert Path(records[0].path).exists()


def test_scan_folder_stores_ocr_text_from_extractor(tmp_path):
    source_dir = tmp_path / "screenshots"
    upload_dir = tmp_path / "uploads"
    db_path = tmp_path / "screenshots.db"
    source_dir.mkdir()
    source = source_dir / "shot.png"
    write_png(source)
    init_db(db_path)

    summary = scan_folder_once(
        db_path,
        upload_dir,
        FakeClassifier(),
        AppSettings(screenshots_dir=source_dir),
        FakeOcrExtractor(),
    )

    assert summary.ingested == 1
    assert summary.records[0].ocr_text == "visible OCR text"
    assert list_screenshots(db_path)[0].ocr_text == "visible OCR text"


def test_scan_folder_ocr_failure_removes_copy_without_record(tmp_path):
    source_dir = tmp_path / "screenshots"
    upload_dir = tmp_path / "uploads"
    db_path = tmp_path / "screenshots.db"
    source_dir.mkdir()
    source = source_dir / "shot.png"
    write_png(source)
    init_db(db_path)

    summary = scan_folder_once(
        db_path,
        upload_dir,
        FakeClassifier(),
        AppSettings(screenshots_dir=source_dir),
        FailingOcrExtractor(),
    )

    assert summary.seen == 1
    assert summary.failed == 1
    assert summary.ingested == 0
    assert source.exists()
    assert list(upload_dir.glob("*")) == []
    assert list_screenshots(db_path) == []


def test_scan_folder_skips_existing_source_path(tmp_path):
    source_dir = tmp_path / "screenshots"
    upload_dir = tmp_path / "uploads"
    db_path = tmp_path / "screenshots.db"
    source_dir.mkdir()
    source = source_dir / "shot.png"
    write_png(source)
    init_db(db_path)

    scan_folder_once(db_path, upload_dir, FakeClassifier(), AppSettings(screenshots_dir=source_dir))
    summary = scan_folder_once(db_path, upload_dir, FakeClassifier(), AppSettings(screenshots_dir=source_dir))

    assert summary.seen == 1
    assert summary.ingested == 0
    assert summary.skipped == 1
    assert summary.failed == 0
    assert len(list_screenshots(db_path)) == 1


def test_scan_folder_moves_original_in_move_mode(tmp_path):
    source_dir = tmp_path / "screenshots"
    organized_dir = tmp_path / "organized"
    upload_dir = tmp_path / "uploads"
    db_path = tmp_path / "screenshots.db"
    source_dir.mkdir()
    source = source_dir / "shot.png"
    write_png(source)
    init_db(db_path)

    summary = scan_folder_once(
        db_path,
        upload_dir,
        FakeClassifier(),
        AppSettings(screenshots_dir=source_dir, organized_dir=organized_dir, organize_mode="move"),
    )

    assert summary.ingested == 1
    assert not source.exists()
    assert (organized_dir / "code" / "shot.png").exists()


def test_scan_folder_cleans_copy_when_classifier_fails(tmp_path):
    source_dir = tmp_path / "screenshots"
    upload_dir = tmp_path / "uploads"
    db_path = tmp_path / "screenshots.db"
    source_dir.mkdir()
    source = source_dir / "shot.png"
    write_png(source)
    init_db(db_path)

    summary = scan_folder_once(db_path, upload_dir, FailingClassifier(), AppSettings(screenshots_dir=source_dir))

    assert summary.seen == 1
    assert summary.failed == 1
    assert summary.ingested == 0
    assert source.exists()
    assert list(upload_dir.glob("*")) == []
    assert list_screenshots(db_path) == []


def test_scan_folder_rejects_missing_source_dir(tmp_path):
    db_path = tmp_path / "screenshots.db"
    init_db(db_path)

    with pytest.raises(FileNotFoundError):
        scan_folder_once(db_path, tmp_path / "uploads", FakeClassifier(), AppSettings(screenshots_dir=tmp_path / "missing"))


def test_scan_folder_ignores_disallowed_suffixes(tmp_path):
    source_dir = tmp_path / "screenshots"
    db_path = tmp_path / "screenshots.db"
    source_dir.mkdir()
    (source_dir / "note.txt").write_text("not image")
    init_db(db_path)

    summary = scan_folder_once(db_path, tmp_path / "uploads", FakeClassifier(), AppSettings(screenshots_dir=source_dir))

    assert summary.seen == 0
    assert summary.ingested == 0
    assert list_screenshots(db_path) == []


def test_scan_folder_validates_size_and_pixels(tmp_path):
    source_dir = tmp_path / "screenshots"
    db_path = tmp_path / "screenshots.db"
    source_dir.mkdir()
    write_png(source_dir / "too-large.png", size=(8, 8))
    init_db(db_path)

    summary = scan_folder_once(
        db_path,
        tmp_path / "uploads",
        FakeClassifier(),
        AppSettings(screenshots_dir=source_dir, max_image_pixels=4),
    )

    assert summary.seen == 1
    assert summary.failed == 1
    assert list_screenshots(db_path) == []


def test_scan_folder_rejects_oversized_bytes_without_copying(tmp_path):
    source_dir = tmp_path / "screenshots"
    upload_dir = tmp_path / "uploads"
    db_path = tmp_path / "screenshots.db"
    source_dir.mkdir()
    source = source_dir / "too-large.png"
    write_png(source)
    init_db(db_path)

    summary = scan_folder_once(
        db_path,
        upload_dir,
        FakeClassifier(),
        AppSettings(screenshots_dir=source_dir, max_upload_bytes=source.stat().st_size - 1),
    )

    assert summary.seen == 1
    assert summary.failed == 1
    assert source.exists()
    assert list(upload_dir.glob("*")) == []
    assert list_screenshots(db_path) == []


def test_scan_folder_sanitizes_move_category(tmp_path):
    source_dir = tmp_path / "screenshots"
    organized_dir = tmp_path / "organized"
    db_path = tmp_path / "screenshots.db"
    source_dir.mkdir()
    source = source_dir / "shot.png"
    write_png(source)
    init_db(db_path)

    summary = scan_folder_once(
        db_path,
        tmp_path / "uploads",
        WeirdClassifier(),
        AppSettings(screenshots_dir=source_dir, organized_dir=organized_dir, organize_mode="move"),
    )

    assert summary.ingested == 1
    assert (organized_dir / "work-notes" / "shot.png").exists()


def test_scan_folder_rejects_symlink_escape_before_copy(tmp_path):
    source_dir = tmp_path / "screenshots"
    outside_dir = tmp_path / "outside"
    upload_dir = tmp_path / "uploads"
    db_path = tmp_path / "screenshots.db"
    source_dir.mkdir()
    outside_dir.mkdir()
    outside = outside_dir / "outside.png"
    write_png(outside)
    (source_dir / "linked.png").symlink_to(outside)
    init_db(db_path)

    summary = scan_folder_once(db_path, upload_dir, FakeClassifier(), AppSettings(screenshots_dir=source_dir))

    assert summary.seen == 1
    assert summary.failed == 1
    assert outside.exists()
    assert list(upload_dir.glob("*")) == []
    assert list_screenshots(db_path) == []


def test_scan_folder_rejects_symlink_inside_source_dir_before_move(tmp_path):
    source_dir = tmp_path / "screenshots"
    organized_dir = tmp_path / "organized"
    upload_dir = tmp_path / "uploads"
    db_path = tmp_path / "screenshots.db"
    source_dir.mkdir()
    target = source_dir / "target.png"
    write_png(target)
    link = source_dir / "linked.png"
    link.symlink_to(target)
    init_db(db_path)

    summary = scan_folder_once(
        db_path,
        upload_dir,
        FakeClassifier(),
        AppSettings(screenshots_dir=source_dir, organized_dir=organized_dir, organize_mode="move"),
    )

    assert summary.seen == 2
    assert summary.failed == 1
    assert summary.ingested == 1
    assert target.exists() is False
    assert link.exists() is False
    assert (organized_dir / "code" / "target.png").exists()
    assert not (organized_dir / "code" / "linked.png").exists()


def test_scan_folder_validates_and_copies_same_bytes(tmp_path, monkeypatch):
    source_dir = tmp_path / "screenshots"
    upload_dir = tmp_path / "uploads"
    db_path = tmp_path / "screenshots.db"
    source_dir.mkdir()
    source = source_dir / "shot.png"
    write_png(source)
    replacement = tmp_path / "replacement.png"
    write_png(replacement, size=(16, 16))
    replacement_bytes = replacement.read_bytes()
    init_db(db_path)
    original_open = Image.open

    def replacing_open(fp, *args, **kwargs):
        if isinstance(fp, BytesIO):
            source.write_bytes(replacement_bytes)
        return original_open(fp, *args, **kwargs)

    monkeypatch.setattr("app.services.ingest.Image.open", replacing_open)
    summary = scan_folder_once(db_path, upload_dir, FakeClassifier(), AppSettings(screenshots_dir=source_dir))

    assert summary.ingested == 1
    assert Path(summary.records[0].path).read_bytes() != replacement_bytes


def test_scan_folder_cleans_db_and_upload_when_move_fails(tmp_path, monkeypatch):
    source_dir = tmp_path / "screenshots"
    organized_dir = tmp_path / "organized"
    upload_dir = tmp_path / "uploads"
    db_path = tmp_path / "screenshots.db"
    source_dir.mkdir()
    source = source_dir / "shot.png"
    write_png(source)
    init_db(db_path)

    def fail_move(*args):
        raise OSError("move failed")

    monkeypatch.setattr("app.services.ingest.shutil.move", fail_move)
    summary = scan_folder_once(
        db_path,
        upload_dir,
        FakeClassifier(),
        AppSettings(screenshots_dir=source_dir, organized_dir=organized_dir, organize_mode="move"),
    )

    assert summary.ingested == 0
    assert summary.failed == 1
    assert source.exists()
    assert list_screenshots(db_path) == []
    assert list(upload_dir.glob("*")) == []


def test_scan_folder_counts_generic_db_failure_without_copy_or_record(tmp_path, monkeypatch):
    source_dir = tmp_path / "screenshots"
    upload_dir = tmp_path / "uploads"
    db_path = tmp_path / "screenshots.db"
    source_dir.mkdir()
    source = source_dir / "shot.png"
    write_png(source)
    init_db(db_path)

    def fail_insert(*args, **kwargs):
        raise sqlite3.OperationalError("db failed")

    monkeypatch.setattr("app.services.ingest.insert_screenshot", fail_insert)
    summary = scan_folder_once(db_path, upload_dir, FakeClassifier(), AppSettings(screenshots_dir=source_dir))

    assert summary.seen == 1
    assert summary.ingested == 0
    assert summary.failed == 1
    assert source.exists()
    assert list(upload_dir.glob("*")) == []
    assert list_screenshots(db_path) == []



def test_scan_folder_skips_duplicate_source_path_integrity_error(tmp_path):
    source_dir = tmp_path / "screenshots"
    upload_dir = tmp_path / "uploads"
    db_path = tmp_path / "screenshots.db"
    source_dir.mkdir()
    source = source_dir / "shot.png"
    write_png(source)
    init_db(db_path)

    resolved = str(source.resolve())
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO screenshots (original_filename, stored_filename, path, source_path, ingest_method, category, confidence, tags, created_at)
            VALUES ('existing.png', 'existing.png', 'uploads/existing.png', ?, 'scan', 'code', 0.9, '[]', '2026-01-01T00:00:00+00:00')
            """,
            (resolved,),
        )
    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM screenshots WHERE source_path = ?", (resolved,))
        conn.execute(
            """
            CREATE TRIGGER duplicate_source_path_race BEFORE INSERT ON screenshots
            BEGIN
                SELECT RAISE(ABORT, 'UNIQUE constraint failed: screenshots.source_path');
            END
            """
        )

    summary = scan_folder_once(db_path, upload_dir, FakeClassifier(), AppSettings(screenshots_dir=source_dir))

    assert summary.ingested == 0
    assert summary.skipped == 1
    assert summary.failed == 0
    assert list_screenshots(db_path) == []
    assert list(upload_dir.glob("*")) == []


def test_scan_folder_skips_disappearing_source_during_stability(tmp_path, monkeypatch):
    source_dir = tmp_path / "screenshots"
    db_path = tmp_path / "screenshots.db"
    source_dir.mkdir()
    source = source_dir / "shot.png"
    write_png(source)
    init_db(db_path)

    original_stat = Path.stat

    def disappearing_stat(path, *args, **kwargs):
        if path == source:
            source.unlink(missing_ok=True)
            raise FileNotFoundError(str(path))
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", disappearing_stat)
    summary = scan_folder_once(db_path, tmp_path / "uploads", FakeClassifier(), AppSettings(screenshots_dir=source_dir))

    assert summary.seen == 1
    assert summary.skipped == 1
    assert summary.failed == 0
    assert list_screenshots(db_path) == []
