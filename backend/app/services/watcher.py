"""Purpose: continuous folder watcher loop. Callers: watcher CLI and tests. Deps: time, pathlib, app config and ingest service. API: run_watcher_once, run_watcher_loop. Side effects: scans screenshot folder and sleeps between polls."""
import time
from pathlib import Path
from typing import Any, Callable

from app.config import AppSettings
from app.models import ScanSummary
from app.services.ingest import scan_folder_once


def run_watcher_once(
    db_path: Path,
    upload_dir: Path,
    classifier: Any,
    settings: AppSettings,
    ocr_extractor: Any | None = None,
) -> ScanSummary:
    return scan_folder_once(db_path, upload_dir, classifier, settings, ocr_extractor)


def run_watcher_loop(
    db_path: Path,
    upload_dir: Path,
    classifier: Any,
    settings: AppSettings,
    ocr_extractor: Any | None = None,
    interval_seconds: float = 5.0,
    should_stop: Callable[[], bool] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    stop = should_stop or (lambda: False)
    while not stop():
        run_watcher_once(db_path, upload_dir, classifier, settings, ocr_extractor)
        if not stop():
            sleep(interval_seconds)
