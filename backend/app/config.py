"""Purpose: application runtime configuration. Callers: app factory and ingest service. Deps: dataclasses, pathlib. API: AppSettings. Side effects: validates settings at construction."""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

OrganizeMode = Literal["copy", "move"]


@dataclass(frozen=True)
class AppSettings:
    screenshots_dir: str | Path = "data/inbox"
    organized_dir: str | Path = "data/organized"
    organize_mode: OrganizeMode = "copy"
    max_upload_bytes: int = 10 * 1024 * 1024
    max_image_pixels: int = 16_000_000
    ocr_enabled: bool = True
    ocr_language: str = "eng"
    ocr_timeout_seconds: int = 10
    taxonomy_path: str | Path | None = None
    api_key: str | None = None

    def __post_init__(self) -> None:
        if self.organize_mode not in {"copy", "move"}:
            raise ValueError("organize_mode must be 'copy' or 'move'")


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    return default if value is None else int(value)


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    return default if value is None else float(value)


def settings_from_env() -> AppSettings:
    return AppSettings(
        screenshots_dir=os.getenv("SCREENSORT_SCREENSHOTS_DIR", "data/inbox"),
        organized_dir=os.getenv("SCREENSORT_ORGANIZED_DIR", "data/organized"),
        organize_mode=os.getenv("SCREENSORT_ORGANIZE_MODE", "copy"),
        max_upload_bytes=_int_env("SCREENSORT_MAX_UPLOAD_BYTES", 10 * 1024 * 1024),
        max_image_pixels=_int_env("SCREENSORT_MAX_IMAGE_PIXELS", 16_000_000),
        ocr_enabled=_bool_env("SCREENSORT_OCR_ENABLED", True),
        ocr_language=os.getenv("SCREENSORT_OCR_LANGUAGE", "eng"),
        ocr_timeout_seconds=_int_env("SCREENSORT_OCR_TIMEOUT_SECONDS", 10),
        taxonomy_path=os.getenv("SCREENSORT_TAXONOMY_PATH"),
        api_key=os.getenv("SCREENSORT_API_KEY"),
    )


def watcher_interval_from_env() -> float:
    return _float_env("SCREENSORT_WATCHER_INTERVAL_SECONDS", 5.0)
