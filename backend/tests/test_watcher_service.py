"""Purpose: watcher service tests. Callers: pytest. Deps: pathlib, app watcher service. API: test functions. Side effects: none."""
from pathlib import Path

from app.config import AppSettings
from app.models import ScanSummary
from app.services import watcher


class FakeClassifier:
    pass


class FakeOcrExtractor:
    pass


def test_run_watcher_once_delegates_to_scan(monkeypatch, tmp_path):
    calls = []
    expected = ScanSummary(seen=1, ingested=1, skipped=0, failed=0, records=[])

    def fake_scan(db_path, upload_dir, classifier, settings, ocr_extractor):
        calls.append((db_path, upload_dir, classifier, settings, ocr_extractor))
        return expected

    monkeypatch.setattr(watcher, "scan_folder_once", fake_scan)
    classifier = FakeClassifier()
    ocr_extractor = FakeOcrExtractor()
    settings = AppSettings()

    result = watcher.run_watcher_once(tmp_path / "db.sqlite", tmp_path / "uploads", classifier, settings, ocr_extractor)

    assert result == expected
    assert calls == [(tmp_path / "db.sqlite", tmp_path / "uploads", classifier, settings, ocr_extractor)]


def test_run_watcher_loop_repeats_until_stop(monkeypatch, tmp_path):
    calls: list[Path] = []
    sleeps: list[float] = []

    def fake_once(db_path, *_args):
        calls.append(db_path)

    def should_stop():
        return len(calls) == 3

    monkeypatch.setattr(watcher, "run_watcher_once", fake_once)

    watcher.run_watcher_loop(
        tmp_path / "db.sqlite",
        tmp_path / "uploads",
        FakeClassifier(),
        AppSettings(),
        interval_seconds=2.5,
        should_stop=should_stop,
        sleep=sleeps.append,
    )

    assert calls == [tmp_path / "db.sqlite", tmp_path / "db.sqlite", tmp_path / "db.sqlite"]
    assert sleeps == [2.5, 2.5]
