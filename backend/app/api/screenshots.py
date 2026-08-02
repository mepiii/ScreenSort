"""Purpose: screenshot API routes. Callers: app.main router registration. Deps: FastAPI, Pillow, DB, storage, models. API: router with health/upload/list/detail/image routes. Side effects: decodes images, writes uploads, reads/writes SQLite."""
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from app.api.auth import require_api_key
from app.db import delete_screenshot, get_screenshot, insert_screenshot, list_screenshots
from app.models import ScreenshotRecord
from app.services.storage import save_upload_bytes

router = APIRouter()
ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp"}


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


def _validate_image(content: bytes, max_image_pixels: int) -> None:
    try:
        with Image.open(BytesIO(content)) as image:
            if image.width * image.height > max_image_pixels:
                raise HTTPException(status_code=400, detail="Image dimensions exceed limit.")
            image.verify()
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(status_code=400, detail="Invalid image file") from exc


@router.post("/screenshots", response_model=ScreenshotRecord, dependencies=[Depends(require_api_key)])
async def upload_screenshot(request: Request, file: UploadFile = File(...)) -> ScreenshotRecord:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported image content type")
    settings = request.app.state.settings
    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Upload exceeds size limit.")
    await run_in_threadpool(_validate_image, content, settings.max_image_pixels)
    stored = await run_in_threadpool(
        save_upload_bytes,
        request.app.state.upload_dir,
        file.filename or "upload",
        content,
    )
    try:
        classification = await run_in_threadpool(request.app.state.classifier.classify, stored.path)
        ocr_text = await run_in_threadpool(request.app.state.ocr_extractor.extract, stored.path)
        return await run_in_threadpool(
            insert_screenshot,
            request.app.state.db_path,
            file.filename or "upload",
            stored.stored_filename,
            str(stored.path),
            classification.category,
            classification.confidence,
            classification.tags,
            ingest_method="upload",
            ocr_text=ocr_text,
        )
    except Exception:
        stored.path.unlink(missing_ok=True)
        raise


@router.get("/screenshots", response_model=list[ScreenshotRecord], dependencies=[Depends(require_api_key)])
def list_screenshot_records(
    request: Request,
    query: str | None = None,
    category: str | None = None,
    tag: str | None = None,
) -> list[ScreenshotRecord]:
    return list_screenshots(request.app.state.db_path, query=query, category=category, tag=tag)


@router.get("/screenshots/{screenshot_id}", response_model=ScreenshotRecord, dependencies=[Depends(require_api_key)])
def get_screenshot_record(request: Request, screenshot_id: int) -> ScreenshotRecord:
    record = get_screenshot(request.app.state.db_path, screenshot_id)
    if not record:
        raise HTTPException(status_code=404, detail="Screenshot not found")
    return record


@router.get("/screenshots/{screenshot_id}/image", dependencies=[Depends(require_api_key)])
def stream_screenshot_image(request: Request, screenshot_id: int) -> FileResponse:
    record = get_screenshot(request.app.state.db_path, screenshot_id)
    if not record:
        raise HTTPException(status_code=404, detail="Screenshot not found")
    stored_path = Path(record.path).resolve()
    upload_dir = Path(request.app.state.upload_dir).resolve()
    if not stored_path.is_file() or not stored_path.is_relative_to(upload_dir):
        raise HTTPException(status_code=404, detail="Screenshot image not found")
    media_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(_stored_path_suffix(record.stored_filename), "application/octet-stream")
    return FileResponse(stored_path, media_type=media_type)


@router.delete("/screenshots/{screenshot_id}", dependencies=[Depends(require_api_key)])
def delete_screenshot_record(request: Request, screenshot_id: int) -> dict[str, bool]:
    record = get_screenshot(request.app.state.db_path, screenshot_id)
    if not record:
        raise HTTPException(status_code=404, detail="Screenshot not found")
    stored_path = Path(record.path).resolve()
    upload_dir = Path(request.app.state.upload_dir).resolve()
    delete_screenshot(request.app.state.db_path, screenshot_id)
    if stored_path.is_relative_to(upload_dir):
        stored_path.unlink(missing_ok=True)
    return {"deleted": True}


def _stored_path_suffix(stored_filename: str) -> str:
    return f".{stored_filename.rsplit('.', 1)[-1].lower()}" if "." in stored_filename else ""
