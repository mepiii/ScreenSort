# Local Automation Pack Design

## Goal

Add local screenshot automation to ScreenSort. Users can scan a configured screenshot folder, ingest matching images, classify them with the existing CLIP pipeline, and optionally organize originals into category folders.

## Scope

Included:
- One-shot folder scan API.
- Watcher status/config API.
- Copy-only ingest by default.
- Optional move-to-category mode.
- Source-path metadata.
- Upload size limit.
- Image dimension guard.
- Threadpool offload for CLIP inference.
- Library page scan button.

Excluded:
- Long-running watcher daemon controls.
- Cloud storage.
- OCR.
- Docker deployment.
- Model fine-tuning.

## Backend Design

### Configuration

Add runtime settings:
- `screenshots_dir`: source folder to scan. Default: `data/inbox`.
- `organized_dir`: category folders root. Default: `data/organized`.
- `organize_mode`: `copy` or `move`. Default: `copy`.
- `max_upload_bytes`: default 10 MB.
- `max_image_pixels`: default 16,000,000 pixels.

Settings live in `app/config.py`. App factory accepts overrides for tests.

### Data Model

Extend `screenshots` table:
- `source_path` nullable text.
- `ingest_method` text: `upload` or `scan`.

Existing rows remain valid through additive migration at startup.

### Ingest Service

Add `app/services/ingest.py`:
- validates image file extension and content.
- waits for file stability before scan ingest.
- copies source image into app upload storage.
- classifies copied image through existing classifier.
- inserts metadata with `source_path` and `ingest_method`.
- if `organize_mode = move`, moves original into `organized/<category>/` after successful DB insert.

Duplicate handling:
- skip files whose `source_path` already exists in metadata.
- upload flow keeps current behavior and sets `ingest_method = upload`.

### Safety Rules

- Default scan mode never moves originals.
- Move mode only moves files under configured `screenshots_dir`.
- Category folder names are sanitized.
- Failed classification or DB insert deletes copied app file and leaves original untouched.
- Upload and scan reject files over byte or pixel limits.
- Missing or unreadable source folders return clear 400 errors.

### API

Add `app/api/watcher.py`:
- `GET /api/watcher/status`
  - returns `screenshots_dir`, `organized_dir`, `organize_mode`, and whether source directory exists.
- `POST /api/watcher/scan`
  - scans configured folder once.
  - returns counts: `seen`, `ingested`, `skipped`, `failed`.
  - returns ingested records.

Update upload endpoint:
- enforce file size limit before saving.
- enforce image pixel limit after decode.
- run classifier in threadpool.
- store `ingest_method = upload`.

## Frontend Design

Update `LibraryPage`:
- add “Scan folder” button.
- call `POST /api/watcher/scan`.
- show scan summary.
- refresh library after successful scan.
- show watcher status text: source folder and mode.

Add API client functions:
- `getWatcherStatus()`.
- `scanWatcherFolder()`.

No new route needed.

## Testing

Backend tests:
- upload rejects oversized file.
- upload rejects image above pixel limit.
- scan ingests valid images from temp source folder.
- scan skips already ingested `source_path`.
- copy mode leaves original in place.
- move mode moves original into sanitized category folder.
- classifier failures clean copied app file and leave original untouched.
- watcher status reports missing source folder.

Frontend tests:
- library page renders watcher status.
- scan button calls scan API.
- scan success shows counts and refreshes list.
- scan error shows alert.

Manual verification:
- create a temp screenshot folder with PNG/JPG files.
- start backend with `screenshots_dir` pointing there.
- click “Scan folder”.
- verify library shows ingested screenshots.
- verify originals remain in copy mode.
- enable move mode in config and verify originals move to category folders.

## Implementation Order

1. Add config and DB additive fields.
2. Add upload size/pixel guards.
3. Add threadpool classifier offload.
4. Add ingest service.
5. Add watcher API.
6. Add frontend API functions.
7. Add library scan UI.
8. Run backend/frontend tests and manual check.
