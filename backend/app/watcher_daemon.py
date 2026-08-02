"""Purpose: CLI entrypoint for continuous screenshot folder watching. Callers: python -m app.watcher_daemon and Docker/manual operators. Deps: pathlib, app config, classifier, OCR, DB, watcher service. API: main. Side effects: initializes DB, creates upload directory, polls filesystem forever."""
from pathlib import Path

from app.config import watcher_interval_from_env, settings_from_env
from app.db import init_db
from app.services.classifier import PromptClassifier
from app.services.ocr import OcrExtractor
from app.services.watcher import run_watcher_loop


def main() -> None:
    settings = settings_from_env()
    db_path = Path("data/screenshots.db")
    upload_dir = Path("data/uploads")
    init_db(db_path)
    upload_dir.mkdir(parents=True, exist_ok=True)
    run_watcher_loop(
        db_path,
        upload_dir,
        PromptClassifier(taxonomy_path=settings.taxonomy_path),
        settings,
        OcrExtractor(settings),
        interval_seconds=watcher_interval_from_env(),
    )


if __name__ == "__main__":
    main()
