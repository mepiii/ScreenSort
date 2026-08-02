# OCR and Full-Text Search Design

## Goal

Add text-aware screenshot search. ScreenSort extracts OCR text from uploads and folder scans, stores it with screenshot metadata, and searches filename, category, tags, and OCR text through SQLite FTS.

## Scope

Included:
- OCR extraction for upload ingest.
- OCR extraction for folder scan ingest.
- Additive `ocr_text` metadata field.
- SQLite FTS5 search index.
- Search endpoint upgrade that uses FTS for `query`.
- Frontend library cards show short OCR snippets when available.
- Upload and scan flows keep working when OCR returns no text.

Excluded:
- OCR language selection UI.
- OCR bounding boxes.
- OCR correction editor.
- Cloud OCR APIs.
- Background reprocessing jobs for old screenshots.

## Backend Design

### Configuration

Add runtime settings in `app/config.py`:
- `ocr_enabled`: default `True`.
- `ocr_language`: default `eng`.
- `ocr_timeout_seconds`: default `10`.

Tests may disable OCR by passing a fake extractor or `ocr_enabled=False`.

### Data Model

Extend `screenshots` table:
- `ocr_text` nullable text, default `NULL`.

Extend `ScreenshotRecord` with:
- `ocr_text: str | None = None`.

Existing rows remain valid through startup migration.

### OCR Service

Add `app/services/ocr.py`:
- `OcrExtractor.extract(image_path: Path) -> str`.
- Uses `pytesseract.image_to_string` when OCR is enabled.
- Opens images through Pillow before OCR to reject invalid input at boundary.
- Returns stripped text.
- Returns empty string when Tesseract produces no text.
- Raises `RuntimeError("OCR failed.")` for OCR engine failures.

The app factory accepts an OCR extractor override for tests.

### Ingest Flow

Upload flow:
1. Validate size and pixels.
2. Store image copy.
3. Run classifier in threadpool.
4. Run OCR in threadpool.
5. Insert screenshot metadata with `ocr_text`.
6. Clean stored file on classifier, OCR, or DB failure.

Folder scan flow:
1. Copy source image into upload storage.
2. Run classifier in threadpool caller context.
3. Run OCR.
4. Insert metadata with `source_path`, `ingest_method="scan"`, and `ocr_text`.
5. Move original only after DB insert succeeds in move mode.
6. Clean copied file and leave original untouched on OCR failure.

### SQLite FTS

Create FTS5 virtual table:
- `screenshots_fts(screenshot_id UNINDEXED, original_filename, category, tags_text, ocr_text)`.

Keep FTS synchronized in DB helper functions:
- Insert FTS row after screenshot insert.
- Delete FTS row when screenshot deleted.

Use parameterized SQL only.

`list_screenshots(query=...)` behavior:
- If `query` is empty, current filtering remains.
- If `query` is present, search FTS with escaped tokens.
- Combine with `category` and exact `tag` filters.
- Return same `ScreenshotRecord` shape.

If SQLite lacks FTS5, app startup should fail fast with clear error: `SQLite FTS5 support is required.`

## Frontend Design

Update API types:
- Add `ocr_text?: string | null` to `ScreenshotRecord`.

Update `ScreenshotCard`:
- Show an OCR preview below tags when text exists.
- Limit preview to 160 characters.
- Label it `OCR text`.

Update `LibraryPage` copy:
- Search input remains one field.
- Placeholder or helper text says search covers filenames, categories, tags, and OCR text.

No new route needed.

## Safety Rules

- OCR never runs before image validation.
- OCR failures fail that upload or scan item; they do not create partial DB rows.
- Folder scan failure leaves original source file untouched.
- Search input never interpolates raw user text into SQL.
- OCR extraction runs outside async event loop.

## Testing

Backend tests:
- Upload stores OCR text from fake extractor.
- Upload cleans stored file when OCR fails.
- Scan stores OCR text from fake extractor.
- Scan OCR failure counts failed and leaves original untouched.
- DB migration adds `ocr_text` and FTS table idempotently.
- Query matches OCR text.
- Query combines OCR search with category filter.
- Query combines OCR search with exact tag filter.
- FTS delete removes deleted screenshot from search.

Frontend tests:
- API type accepts `ocr_text`.
- `ScreenshotCard` renders OCR preview.
- `ScreenshotCard` truncates long OCR text.
- `LibraryPage` search helper mentions OCR text.

Manual verification:
- Upload screenshot containing visible text.
- Search for that text in Library.
- Verify matching screenshot appears.
- Scan folder with text screenshot.
- Search for scanned text.

## Implementation Order

1. Add config and model fields.
2. Add DB migration and FTS helpers.
3. Add OCR service.
4. Wire OCR into upload flow.
5. Wire OCR into scan flow.
6. Update frontend API type and card UI.
7. Run backend/frontend tests.
8. Manually verify OCR search if Tesseract is installed.
