"""Purpose: watcher API routes. Callers: app.main router registration. Deps: pathlib, FastAPI, ingest service, models. API: router with watcher status and scan routes. Side effects: scan route reads source folder and writes uploads/SQLite."""
from dataclasses import replace
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.api.auth import require_api_key
from app.models import ScanSummary, WatcherStatus
from app.services.ingest import scan_folder_once

router = APIRouter(prefix="/watcher")


class ScanRequest(BaseModel):
    screenshots_dir: str | None = None


@router.get("/status", response_model=WatcherStatus, dependencies=[Depends(require_api_key)])
def watcher_status(request: Request) -> WatcherStatus:
    settings = request.app.state.settings
    source = Path(settings.screenshots_dir)
    return WatcherStatus(
        screenshots_dir=str(settings.screenshots_dir),
        organized_dir=str(settings.organized_dir),
        organize_mode=settings.organize_mode,
        source_exists=source.exists() and source.is_dir(),
    )


@router.post("/scan", response_model=ScanSummary, dependencies=[Depends(require_api_key)])
async def scan_watcher_folder(request: Request, scan_request: ScanRequest | None = None) -> ScanSummary:
    settings = request.app.state.settings
    if scan_request and scan_request.screenshots_dir:
        settings = replace(settings, screenshots_dir=scan_request.screenshots_dir)
    source = Path(settings.screenshots_dir).expanduser()
    if not source.is_dir():
        raise HTTPException(status_code=400, detail="Screenshot source folder does not exist.")
    settings = replace(settings, screenshots_dir=source)
    return await run_in_threadpool(
        scan_folder_once,
        request.app.state.db_path,
        request.app.state.upload_dir,
        request.app.state.classifier,
        settings,
        request.app.state.ocr_extractor,
    )
