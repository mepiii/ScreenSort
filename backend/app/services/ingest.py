"""Purpose: folder scan ingest. Callers: watcher API and tests. Deps: pathlib, shutil, PIL, DB, storage. API: scan_folder_once. Side effects: copies app files, may move originals, writes DB."""
import re
import shutil
import sqlite3
import time
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import uuid4

from PIL import Image, UnidentifiedImageError

from app.config import AppSettings
from app.db import delete_screenshot, get_screenshot_by_source_path, insert_screenshot
from app.models import ScanSummary, ScreenshotRecord
from app.services.storage import save_upload_bytes

ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def _is_stable(path: Path, delay_seconds: float = 0.05) -> bool:
    try:
        first = path.stat().st_size
        time.sleep(delay_seconds)
        return path.exists() and path.stat().st_size == first
    except OSError:
        return False


def _safe_category(category: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", category.strip().lower()).strip("-")
    return value or "uncategorized"


def _read_validated_image_bytes(path: Path, settings: AppSettings) -> bytes:
    if path.is_symlink():
        raise ValueError("source file cannot be a symlink")
    source_root = Path(settings.screenshots_dir).resolve()
    resolved_source = path.resolve()
    if source_root != resolved_source.parent and source_root not in resolved_source.parents:
        raise ValueError("source file is outside screenshots_dir")
    data = resolved_source.read_bytes()
    if len(data) > settings.max_upload_bytes:
        raise ValueError("Upload exceeds size limit.")
    with Image.open(BytesIO(data)) as image:
        if image.width * image.height > settings.max_image_pixels:
            raise ValueError("Image dimensions exceed limit.")
        image.verify()
    return data


def _move_original(source: Path, category: str, settings: AppSettings) -> None:
    source_root = Path(settings.screenshots_dir).resolve()
    resolved_source = source.resolve()
    if source_root not in resolved_source.parents:
        raise ValueError("source file is outside screenshots_dir")
    target_dir = Path(settings.organized_dir) / _safe_category(category)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source.name
    if target.exists():
        target = target_dir / f"{source.stem}-{uuid4().hex}{source.suffix}"
    shutil.move(str(source), str(target))


def _ingest_one(
    db_path: Path,
    upload_dir: Path,
    classifier: Any,
    settings: AppSettings,
    source: Path,
    ocr_extractor: Any | None = None,
) -> ScreenshotRecord:
    resolved_source = source.resolve()
    if get_screenshot_by_source_path(db_path, str(resolved_source)) is not None:
        raise FileExistsError(str(resolved_source))
    data = _read_validated_image_bytes(source, settings)
    stored = save_upload_bytes(upload_dir, source.name, data)
    try:
        result = classifier.classify(stored.path)
        ocr_text = ocr_extractor.extract(stored.path) if ocr_extractor is not None else None
        record = insert_screenshot(
            db_path,
            original_filename=source.name,
            stored_filename=stored.stored_filename,
            path=str(stored.path),
            category=result.category,
            confidence=result.confidence,
            tags=result.tags,
            source_path=str(resolved_source),
            ingest_method="scan",
            ocr_text=ocr_text,
        )
        if settings.organize_mode == "move":
            try:
                _move_original(resolved_source, result.category, settings)
            except Exception:
                delete_screenshot(db_path, record.id)
                raise
        return record
    except Exception:
        stored.path.unlink(missing_ok=True)
        raise


def scan_folder_once(
    db_path: Path,
    upload_dir: Path,
    classifier: Any,
    settings: AppSettings,
    ocr_extractor: Any | None = None,
) -> ScanSummary:
    source_dir = Path(settings.screenshots_dir)
    if not source_dir.exists() or not source_dir.is_dir():
        raise FileNotFoundError(str(source_dir))
    seen = ingested = skipped = failed = 0
    records: list[ScreenshotRecord] = []
    for source in sorted(source_dir.iterdir()):
        if source.suffix.lower() not in ALLOWED_SUFFIXES:
            continue
        seen += 1
        try:
            is_file = source.is_file()
        except OSError:
            skipped += 1
            continue
        if not is_file:
            continue
        if not _is_stable(source):
            skipped += 1
            continue
        try:
            record = _ingest_one(db_path, upload_dir, classifier, settings, source, ocr_extractor)
        except (FileExistsError, sqlite3.IntegrityError):
            skipped += 1
        except (sqlite3.Error, OSError, ValueError, UnidentifiedImageError, RuntimeError):
            failed += 1
        else:
            ingested += 1
            records.append(record)
    return ScanSummary(seen=seen, ingested=ingested, skipped=skipped, failed=failed, records=records)
