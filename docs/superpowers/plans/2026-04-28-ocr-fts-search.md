# OCR and FTS Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add OCR extraction and full-text search across screenshot metadata and OCR text.

**Architecture:** Extend existing ingest paths with injectable OCR extraction, store `ocr_text` in SQLite, and maintain an FTS5 table through DB helper functions. Frontend displays OCR previews and tells users search includes OCR.

**Tech Stack:** FastAPI, SQLite FTS5, Pillow, pytesseract, React, TypeScript, Vitest, pytest.

---

## File Structure

- Modify `backend/app/config.py`: OCR settings.
- Modify `backend/app/models.py`: `ocr_text` on records.
- Modify `backend/app/db.py`: `ocr_text` column, FTS table, insert/delete/search sync.
- Create `backend/app/services/ocr.py`: OCR extractor boundary.
- Modify `backend/app/main.py`: app-level OCR extractor injection.
- Modify `backend/app/api/screenshots.py`: upload OCR extraction.
- Modify `backend/app/services/ingest.py`: scan OCR extraction.
- Modify `backend/tests/*`: backend coverage.
- Modify `frontend/src/api/client.ts`: `ocr_text` type.
- Modify `frontend/src/components/ScreenshotCard.tsx`: OCR preview.
- Modify `frontend/src/pages/LibraryPage.tsx`: search helper copy.
- Modify frontend tests.

## Task 1: Models and Settings

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/models.py`
- Test: `backend/tests/test_config.py`

- [ ] Add failing tests for OCR settings defaults and `ScreenshotRecord.ocr_text` serialization.
- [ ] Run: `.venv/bin/python -m pytest backend/tests/test_config.py -v`; expect failure.
- [ ] Add `ocr_enabled`, `ocr_language`, `ocr_timeout_seconds` to `AppSettings`.
- [ ] Add `ocr_text: str | None = None` to `ScreenshotRecord`.
- [ ] Re-run config tests; expect pass.

## Task 2: DB OCR Column and FTS

**Files:**
- Modify: `backend/app/db.py`
- Test: `backend/tests/test_db.py`

- [ ] Add failing DB tests for `ocr_text` insert/get/list, legacy migration, OCR query match, category+OCR query, exact tag+OCR query, and FTS delete cleanup.
- [ ] Run: `.venv/bin/python -m pytest backend/tests/test_db.py -v`; expect failure.
- [ ] Add additive `ocr_text` column migration.
- [ ] Create `screenshots_fts` FTS5 table at startup and fail clearly if unavailable.
- [ ] Update `insert_screenshot` to accept `ocr_text` and insert FTS row.
- [ ] Update `delete_screenshot` to delete FTS row.
- [ ] Update `list_screenshots` query handling to use FTS when `query` exists while preserving category/tag filters.
- [ ] Re-run DB tests; expect pass.

## Task 3: OCR Service

**Files:**
- Create: `backend/app/services/ocr.py`
- Modify: `backend/pyproject.toml`
- Test: `backend/tests/test_ocr.py`

- [ ] Add failing tests for stripped OCR text, empty OCR result, disabled OCR, and OCR engine failure.
- [ ] Run: `.venv/bin/python -m pytest backend/tests/test_ocr.py -v`; expect failure.
- [ ] Add `pytesseract` dependency.
- [ ] Implement `OcrExtractor.extract(image_path: Path) -> str` with Pillow decode and pytesseract.
- [ ] Re-run OCR tests; expect pass.

## Task 4: Upload OCR Wiring

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/api/screenshots.py`
- Test: `backend/tests/test_screenshots_api.py`

- [ ] Add failing tests: upload stores fake OCR text and upload removes stored file when OCR fails.
- [ ] Run: `.venv/bin/python -m pytest backend/tests/test_screenshots_api.py -v`; expect failure.
- [ ] Add `ocr_extractor` app factory override and `app.state.ocr_extractor`.
- [ ] Run OCR in threadpool after classifier and before DB insert.
- [ ] Store `ocr_text` in insert call.
- [ ] Ensure OCR failure cleans stored file and returns error.
- [ ] Re-run screenshots API tests; expect pass.

## Task 5: Scan OCR Wiring

**Files:**
- Modify: `backend/app/services/ingest.py`
- Modify: `backend/app/api/watcher.py`
- Test: `backend/tests/test_ingest.py`
- Test: `backend/tests/test_watcher_api.py`

- [ ] Add failing tests: scan stores OCR text and scan OCR failure counts failed, removes copied upload, and leaves original untouched.
- [ ] Run: `.venv/bin/python -m pytest backend/tests/test_ingest.py backend/tests/test_watcher_api.py -v`; expect failure.
- [ ] Pass OCR extractor into `scan_folder_once`.
- [ ] Extract OCR before DB insert.
- [ ] Store `ocr_text` for scan records.
- [ ] Update watcher route to pass `app.state.ocr_extractor`.
- [ ] Re-run ingest/watcher tests; expect pass.

## Task 6: Frontend OCR UI

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/components/ScreenshotCard.tsx`
- Modify: `frontend/src/components/ScreenshotCard.test.tsx`
- Modify: `frontend/src/pages/LibraryPage.tsx`
- Modify: `frontend/src/pages/LibraryPage.test.tsx`

- [ ] Add failing frontend tests for OCR preview, truncation, and LibraryPage OCR helper copy.
- [ ] Run: `npm --prefix frontend test -- ScreenshotCard.test.tsx LibraryPage.test.tsx`; expect failure.
- [ ] Add `ocr_text?: string | null` to `ScreenshotRecord`.
- [ ] Render `OCR text` preview when `ocr_text` exists; truncate over 160 chars.
- [ ] Add LibraryPage helper text: `Search filenames, categories, tags, and OCR text.`
- [ ] Re-run frontend tests; expect pass.

## Task 7: Final Verification

**Files:**
- All changed files.

- [ ] Run: `.venv/bin/python -m pytest backend/tests -v`; expect pass.
- [ ] Run: `npm --prefix frontend test`; expect pass.
- [ ] Run: `npm --prefix frontend run build`; expect pass.
- [ ] Remove generated artifacts after build.
- [ ] Run final code review.

## Self-Review

Spec coverage: all OCR config, data model, service, upload, scan, FTS, frontend preview, tests covered.

Placeholder scan: no TBD/TODO/fill-in placeholders.

Type consistency: uses `ocr_text`, `OcrExtractor.extract`, `ocr_extractor`, and existing record shape consistently.
