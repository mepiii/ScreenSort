"""Purpose: FastAPI app factory. Callers: ASGI servers and tests. Deps: pathlib, FastAPI, CORS, DB, API routers, classifier. API: create_app, app. Side effects: initializes DB and creates app instance at import."""
from pathlib import Path
from typing import Protocol

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.screenshots import router as screenshots_router
from app.api.watcher import router as watcher_router
from app.config import AppSettings, settings_from_env
from app.db import init_db
from app.models import ClassificationResult
from app.services.classifier import PromptClassifier
from app.services.ocr import OcrExtractor


class Classifier(Protocol):
    def classify(self, image_path: Path) -> ClassificationResult: ...


class OcrExtracting(Protocol):
    def extract(self, image_path: Path) -> str: ...


def create_app(
    db_path: Path = Path("data/screenshots.db"),
    upload_dir: Path = Path("data/uploads"),
    classifier: Classifier | None = None,
    ocr_extractor: OcrExtracting | None = None,
    settings: AppSettings | None = None,
) -> FastAPI:
    settings = settings if settings is not None else settings_from_env()
    init_db(db_path)
    app = FastAPI(title="ScreenSort API")
    app.state.db_path = db_path
    app.state.upload_dir = upload_dir
    app.state.settings = settings
    app.state.classifier = classifier if classifier is not None else PromptClassifier(taxonomy_path=settings.taxonomy_path)
    app.state.ocr_extractor = ocr_extractor if ocr_extractor is not None else OcrExtractor(settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(screenshots_router, prefix="/api")
    app.include_router(watcher_router, prefix="/api")
    return app


app = create_app()
