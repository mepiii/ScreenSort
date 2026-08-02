"""Purpose: OCR text extraction. Callers: ingest/search pipelines and tests. Deps: pathlib, Pillow, pytesseract, app.config. API: OcrExtractor.extract. Side effects: reads image files and invokes OCR engine."""
from pathlib import Path

import pytesseract
from PIL import Image, UnidentifiedImageError

from app.config import AppSettings


class OcrExtractor:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    def extract(self, image_path: Path) -> str:
        if not self.settings.ocr_enabled:
            return ""
        try:
            with Image.open(image_path) as image:
                rgb_image = image.convert("RGB")
        except (UnidentifiedImageError, OSError) as exc:
            raise ValueError("Invalid image file.") from exc

        with rgb_image:
            try:
                text = pytesseract.image_to_string(
                    rgb_image,
                    lang=self.settings.ocr_language,
                    timeout=self.settings.ocr_timeout_seconds,
                )
            except (pytesseract.TesseractError, pytesseract.TesseractNotFoundError, RuntimeError, TimeoutError) as exc:
                raise RuntimeError("OCR failed.") from exc
        return text.strip()
