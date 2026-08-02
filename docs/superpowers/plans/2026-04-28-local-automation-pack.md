# Local Automation Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add local folder scan automation, safe ingest, optional category organization, upload guards, and library scan UI.

**Architecture:** Backend adds settings, additive SQLite fields, reusable ingest service, watcher API, and threadpool classifier execution. Frontend extends the existing API client and LibraryPage with watcher status, scan action, summary, and refresh behavior.

**Tech Stack:** FastAPI, SQLite, Pillow, Starlette threadpool, pytest, React, TypeScript, Vitest, TailwindCSS.

---

## File Structure

Backend:
- Create: `backend/app/config.py` — runtime settings dataclass.
- Modify: `backend/app/main.py` — app factory accepts settings and includes watcher router.
- Modify: `backend/app/models.py` — add watcher/scan models and metadata fields.
- Modify: `backend/app/db.py` — additive columns, source-path lookup, ingest metadata.
- Modify: `backend/app/api/screenshots.py` — upload guards and threadpool classify.
- Create: `backend/app/services/ingest.py` — scan ingest and optional move organization.
- Create: `backend/app/api/watcher.py` — status and scan endpoints.
- Create: `backend/tests/test_config.py` — settings tests.
- Modify: `backend/tests/test_db.py` — additive metadata tests.
- Modify: `backend/tests/test_screenshots_api.py` — upload guard tests.
- Create: `backend/tests/test_ingest.py` — scan ingest tests.
- Create: `backend/tests/test_watcher_api.py` — watcher API tests.

Frontend:
- Modify: `frontend/src/api/client.ts` — watcher types/functions.
- Modify: `frontend/src/api/client.test.ts` — watcher API tests.
- Modify: `frontend/src/pages/LibraryPage.tsx` — status, scan button, summary, refresh.
- Modify: `frontend/src/pages/LibraryPage.test.tsx` — scan UI tests.

---

## Task 1: Backend Config and DB Metadata

**Files:**
- Create: `backend/app/config.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/models.py`
- Modify: `backend/app/db.py`
- Create: `backend/tests/test_config.py`
- Modify: `backend/tests/test_db.py`

- [ ] **Step 1: Write failing config tests**

Create `backend/tests/test_config.py`:

```python
from pathlib import Path

from app.config import AppSettings


def test_app_settings_defaults():
    settings = AppSettings()

    assert settings.screenshots_dir == Path("data/inbox")
    assert settings.organized_dir == Path("data/organized")
    assert settings.organize_mode == "copy"
    assert settings.max_upload_bytes == 10 * 1024 * 1024
    assert settings.max_image_pixels == 16_000_000


def test_app_settings_rejects_invalid_mode():
    try:
        AppSettings(organize_mode="delete")
    except ValueError as exc:
        assert "organize_mode" in str(exc)
    else:
        raise AssertionError("invalid organize_mode should fail")
```

- [ ] **Step 2: Write failing DB metadata tests**

Append to `backend/tests/test_db.py`:

```python

def test_insert_screenshot_defaults_upload_metadata(tmp_path):
    db_path = tmp_path / "screenshots.db"
    init_db(db_path)

    record = insert_screenshot(
        db_path,
        original_filename="sample.png",
        stored_filename="abc.png",
        path="data/uploads/abc.png",
        category="code",
        confidence=0.9,
        tags=["terminal"],
    )

    assert record.source_path is None
    assert record.ingest_method == "upload"


def test_get_screenshot_by_source_path(tmp_path):
    from app.db import get_screenshot_by_source_path

    db_path = tmp_path / "screenshots.db"
    init_db(db_path)
    source_path = str(tmp_path / "source.png")
    inserted = insert_screenshot(
        db_path,
        original_filename="source.png",
        stored_filename="stored.png",
        path="data/uploads/stored.png",
        category="work",
        confidence=0.8,
        tags=["meeting"],
        source_path=source_path,
        ingest_method="scan",
    )

    loaded = get_screenshot_by_source_path(db_path, source_path)

    assert loaded is not None
    assert loaded.id == inserted.id
    assert loaded.ingest_method == "scan"
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```bash
cd backend && ../.venv/bin/python -m pytest tests/test_config.py tests/test_db.py -v
```

Expected: FAIL because `app.config`, new model fields, and source-path helper do not exist.

- [ ] **Step 4: Implement config**

Create `backend/app/config.py`:

```python
"""Purpose: Runtime settings. Callers: app factory, ingest, APIs. Deps: dataclasses, pathlib. API: AppSettings. Side effects: none."""
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

OrganizeMode = Literal["copy", "move"]


@dataclass(frozen=True)
class AppSettings:
    screenshots_dir: Path = Path("data/inbox")
    organized_dir: Path = Path("data/organized")
    organize_mode: OrganizeMode = "copy"
    max_upload_bytes: int = 10 * 1024 * 1024
    max_image_pixels: int = 16_000_000

    def __post_init__(self) -> None:
        if self.organize_mode not in {"copy", "move"}:
            raise ValueError("organize_mode must be 'copy' or 'move'")
```

- [ ] **Step 5: Update models**

Modify `ScreenshotRecord` in `backend/app/models.py` to include:

```python
    source_path: str | None = None
    ingest_method: str = "upload"
```

Add models:

```python
class WatcherStatus(BaseModel):
    screenshots_dir: str
    organized_dir: str
    organize_mode: str
    source_exists: bool


class ScanSummary(BaseModel):
    seen: int
    ingested: int
    skipped: int
    failed: int
    records: list[ScreenshotRecord]
```

- [ ] **Step 6: Update DB schema and helpers**

Modify `backend/app/db.py`:

- Add columns to `SCHEMA`:

```sql
    source_path TEXT,
    ingest_method TEXT NOT NULL DEFAULT 'upload'
```

- Add migration statements in `init_db` after `conn.execute(SCHEMA)`:

```python
        columns = {row[1] for row in conn.execute("PRAGMA table_info(screenshots)").fetchall()}
        if "source_path" not in columns:
            conn.execute("ALTER TABLE screenshots ADD COLUMN source_path TEXT")
        if "ingest_method" not in columns:
            conn.execute("ALTER TABLE screenshots ADD COLUMN ingest_method TEXT NOT NULL DEFAULT 'upload'")
```

- Update `_row_to_record`:

```python
        source_path=row["source_path"],
        ingest_method=row["ingest_method"],
```

- Update `insert_screenshot` signature:

```python
    source_path: str | None = None,
    ingest_method: str = "upload",
```

- Insert `source_path` and `ingest_method` into SQL.

- Add helper:

```python
def get_screenshot_by_source_path(db_path: Path, source_path: str) -> ScreenshotRecord | None:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM screenshots WHERE source_path = ?", (source_path,)).fetchone()
    return _row_to_record(row) if row else None
```

- [ ] **Step 7: Update app factory settings**

Modify `backend/app/main.py` `create_app` signature:

```python
from app.config import AppSettings


def create_app(
    db_path: Path = Path("data/screenshots.db"),
    upload_dir: Path = Path("data/uploads"),
    classifier: Any | None = None,
    settings: AppSettings | None = None,
) -> FastAPI:
```

Inside factory:

```python
    app.state.settings = settings or AppSettings()
```

- [ ] **Step 8: Run tests to verify pass**

Run:

```bash
cd backend && ../.venv/bin/python -m pytest tests/test_config.py tests/test_db.py -v
```

Expected: PASS.

---

## Task 2: Upload Guards and Threadpool Classification

**Files:**
- Modify: `backend/app/api/screenshots.py`
- Modify: `backend/tests/test_screenshots_api.py`

- [ ] **Step 1: Write failing upload guard tests**

Append to `backend/tests/test_screenshots_api.py`:

```python
from app.config import AppSettings
from app.main import create_app
from fastapi.testclient import TestClient


def test_upload_rejects_file_over_size_limit(tmp_path):
    app = create_app(
        db_path=tmp_path / "screenshots.db",
        upload_dir=tmp_path / "uploads",
        classifier=FakeClassifier(),
        settings=AppSettings(max_upload_bytes=4),
    )
    client = TestClient(app)

    response = client.post(
        "/api/screenshots",
        files={"file": ("too-big.png", png_bytes(), "image/png")},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "Upload exceeds size limit."


def test_upload_rejects_image_over_pixel_limit(tmp_path):
    app = create_app(
        db_path=tmp_path / "screenshots.db",
        upload_dir=tmp_path / "uploads",
        classifier=FakeClassifier(),
        settings=AppSettings(max_image_pixels=4),
    )
    client = TestClient(app)

    response = client.post(
        "/api/screenshots",
        files={"file": ("large.png", png_bytes(), "image/png")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Image dimensions exceed limit."
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
cd backend && ../.venv/bin/python -m pytest tests/test_screenshots_api.py::test_upload_rejects_file_over_size_limit tests/test_screenshots_api.py::test_upload_rejects_image_over_pixel_limit -v
```

Expected: FAIL because guards are not implemented.

- [ ] **Step 3: Add guard helpers and threadpool offload**

Modify `backend/app/api/screenshots.py`:

- import:

```python
from starlette.concurrency import run_in_threadpool
```

- after `content = await file.read()` add:

```python
    if len(content) > request.app.state.settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Upload exceeds size limit.")
```

- after opening image, before `image.verify()` or via a second open, check pixels:

```python
        with Image.open(stored.path) as image:
            if image.width * image.height > request.app.state.settings.max_image_pixels:
                stored.path.unlink(missing_ok=True)
                raise HTTPException(status_code=400, detail="Image dimensions exceed limit.")
            image.verify()
```

- replace classifier call:

```python
        classification = await run_in_threadpool(request.app.state.classifier.classify, stored.path)
```

- update insert call with:

```python
        ingest_method="upload",
```

- [ ] **Step 4: Run endpoint tests**

Run:

```bash
cd backend && ../.venv/bin/python -m pytest tests/test_screenshots_api.py -v
```

Expected: PASS.

---

## Task 3: Ingest Service

**Files:**
- Create: `backend/app/services/ingest.py`
- Create: `backend/tests/test_ingest.py`

- [ ] **Step 1: Write failing ingest tests**

Create `backend/tests/test_ingest.py`:

```python
from io import BytesIO
from pathlib import Path

from PIL import Image

from app.config import AppSettings
from app.db import init_db, list_screenshots
from app.models import ClassificationResult
from app.services.ingest import scan_folder_once


class FakeClassifier:
    def classify(self, image_path: Path):
        return ClassificationResult(category="code", confidence=0.93, tags=["terminal", "error"])


class FailingClassifier:
    def classify(self, image_path: Path):
        raise RuntimeError("classifier failed")


def write_png(path: Path) -> None:
    buffer = BytesIO()
    Image.new("RGB", (8, 8), color="black").save(buffer, format="PNG")
    path.write_bytes(buffer.getvalue())


def test_scan_folder_ingests_image_in_copy_mode(tmp_path):
    source_dir = tmp_path / "screenshots"
    upload_dir = tmp_path / "uploads"
    db_path = tmp_path / "screenshots.db"
    source_dir.mkdir()
    source = source_dir / "shot.png"
    write_png(source)
    init_db(db_path)

    summary = scan_folder_once(db_path, upload_dir, FakeClassifier(), AppSettings(screenshots_dir=source_dir))

    assert summary.seen == 1
    assert summary.ingested == 1
    assert summary.skipped == 0
    assert summary.failed == 0
    assert source.exists()
    records = list_screenshots(db_path)
    assert records[0].source_path == str(source.resolve())
    assert records[0].ingest_method == "scan"


def test_scan_folder_skips_existing_source_path(tmp_path):
    source_dir = tmp_path / "screenshots"
    upload_dir = tmp_path / "uploads"
    db_path = tmp_path / "screenshots.db"
    source_dir.mkdir()
    source = source_dir / "shot.png"
    write_png(source)
    init_db(db_path)

    scan_folder_once(db_path, upload_dir, FakeClassifier(), AppSettings(screenshots_dir=source_dir))
    summary = scan_folder_once(db_path, upload_dir, FakeClassifier(), AppSettings(screenshots_dir=source_dir))

    assert summary.seen == 1
    assert summary.ingested == 0
    assert summary.skipped == 1


def test_scan_folder_moves_original_in_move_mode(tmp_path):
    source_dir = tmp_path / "screenshots"
    organized_dir = tmp_path / "organized"
    upload_dir = tmp_path / "uploads"
    db_path = tmp_path / "screenshots.db"
    source_dir.mkdir()
    source = source_dir / "shot.png"
    write_png(source)
    init_db(db_path)

    summary = scan_folder_once(
        db_path,
        upload_dir,
        FakeClassifier(),
        AppSettings(screenshots_dir=source_dir, organized_dir=organized_dir, organize_mode="move"),
    )

    assert summary.ingested == 1
    assert not source.exists()
    assert (organized_dir / "code" / "shot.png").exists()


def test_scan_folder_cleans_copy_when_classifier_fails(tmp_path):
    source_dir = tmp_path / "screenshots"
    upload_dir = tmp_path / "uploads"
    db_path = tmp_path / "screenshots.db"
    source_dir.mkdir()
    source = source_dir / "shot.png"
    write_png(source)
    init_db(db_path)

    summary = scan_folder_once(db_path, upload_dir, FailingClassifier(), AppSettings(screenshots_dir=source_dir))

    assert summary.seen == 1
    assert summary.failed == 1
    assert source.exists()
    assert list(upload_dir.glob("*")) == []
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
cd backend && ../.venv/bin/python -m pytest tests/test_ingest.py -v
```

Expected: FAIL because `app.services.ingest` does not exist.

- [ ] **Step 3: Implement ingest service**

Create `backend/app/services/ingest.py`:

```python
"""Purpose: Folder scan ingest. Callers: watcher API/tests. Deps: pathlib, shutil, PIL, DB, storage. API: scan_folder_once. Side effects: copies files, may move originals, writes DB."""
import re
import shutil
import time
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

from app.config import AppSettings
from app.db import get_screenshot_by_source_path, insert_screenshot
from app.models import ScanSummary, ScreenshotRecord
from app.services.storage import save_upload_bytes

ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def _is_stable(path: Path, delay_seconds: float = 0.05) -> bool:
    first = path.stat().st_size
    time.sleep(delay_seconds)
    return path.exists() and path.stat().st_size == first


def _safe_category(category: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", category.strip().lower()).strip("-")
    return value or "uncategorized"


def _validate_image(path: Path, settings: AppSettings) -> None:
    if path.stat().st_size > settings.max_upload_bytes:
        raise ValueError("Upload exceeds size limit.")
    with Image.open(path) as image:
        if image.width * image.height > settings.max_image_pixels:
            raise ValueError("Image dimensions exceed limit.")
        image.verify()


def _move_original(source: Path, category: str, settings: AppSettings) -> None:
    source_root = settings.screenshots_dir.resolve()
    resolved_source = source.resolve()
    if source_root not in resolved_source.parents and resolved_source.parent != source_root:
        raise ValueError("source file is outside screenshots_dir")
    target_dir = settings.organized_dir / _safe_category(category)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source.name
    if target.exists():
        target = target_dir / f"{source.stem}-{int(time.time())}{source.suffix}"
    shutil.move(str(source), str(target))


def _ingest_one(db_path: Path, upload_dir: Path, classifier: Any, settings: AppSettings, source: Path) -> ScreenshotRecord:
    resolved_source = source.resolve()
    existing = get_screenshot_by_source_path(db_path, str(resolved_source))
    if existing is not None:
        raise FileExistsError(str(resolved_source))
    _validate_image(resolved_source, settings)
    stored = save_upload_bytes(upload_dir, source.name, resolved_source.read_bytes())
    try:
        result = classifier.classify(stored.path)
        record = insert_screenshot(
            db_path,
            original_filename=source.name,
            stored_filename=stored.stored_filename,
            path=str(stored.path),
            category=result.category,
            confidence=result.confidence,
            tags=result.tags,
            source_path=str(resolved_source),
            ingest_method="scan",
        )
        if settings.organize_mode == "move":
            _move_original(resolved_source, result.category, settings)
        return record
    except Exception:
        stored.path.unlink(missing_ok=True)
        raise


def scan_folder_once(db_path: Path, upload_dir: Path, classifier: Any, settings: AppSettings) -> ScanSummary:
    source_dir = settings.screenshots_dir
    if not source_dir.exists() or not source_dir.is_dir():
        raise FileNotFoundError(str(source_dir))
    seen = 0
    ingested = 0
    skipped = 0
    failed = 0
    records: list[ScreenshotRecord] = []
    for source in sorted(source_dir.iterdir()):
        if not source.is_file() or source.suffix.lower() not in ALLOWED_SUFFIXES:
            continue
        seen += 1
        if not _is_stable(source):
            skipped += 1
            continue
        try:
            record = _ingest_one(db_path, upload_dir, classifier, settings, source)
        except FileExistsError:
            skipped += 1
        except (OSError, ValueError, UnidentifiedImageError, RuntimeError):
            failed += 1
        else:
            ingested += 1
            records.append(record)
    return ScanSummary(seen=seen, ingested=ingested, skipped=skipped, failed=failed, records=records)
```

- [ ] **Step 4: Run ingest tests**

Run:

```bash
cd backend && ../.venv/bin/python -m pytest tests/test_ingest.py -v
```

Expected: PASS.

---

## Task 4: Watcher API

**Files:**
- Create: `backend/app/api/watcher.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_watcher_api.py`

- [ ] **Step 1: Write failing watcher API tests**

Create `backend/tests/test_watcher_api.py`:

```python
from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.config import AppSettings
from app.main import create_app
from app.models import ClassificationResult


class FakeClassifier:
    def classify(self, image_path):
        return ClassificationResult(category="code", confidence=0.93, tags=["terminal"])


def png_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (8, 8), color="black").save(buffer, format="PNG")
    return buffer.getvalue()


def test_watcher_status_reports_config_and_source_exists(tmp_path):
    source_dir = tmp_path / "screenshots"
    source_dir.mkdir()
    app = create_app(
        db_path=tmp_path / "screenshots.db",
        upload_dir=tmp_path / "uploads",
        classifier=FakeClassifier(),
        settings=AppSettings(screenshots_dir=source_dir, organized_dir=tmp_path / "organized", organize_mode="copy"),
    )
    client = TestClient(app)

    response = client.get("/api/watcher/status")

    assert response.status_code == 200
    assert response.json()["screenshots_dir"] == str(source_dir)
    assert response.json()["source_exists"] is True


def test_scan_endpoint_ingests_folder(tmp_path):
    source_dir = tmp_path / "screenshots"
    source_dir.mkdir()
    (source_dir / "shot.png").write_bytes(png_bytes())
    app = create_app(
        db_path=tmp_path / "screenshots.db",
        upload_dir=tmp_path / "uploads",
        classifier=FakeClassifier(),
        settings=AppSettings(screenshots_dir=source_dir, organized_dir=tmp_path / "organized", organize_mode="copy"),
    )
    client = TestClient(app)

    response = client.post("/api/watcher/scan")

    assert response.status_code == 200
    body = response.json()
    assert body["seen"] == 1
    assert body["ingested"] == 1
    assert body["records"][0]["category"] == "code"


def test_scan_endpoint_returns_400_for_missing_source(tmp_path):
    app = create_app(
        db_path=tmp_path / "screenshots.db",
        upload_dir=tmp_path / "uploads",
        classifier=FakeClassifier(),
        settings=AppSettings(screenshots_dir=tmp_path / "missing"),
    )
    client = TestClient(app)

    response = client.post("/api/watcher/scan")

    assert response.status_code == 400
    assert response.json()["detail"] == "Screenshot source folder does not exist."
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
cd backend && ../.venv/bin/python -m pytest tests/test_watcher_api.py -v
```

Expected: FAIL because watcher API does not exist.

- [ ] **Step 3: Implement watcher API**

Create `backend/app/api/watcher.py`:

```python
"""Purpose: Watcher scan API. Callers: frontend/tests. Deps: FastAPI, ingest service. API: router. Side effects: scans source folder and writes metadata."""
from fastapi import APIRouter, HTTPException, Request

from app.models import ScanSummary, WatcherStatus
from app.services.ingest import scan_folder_once

router = APIRouter(prefix="/watcher")


@router.get("/status", response_model=WatcherStatus)
def watcher_status(request: Request) -> WatcherStatus:
    settings = request.app.state.settings
    return WatcherStatus(
        screenshots_dir=str(settings.screenshots_dir),
        organized_dir=str(settings.organized_dir),
        organize_mode=settings.organize_mode,
        source_exists=settings.screenshots_dir.exists() and settings.screenshots_dir.is_dir(),
    )


@router.post("/scan", response_model=ScanSummary)
def scan_watcher_folder(request: Request) -> ScanSummary:
    try:
        return scan_folder_once(
            request.app.state.db_path,
            request.app.state.upload_dir,
            request.app.state.classifier,
            request.app.state.settings,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail="Screenshot source folder does not exist.") from exc
```

Modify `backend/app/main.py`:

```python
from app.api.watcher import router as watcher_router
```

and include:

```python
    app.include_router(watcher_router, prefix="/api")
```

- [ ] **Step 4: Run watcher API tests**

Run:

```bash
cd backend && ../.venv/bin/python -m pytest tests/test_watcher_api.py -v
```

Expected: PASS.

---

## Task 5: Frontend Watcher API Client

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/api/client.test.ts`

- [ ] **Step 1: Write failing frontend API tests**

Append to `frontend/src/api/client.test.ts`:

```ts
import { getWatcherStatus, scanWatcherFolder } from './client';

it('gets watcher status', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
    screenshots_dir: 'data/inbox',
    organized_dir: 'data/organized',
    organize_mode: 'copy',
    source_exists: true,
  }), { status: 200 })));

  const status = await getWatcherStatus();

  expect(fetch).toHaveBeenCalledWith('http://localhost:8000/api/watcher/status');
  expect(status.source_exists).toBe(true);
});

it('scans watcher folder', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({
    seen: 1,
    ingested: 1,
    skipped: 0,
    failed: 0,
    records: [],
  }), { status: 200 })));

  const summary = await scanWatcherFolder();

  expect(fetch).toHaveBeenCalledWith('http://localhost:8000/api/watcher/scan', { method: 'POST' });
  expect(summary.ingested).toBe(1);
});
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
cd frontend && npm test -- src/api/client.test.ts
```

Expected: FAIL because watcher functions are not exported.

- [ ] **Step 3: Implement client functions**

Modify `frontend/src/api/client.ts`:

```ts
export type WatcherStatus = {
  screenshots_dir: string;
  organized_dir: string;
  organize_mode: 'copy' | 'move';
  source_exists: boolean;
};

export type ScanSummary = {
  seen: number;
  ingested: number;
  skipped: number;
  failed: number;
  records: ScreenshotRecord[];
};

export async function getWatcherStatus(): Promise<WatcherStatus> {
  const response = await fetch(`${API_BASE_URL}/watcher/status`);
  return parseResponse<WatcherStatus>(response);
}

export async function scanWatcherFolder(): Promise<ScanSummary> {
  const response = await fetch(`${API_BASE_URL}/watcher/scan`, { method: 'POST' });
  return parseResponse<ScanSummary>(response);
}
```

- [ ] **Step 4: Run client tests**

Run:

```bash
cd frontend && npm test -- src/api/client.test.ts
```

Expected: PASS.

---

## Task 6: Library Scan UI

**Files:**
- Modify: `frontend/src/pages/LibraryPage.tsx`
- Modify: `frontend/src/pages/LibraryPage.test.tsx`

- [ ] **Step 1: Write failing library scan tests**

Append to `frontend/src/pages/LibraryPage.test.tsx`:

```tsx
it('shows watcher status and scans folder', async () => {
  const user = userEvent.setup();
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes('/watcher/status')) {
      return new Response(JSON.stringify({
        screenshots_dir: 'data/inbox',
        organized_dir: 'data/organized',
        organize_mode: 'copy',
        source_exists: true,
      }), { status: 200 });
    }
    if (url.includes('/watcher/scan')) {
      return new Response(JSON.stringify({ seen: 1, ingested: 1, skipped: 0, failed: 0, records: [] }), { status: 200 });
    }
    return new Response(JSON.stringify(records), { status: 200 });
  }));

  render(<LibraryPage />);

  expect(await screen.findByText(/Source: data\/inbox/)).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Scan folder' }));

  expect(await screen.findByText('Scan complete: 1 ingested, 0 skipped, 0 failed.')).toBeInTheDocument();
  expect(fetch).toHaveBeenCalledWith('http://localhost:8000/api/watcher/scan', { method: 'POST' });
});

it('shows scan errors', async () => {
  const user = userEvent.setup();
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes('/watcher/status')) {
      return new Response(JSON.stringify({ screenshots_dir: 'missing', organized_dir: 'data/organized', organize_mode: 'copy', source_exists: false }), { status: 200 });
    }
    if (url.includes('/watcher/scan')) {
      return new Response(JSON.stringify({ detail: 'Screenshot source folder does not exist.' }), { status: 400 });
    }
    return new Response(JSON.stringify(records), { status: 200 });
  }));

  render(<LibraryPage />);
  await user.click(await screen.findByRole('button', { name: 'Scan folder' }));

  expect(await screen.findByRole('alert')).toHaveTextContent('Screenshot source folder does not exist.');
});
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
cd frontend && npm test -- src/pages/LibraryPage.test.tsx
```

Expected: FAIL because LibraryPage has no watcher UI.

- [ ] **Step 3: Implement watcher UI**

Modify `frontend/src/pages/LibraryPage.tsx`:

- update imports:

```ts
import { getWatcherStatus, listScreenshots, scanWatcherFolder, ScanSummary, ScreenshotRecord, WatcherStatus } from '../api/client';
```

- add state:

```ts
  const [watcherStatus, setWatcherStatus] = useState<WatcherStatus | null>(null);
  const [scanSummary, setScanSummary] = useState<ScanSummary | null>(null);
  const [scanError, setScanError] = useState<string | null>(null);
  const [scanning, setScanning] = useState(false);
```

- add status effect:

```ts
  useEffect(() => {
    let cancelled = false;
    getWatcherStatus()
      .then((status) => {
        if (!cancelled) setWatcherStatus(status);
      })
      .catch(() => {
        if (!cancelled) setWatcherStatus(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);
```

- extract load function if needed or trigger refresh with state counter.

- add scan handler:

```ts
  const scanFolder = async () => {
    setScanning(true);
    setScanError(null);
    try {
      const summary = await scanWatcherFolder();
      setScanSummary(summary);
      setRefreshKey((value) => value + 1);
    } catch (caught) {
      setScanError(caught instanceof Error ? caught.message : 'Scan failed.');
    } finally {
      setScanning(false);
    }
  };
```

- add UI above filters:

```tsx
      <div className="mt-6 rounded-2xl border border-slate-800 bg-slate-900 p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="font-semibold text-white">Folder scan</h2>
            <p className="mt-1 text-sm text-slate-400">
              {watcherStatus ? `Source: ${watcherStatus.screenshots_dir} · Mode: ${watcherStatus.organize_mode}` : 'Watcher status unavailable'}
            </p>
          </div>
          <button className="rounded-xl bg-cyan-400 px-4 py-2 font-semibold text-slate-950 disabled:opacity-50" disabled={scanning} onClick={scanFolder}>
            {scanning ? 'Scanning…' : 'Scan folder'}
          </button>
        </div>
        {scanSummary && <p className="mt-3 text-sm text-emerald-300">Scan complete: {scanSummary.ingested} ingested, {scanSummary.skipped} skipped, {scanSummary.failed} failed.</p>}
        {scanError && <p role="alert" className="mt-3 text-sm text-red-300">{scanError}</p>}
      </div>
```

- [ ] **Step 4: Run library tests**

Run:

```bash
cd frontend && npm test -- src/pages/LibraryPage.test.tsx
```

Expected: PASS.

---

## Task 7: Final Verification

**Files:**
- Modify only if verification fails.

- [ ] **Step 1: Run backend tests**

Run:

```bash
.venv/bin/python -m pytest backend/tests -v
```

Expected: all tests PASS.

- [ ] **Step 2: Run frontend tests and build**

Run:

```bash
cd frontend && npm test && npm run build
```

Expected: all tests PASS and build succeeds.

- [ ] **Step 3: Remove generated frontend artifacts**

Run:

```bash
rm -rf frontend/dist frontend/tsconfig.tsbuildinfo
```

Expected: artifacts removed.

- [ ] **Step 4: Manual check**

Run backend and frontend. Use a temp screenshot folder. Verify scan status, scan summary, library refresh, and copy mode leaves originals in place.

---

## Self-Review

Spec coverage:
- config: Task 1.
- source metadata: Task 1.
- upload guards: Task 2.
- threadpool offload: Task 2.
- ingest service, copy/move, duplicate skip, safety: Task 3.
- watcher API: Task 4.
- frontend client: Task 5.
- scan UI: Task 6.
- verification: Task 7.

Placeholder scan: no TBD/TODO/fill-later language.

Type consistency: `AppSettings`, `WatcherStatus`, `ScanSummary`, `ScreenshotRecord`, and API names match across tasks.
