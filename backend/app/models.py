"""Purpose: shared API/data models. Callers: database helpers and routes. Deps: datetime, Pydantic. API: ScreenshotRecord, ClassificationResult, WatcherStatus, ScanSummary. Side effects: none."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.config import OrganizeMode


class ScreenshotRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    stored_filename: str
    path: str
    source_path: str | None = None
    ingest_method: str = "upload"
    category: str
    confidence: float
    tags: list[str]
    created_at: datetime
    ocr_text: str | None = None


class ClassificationResult(BaseModel):
    category: str
    confidence: float
    tags: list[str]


class WatcherStatus(BaseModel):
    screenshots_dir: str
    organized_dir: str
    organize_mode: OrganizeMode
    source_exists: bool


class ScanSummary(BaseModel):
    seen: int = 0
    ingested: int = 0
    skipped: int = 0
    failed: int = 0
    records: list[ScreenshotRecord] = []

    @property
    def scanned(self) -> int:
        return self.seen

    @property
    def imported(self) -> int:
        return self.ingested
