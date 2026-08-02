# Screenshot Organizer Design

## Goal

Build a local ML-powered screenshot organizer MVP. Users upload screenshots, receive categories and tags from a zero-shot image model, and browse/search saved results.

## Scope

Included:
- React + TypeScript + Tailwind frontend.
- FastAPI backend.
- PyTorch CLIP-based zero-shot classification.
- SQLite metadata store.
- Local image storage under `data/uploads/`.
- Two UI pages: upload and library/search.

Excluded:
- Folder watcher.
- Automatic file moving.
- Cloud storage.
- Model fine-tuning.
- Multi-user auth.
- Docker deployment.

## Architecture

### Backend

`backend/` exposes REST endpoints:
- `POST /api/screenshots`: accepts image upload, stores file, runs classification, saves metadata, returns result.
- `GET /api/screenshots`: returns saved screenshots with optional search, category, and tag filters.
- `GET /api/screenshots/{id}`: returns one screenshot's metadata.
- `GET /api/screenshots/{id}/image`: streams stored image.

Core modules:
- `app/main.py`: FastAPI app setup, CORS, router registration.
- `app/api/screenshots.py`: HTTP routes.
- `app/services/storage.py`: safe local file writes and image streaming.
- `app/services/classifier.py`: CLIP model loading, prompt scoring, category/tag selection.
- `app/db.py`: SQLite connection and schema setup.
- `app/models.py`: response/data types.

### Frontend

`frontend/` contains React app:
- `/upload`: drag-and-drop upload, selected file preview, progress state, result card.
- `/library`: grid/list of saved screenshots, category filter, tag filter, keyword search.

Core modules:
- `src/api/client.ts`: typed API functions.
- `src/pages/UploadPage.tsx`: upload flow.
- `src/pages/LibraryPage.tsx`: search and browse flow.
- `src/components/Dropzone.tsx`: drag-and-drop input.
- `src/components/ScreenshotCard.tsx`: image preview and metadata.

## ML Design

Use PyTorch CLIP zero-shot classification. No training dataset needed.

Category prompts:
- `a screenshot related to work`
- `a personal screenshot`
- `a social media screenshot`
- `a screenshot of documentation`
- `a screenshot of shopping`
- `a screenshot of finance`
- `a screenshot of code`

Tag prompts:
- `meeting`
- `important`
- `recipe`
- `error message`
- `invoice`
- `chat conversation`
- `article`
- `design mockup`
- `terminal`

Classifier returns:
- best category and confidence.
- top tags above threshold, with fallback to top three tags.

Model loads once at backend startup or first request. CPU works for MVP; GPU is optional.

## Data Model

SQLite table `screenshots`:
- `id` integer primary key.
- `original_filename` text.
- `stored_filename` text.
- `path` text.
- `category` text.
- `confidence` real.
- `tags` text JSON array.
- `created_at` text ISO timestamp.

Search matches filename, category, and tags with SQLite `LIKE`. This is enough for MVP. FTS can replace it later.

## Data Flow

1. User drops image on `/upload`.
2. Frontend sends multipart upload to `POST /api/screenshots`.
3. Backend validates content type and image decode.
4. Backend writes image to `data/uploads/` using generated filename.
5. Classifier preprocesses image and scores prompts.
6. Backend inserts metadata into SQLite.
7. Frontend displays category, confidence, tags, and preview.
8. `/library` reads `GET /api/screenshots` and renders searchable cards.

## Error Handling

Backend returns clear 4xx errors for invalid files and unsupported image types. Backend returns 500 only for unexpected server failures. Frontend shows upload errors inline and keeps selected file available for retry.

## Testing

Backend:
- API tests for upload success, invalid file rejection, listing, and filtering.
- Classifier smoke test with mocked model output to avoid downloading CLIP during unit tests.
- Storage tests verify generated paths stay inside upload directory.

Frontend:
- Component tests for dropzone, result card, and library filters.
- API client tests with mocked responses.

Manual verification:
- Start backend and frontend.
- Upload PNG/JPG screenshot.
- Confirm result card renders category/tags.
- Confirm screenshot appears in library.
- Confirm search/filter changes list.

## Implementation Order

1. Create backend skeleton, SQLite schema, storage service, and upload/list endpoints.
2. Add CLIP classifier service and wire into upload endpoint.
3. Create frontend app with Tailwind and routes.
4. Build upload page and API client.
5. Build library/search page.
6. Add tests and manual verification notes.

## Future Extensions

- Folder watcher that ingests OS screenshot directory.
- Automatic folder organization after classification.
- Fine-tuned classifier using user-labeled screenshots.
- OCR for keyword search inside screenshots.
- Cloud storage backend.
- Docker Compose deployment.
