"""Purpose: OCR extractor tests. Callers: pytest. Deps: pathlib, pytest, Pillow, app services/config. API: test functions. Side effects: writes temporary PNG files."""
from pathlib import Path

import pytest
from PIL import Image

from app.config import AppSettings
from app.services import ocr
from app.services.ocr import OcrExtractor


def write_png(path: Path) -> Path:
    Image.new("RGB", (2, 2), "white").save(path, format="PNG")
    return path


def test_extract_returns_stripped_text(tmp_path, monkeypatch):
    image_path = write_png(tmp_path / "screen.png")
    calls = {}

    def fake_image_to_string(image, *, lang, timeout):
        calls["image"] = image
        calls["lang"] = lang
        calls["timeout"] = timeout
        return "  hello world\n"

    monkeypatch.setattr("app.services.ocr.pytesseract.image_to_string", fake_image_to_string)

    text = OcrExtractor(AppSettings(ocr_language="ind", ocr_timeout_seconds=3)).extract(image_path)

    assert text == "hello world"
    assert calls["lang"] == "ind"
    assert calls["timeout"] == 3
    assert calls["image"].mode == "RGB"


def test_extract_returns_empty_for_empty_ocr(tmp_path, monkeypatch):
    image_path = write_png(tmp_path / "empty.png")
    monkeypatch.setattr("app.services.ocr.pytesseract.image_to_string", lambda *_args, **_kwargs: "  \n")

    assert OcrExtractor(AppSettings()).extract(image_path) == ""


def test_extract_returns_empty_when_disabled(tmp_path, monkeypatch):
    image_path = write_png(tmp_path / "disabled.png")

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("OCR should not run when disabled")

    monkeypatch.setattr("app.services.ocr.pytesseract.image_to_string", fail_if_called)

    assert OcrExtractor(AppSettings(ocr_enabled=False)).extract(image_path) == ""


def test_extract_raises_runtime_error_on_engine_failure(tmp_path, monkeypatch):
    image_path = write_png(tmp_path / "failure.png")

    def fail_ocr(*_args, **_kwargs):
        raise RuntimeError("binary missing")

    monkeypatch.setattr("app.services.ocr.pytesseract.image_to_string", fail_ocr)

    with pytest.raises(RuntimeError, match=r"^OCR failed\.$"):
        OcrExtractor(AppSettings()).extract(image_path)


def test_extract_raises_runtime_error_when_tesseract_missing(tmp_path, monkeypatch):
    image_path = write_png(tmp_path / "missing-binary.png")

    def fail_ocr(*_args, **_kwargs):
        raise ocr.pytesseract.TesseractNotFoundError()

    monkeypatch.setattr("app.services.ocr.pytesseract.image_to_string", fail_ocr)

    with pytest.raises(RuntimeError, match=r"^OCR failed\.$"):
        OcrExtractor(AppSettings()).extract(image_path)


def test_extract_raises_runtime_error_on_timeout(tmp_path, monkeypatch):
    image_path = write_png(tmp_path / "timeout.png")

    def fail_ocr(*_args, **_kwargs):
        raise TimeoutError("OCR timed out")

    monkeypatch.setattr("app.services.ocr.pytesseract.image_to_string", fail_ocr)

    with pytest.raises(RuntimeError, match=r"^OCR failed\.$"):
        OcrExtractor(AppSettings()).extract(image_path)


def test_extract_rejects_invalid_image(tmp_path):
    image_path = tmp_path / "invalid.png"
    image_path.write_text("not an image")

    with pytest.raises(ValueError, match=r"^Invalid image file\.$"):
        OcrExtractor(AppSettings()).extract(image_path)


def test_extract_rejects_corrupted_image(tmp_path):
    image_path = tmp_path / "corrupt.png"
    Image.new("RGB", (2, 2), "white").save(image_path, format="PNG")
    image_path.write_bytes(image_path.read_bytes()[:12])

    with pytest.raises(ValueError, match=r"^Invalid image file\.$"):
        OcrExtractor(AppSettings()).extract(image_path)
