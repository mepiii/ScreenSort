"""Purpose: configuration tests. Callers: pytest. Deps: pytest, app.config. API: test functions. Side effects: none."""

import pytest

from app.config import AppSettings, settings_from_env, watcher_interval_from_env
from app.main import create_app


def test_app_settings_defaults():
    settings = AppSettings()

    assert settings.screenshots_dir == "data/inbox"
    assert settings.organized_dir == "data/organized"
    assert settings.organize_mode == "copy"
    assert settings.max_upload_bytes == 10 * 1024 * 1024
    assert settings.max_image_pixels == 16_000_000
    assert settings.ocr_enabled is True
    assert settings.ocr_language == "eng"
    assert settings.ocr_timeout_seconds == 10
    assert settings.taxonomy_path is None


def test_app_settings_rejects_invalid_organize_mode():
    with pytest.raises(ValueError, match="organize_mode"):
        AppSettings(organize_mode="delete")


def test_settings_from_env_reads_container_settings(monkeypatch):
    monkeypatch.setenv("SCREENSORT_SCREENSHOTS_DIR", "/app/data/inbox")
    monkeypatch.setenv("SCREENSORT_ORGANIZED_DIR", "/app/data/organized")
    monkeypatch.setenv("SCREENSORT_ORGANIZE_MODE", "move")
    monkeypatch.setenv("SCREENSORT_MAX_UPLOAD_BYTES", "2048")
    monkeypatch.setenv("SCREENSORT_MAX_IMAGE_PIXELS", "4096")
    monkeypatch.setenv("SCREENSORT_OCR_ENABLED", "false")
    monkeypatch.setenv("SCREENSORT_OCR_LANGUAGE", "eng+ind")
    monkeypatch.setenv("SCREENSORT_OCR_TIMEOUT_SECONDS", "3")
    monkeypatch.setenv("SCREENSORT_TAXONOMY_PATH", "/app/data/taxonomy.json")

    settings = settings_from_env()

    assert settings == AppSettings(
        screenshots_dir="/app/data/inbox",
        organized_dir="/app/data/organized",
        organize_mode="move",
        max_upload_bytes=2048,
        max_image_pixels=4096,
        ocr_enabled=False,
        ocr_language="eng+ind",
        ocr_timeout_seconds=3,
        taxonomy_path="/app/data/taxonomy.json",
    )


def test_settings_from_env_uses_defaults_when_env_is_absent(monkeypatch):
    for key in [
        "SCREENSORT_SCREENSHOTS_DIR",
        "SCREENSORT_ORGANIZED_DIR",
        "SCREENSORT_ORGANIZE_MODE",
        "SCREENSORT_MAX_UPLOAD_BYTES",
        "SCREENSORT_MAX_IMAGE_PIXELS",
        "SCREENSORT_OCR_ENABLED",
        "SCREENSORT_OCR_LANGUAGE",
        "SCREENSORT_OCR_TIMEOUT_SECONDS",
        "SCREENSORT_TAXONOMY_PATH",
    ]:
        monkeypatch.delenv(key, raising=False)

    assert settings_from_env() == AppSettings()


def test_watcher_interval_from_env(monkeypatch):
    monkeypatch.setenv("SCREENSORT_WATCHER_INTERVAL_SECONDS", "1.5")

    assert watcher_interval_from_env() == 1.5


def test_create_app_stores_custom_settings(tmp_path):
    settings = AppSettings(screenshots_dir="custom/inbox")

    app = create_app(db_path=tmp_path / "screenshots.db", upload_dir=tmp_path / "uploads", settings=settings)

    assert app.state.settings == settings
