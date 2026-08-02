"""Purpose: API model tests. Callers: pytest. Deps: datetime, app.models. API: test functions. Side effects: none."""

from datetime import datetime, timezone

from app.models import ScanSummary, ScreenshotRecord, WatcherStatus


def test_watcher_status_constructs_and_serializes():
    status = WatcherStatus(screenshots_dir="data/inbox", organized_dir="data/organized", organize_mode="copy", source_exists=True)

    assert status.model_dump() == {
        "screenshots_dir": "data/inbox",
        "organized_dir": "data/organized",
        "organize_mode": "copy",
        "source_exists": True,
    }


def test_screenshot_record_serializes_ocr_text():
    created_at = datetime(2026, 4, 28, tzinfo=timezone.utc)
    record = ScreenshotRecord(
        id=1,
        original_filename="screen.png",
        stored_filename="stored.png",
        path="data/uploads/stored.png",
        category="notes",
        confidence=0.9,
        tags=["ocr"],
        created_at=created_at,
        ocr_text="Visible text",
    )

    assert record.model_dump()["ocr_text"] == "Visible text"


def test_screenshot_record_defaults_ocr_text_to_none():
    created_at = datetime(2026, 4, 28, tzinfo=timezone.utc)
    record = ScreenshotRecord(
        id=1,
        original_filename="screen.png",
        stored_filename="stored.png",
        path="data/uploads/stored.png",
        category="notes",
        confidence=0.9,
        tags=[],
        created_at=created_at,
    )

    assert record.model_dump()["ocr_text"] is None


def test_scan_summary_constructs_and_serializes():
    summary = ScanSummary(seen=3, ingested=2, skipped=1, failed=0, records=[])

    assert summary.model_dump() == {"seen": 3, "ingested": 2, "skipped": 1, "failed": 0, "records": []}
