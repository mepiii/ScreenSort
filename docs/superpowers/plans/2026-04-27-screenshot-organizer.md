# Screenshot Organizer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local ML-powered screenshot organizer MVP where users upload screenshots, get CLIP-based categories/tags, and browse/search saved results.

**Architecture:** FastAPI backend stores uploaded images locally, classifies them with PyTorch CLIP, and persists metadata in SQLite. React + TypeScript + Tailwind frontend provides upload and library/search pages through typed API calls.

**Tech Stack:** Python 3, FastAPI, PyTorch, Transformers CLIP, Pillow, SQLite, pytest, React, TypeScript, Vite, TailwindCSS, Vitest, React Testing Library.

---

## File Structure

### Backend

- Create: `backend/pyproject.toml` — package metadata, runtime deps, test deps.
- Create: `backend/app/__init__.py` — Python package marker.
- Create: `backend/app/main.py` — FastAPI app, CORS, router registration.
- Create: `backend/app/models.py` — dataclasses/Pydantic response models.
- Create: `backend/app/db.py` — SQLite schema, insert/list/get helpers.
- Create: `backend/app/api/__init__.py` — API package marker.
- Create: `backend/app/api/screenshots.py` — upload/list/detail/image routes.
- Create: `backend/app/services/__init__.py` — services package marker.
- Create: `backend/app/services/storage.py` — local upload directory, safe filenames, image streaming.
- Create: `backend/app/services/classifier.py` — CLIP wrapper and prompt scoring.
- Create: `backend/tests/conftest.py` — temp app/db/upload fixtures.
- Create: `backend/tests/test_storage.py` — storage path safety tests.
- Create: `backend/tests/test_screenshots_api.py` — API behavior tests.
- Create: `backend/tests/test_classifier.py` — classifier selection tests with fake scores.

### Frontend

- Create: `frontend/package.json` — scripts and dependencies.
- Create: `frontend/index.html` — Vite entry document.
- Create: `frontend/tsconfig.json` — TypeScript config.
- Create: `frontend/vite.config.ts` — Vite + React config.
- Create: `frontend/tailwind.config.js` — Tailwind content config.
- Create: `frontend/postcss.config.js` — Tailwind PostCSS config.
- Create: `frontend/src/main.tsx` — React root.
- Create: `frontend/src/App.tsx` — router shell and navigation.
- Create: `frontend/src/index.css` — Tailwind directives and base styles.
- Create: `frontend/src/api/client.ts` — typed fetch API helpers.
- Create: `frontend/src/components/Dropzone.tsx` — drag/drop file picker.
- Create: `frontend/src/components/ScreenshotCard.tsx` — saved screenshot card.
- Create: `frontend/src/pages/UploadPage.tsx` — upload workflow.
- Create: `frontend/src/pages/LibraryPage.tsx` — search and filter workflow.
- Create: `frontend/src/test/setup.ts` — test setup.
- Create: `frontend/src/components/Dropzone.test.tsx` — dropzone tests.
- Create: `frontend/src/pages/LibraryPage.test.tsx` — library search tests.

---

## Task 1: Backend Project Skeleton

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/screenshots.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_screenshots_api.py`

- [ ] **Step 1: Write failing health/API smoke test**

Create `backend/tests/test_screenshots_api.py`:

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_health_check_returns_ok():
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Add backend project config**

Create `backend/pyproject.toml`:

```toml
[project]
name = "screensort-backend"
version = "0.1.0"
description = "Local ML-powered screenshot organizer backend"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.115.0",
  "uvicorn[standard]>=0.30.0",
  "python-multipart>=0.0.9",
  "pillow>=10.4.0",
  "torch>=2.4.0",
  "transformers>=4.44.0",
]

[project.optional-dependencies]
test = [
  "httpx>=0.27.0",
  "pytest>=8.3.0",
]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

Create empty files:

```python
# backend/app/__init__.py
```

```python
# backend/app/api/__init__.py
```

- [ ] **Step 3: Run test to verify failure**

Run:

```bash
cd backend && python -m pytest tests/test_screenshots_api.py::test_health_check_returns_ok -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.main'`.

- [ ] **Step 4: Implement minimal FastAPI app**

Create `backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.screenshots import router as screenshots_router


def create_app() -> FastAPI:
    app = FastAPI(title="ScreenSort API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(screenshots_router, prefix="/api")
    return app


app = create_app()
```

Create `backend/app/api/screenshots.py`:

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 5: Run test to verify pass**

Run:

```bash
cd backend && python -m pytest tests/test_screenshots_api.py::test_health_check_returns_ok -v
```

Expected: PASS.

---

## Task 2: SQLite Metadata Store

**Files:**
- Create: `backend/app/models.py`
- Create: `backend/app/db.py`
- Modify: `backend/tests/conftest.py`
- Create: `backend/tests/test_db.py`

- [ ] **Step 1: Write failing database tests**

Create `backend/tests/test_db.py`:

```python
import json

from app.db import init_db, insert_screenshot, list_screenshots, get_screenshot


def test_insert_and_get_screenshot(tmp_path):
    db_path = tmp_path / "screenshots.db"
    init_db(db_path)

    created = insert_screenshot(
        db_path,
        original_filename="sample.png",
        stored_filename="abc.png",
        path="data/uploads/abc.png",
        category="code",
        confidence=0.91,
        tags=["terminal", "error"],
    )

    loaded = get_screenshot(db_path, created.id)

    assert loaded is not None
    assert loaded.original_filename == "sample.png"
    assert loaded.category == "code"
    assert loaded.tags == ["terminal", "error"]


def test_list_screenshots_filters_by_query_category_and_tag(tmp_path):
    db_path = tmp_path / "screenshots.db"
    init_db(db_path)
    insert_screenshot(db_path, "work.png", "1.png", "data/uploads/1.png", "work", 0.8, ["meeting"])
    insert_screenshot(db_path, "chat.png", "2.png", "data/uploads/2.png", "social media", 0.7, ["chat"])

    results = list_screenshots(db_path, query="work", category="work", tag="meeting")

    assert len(results) == 1
    assert results[0].original_filename == "work.png"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
cd backend && python -m pytest tests/test_db.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.db'`.

- [ ] **Step 3: Add metadata model**

Create `backend/app/models.py`:

```python
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class ScreenshotRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    stored_filename: str
    path: str
    category: str
    confidence: float
    tags: list[str]
    created_at: datetime


class ClassificationResult(BaseModel):
    category: str
    confidence: float
    tags: list[str]
```

- [ ] **Step 4: Implement SQLite helpers**

Create `backend/app/db.py`:

```python
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from app.models import ScreenshotRecord

SCHEMA = """
CREATE TABLE IF NOT EXISTS screenshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_filename TEXT NOT NULL,
    stored_filename TEXT NOT NULL,
    path TEXT NOT NULL,
    category TEXT NOT NULL,
    confidence REAL NOT NULL,
    tags TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(SCHEMA)


def _row_to_record(row: sqlite3.Row) -> ScreenshotRecord:
    return ScreenshotRecord(
        id=row["id"],
        original_filename=row["original_filename"],
        stored_filename=row["stored_filename"],
        path=row["path"],
        category=row["category"],
        confidence=row["confidence"],
        tags=json.loads(row["tags"]),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def insert_screenshot(
    db_path: Path,
    original_filename: str,
    stored_filename: str,
    path: str,
    category: str,
    confidence: float,
    tags: list[str],
) -> ScreenshotRecord:
    created_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            """
            INSERT INTO screenshots (original_filename, stored_filename, path, category, confidence, tags, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (original_filename, stored_filename, path, category, confidence, json.dumps(tags), created_at),
        )
        row = conn.execute("SELECT * FROM screenshots WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _row_to_record(row)


def get_screenshot(db_path: Path, screenshot_id: int) -> ScreenshotRecord | None:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM screenshots WHERE id = ?", (screenshot_id,)).fetchone()
    return _row_to_record(row) if row else None


def list_screenshots(
    db_path: Path,
    query: str | None = None,
    category: str | None = None,
    tag: str | None = None,
) -> list[ScreenshotRecord]:
    clauses: list[str] = []
    params: list[str] = []
    if query:
        clauses.append("(original_filename LIKE ? OR category LIKE ? OR tags LIKE ?)")
        like = f"%{query}%"
        params.extend([like, like, like])
    if category:
        clauses.append("category = ?")
        params.append(category)
    if tag:
        clauses.append("tags LIKE ?")
        params.append(f"%{tag}%")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"SELECT * FROM screenshots {where} ORDER BY created_at DESC, id DESC"
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, params).fetchall()
    return [_row_to_record(row) for row in rows]
```

- [ ] **Step 5: Run tests to verify pass**

Run:

```bash
cd backend && python -m pytest tests/test_db.py -v
```

Expected: PASS.

---

## Task 3: Local Storage Service

**Files:**
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/services/storage.py`
- Create: `backend/tests/test_storage.py`

- [ ] **Step 1: Write failing storage tests**

Create `backend/tests/test_storage.py`:

```python
import pytest

from app.services.storage import save_upload_bytes, resolve_upload_path


def test_save_upload_bytes_generates_safe_name(tmp_path):
    stored = save_upload_bytes(tmp_path, "../../bad name.png", b"image-bytes")

    assert stored.stored_filename.endswith(".png")
    assert ".." not in stored.stored_filename
    assert (tmp_path / stored.stored_filename).read_bytes() == b"image-bytes"


def test_resolve_upload_path_rejects_path_escape(tmp_path):
    with pytest.raises(ValueError):
        resolve_upload_path(tmp_path, "../secret.png")
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
cd backend && python -m pytest tests/test_storage.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.services'`.

- [ ] **Step 3: Implement storage service**

Create `backend/app/services/__init__.py`:

```python
```

Create `backend/app/services/storage.py`:

```python
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class StoredUpload:
    stored_filename: str
    path: Path


def _safe_suffix(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return suffix if suffix in {".png", ".jpg", ".jpeg", ".webp"} else ".png"


def resolve_upload_path(upload_dir: Path, stored_filename: str) -> Path:
    upload_root = upload_dir.resolve()
    path = (upload_root / stored_filename).resolve()
    if upload_root != path.parent:
        raise ValueError("stored filename escapes upload directory")
    return path


def save_upload_bytes(upload_dir: Path, original_filename: str, content: bytes) -> StoredUpload:
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_filename = f"{uuid4().hex}{_safe_suffix(original_filename)}"
    path = resolve_upload_path(upload_dir, stored_filename)
    path.write_bytes(content)
    return StoredUpload(stored_filename=stored_filename, path=path)
```

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
cd backend && python -m pytest tests/test_storage.py -v
```

Expected: PASS.

---

## Task 4: Classifier Service

**Files:**
- Create: `backend/app/services/classifier.py`
- Create: `backend/tests/test_classifier.py`

- [ ] **Step 1: Write failing classifier tests**

Create `backend/tests/test_classifier.py`:

```python
from app.services.classifier import PromptClassifier, pick_labels


def test_pick_labels_chooses_best_category_and_top_tags():
    result = pick_labels(
        category_scores={"work": 0.2, "code": 0.9, "personal": 0.1},
        tag_scores={"terminal": 0.8, "error": 0.7, "recipe": 0.1},
        tag_threshold=0.5,
    )

    assert result.category == "code"
    assert result.confidence == 0.9
    assert result.tags == ["terminal", "error"]


def test_pick_labels_falls_back_to_top_three_tags():
    result = pick_labels(
        category_scores={"work": 0.6},
        tag_scores={"terminal": 0.3, "error": 0.2, "recipe": 0.1, "chat": 0.05},
        tag_threshold=0.5,
    )

    assert result.tags == ["terminal", "error", "recipe"]
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
cd backend && python -m pytest tests/test_classifier.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.classifier'` or `ImportError`.

- [ ] **Step 3: Implement label selection and CLIP wrapper**

Create `backend/app/services/classifier.py`:

```python
from functools import cached_property
from pathlib import Path

import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

from app.models import ClassificationResult

CATEGORY_PROMPTS: dict[str, str] = {
    "work": "a screenshot related to work",
    "personal": "a personal screenshot",
    "social media": "a social media screenshot",
    "documentation": "a screenshot of documentation",
    "shopping": "a screenshot of shopping",
    "finance": "a screenshot of finance",
    "code": "a screenshot of code",
}

TAG_PROMPTS: dict[str, str] = {
    "meeting": "meeting",
    "important": "important",
    "recipe": "recipe",
    "error": "error message",
    "invoice": "invoice",
    "chat": "chat conversation",
    "article": "article",
    "design": "design mockup",
    "terminal": "terminal",
}


def pick_labels(
    category_scores: dict[str, float],
    tag_scores: dict[str, float],
    tag_threshold: float = 0.25,
) -> ClassificationResult:
    category, confidence = max(category_scores.items(), key=lambda item: item[1])
    selected_tags = [tag for tag, score in sorted(tag_scores.items(), key=lambda item: item[1], reverse=True) if score >= tag_threshold]
    if not selected_tags:
        selected_tags = [tag for tag, _ in sorted(tag_scores.items(), key=lambda item: item[1], reverse=True)[:3]]
    return ClassificationResult(category=category, confidence=confidence, tags=selected_tags[:5])


class PromptClassifier:
    def __init__(self, model_name: str = "openai/clip-vit-base-patch32") -> None:
        self.model_name = model_name

    @cached_property
    def processor(self) -> CLIPProcessor:
        return CLIPProcessor.from_pretrained(self.model_name)

    @cached_property
    def model(self) -> CLIPModel:
        model = CLIPModel.from_pretrained(self.model_name)
        model.eval()
        return model

    def classify(self, image_path: Path) -> ClassificationResult:
        image = Image.open(image_path).convert("RGB")
        category_scores = self._score_prompts(image, CATEGORY_PROMPTS)
        tag_scores = self._score_prompts(image, TAG_PROMPTS)
        return pick_labels(category_scores, tag_scores)

    def _score_prompts(self, image: Image.Image, prompts: dict[str, str]) -> dict[str, float]:
        labels = list(prompts.keys())
        text = [prompts[label] for label in labels]
        inputs = self.processor(text=text, images=image, return_tensors="pt", padding=True)
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = outputs.logits_per_image.softmax(dim=1)[0].tolist()
        return dict(zip(labels, probs, strict=True))
```

- [ ] **Step 4: Run classifier tests to verify pass**

Run:

```bash
cd backend && python -m pytest tests/test_classifier.py -v
```

Expected: PASS without downloading CLIP because tests only call `pick_labels`.

---

## Task 5: Upload/List/Image API

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/api/screenshots.py`
- Modify: `backend/tests/conftest.py`
- Modify: `backend/tests/test_screenshots_api.py`

- [ ] **Step 1: Write API tests with fake classifier**

Replace `backend/tests/conftest.py` with:

```python
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models import ClassificationResult


class FakeClassifier:
    def classify(self, image_path):
        return ClassificationResult(category="code", confidence=0.93, tags=["terminal", "error"])


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    app = create_app(db_path=tmp_path / "screenshots.db", upload_dir=tmp_path / "uploads", classifier=FakeClassifier())
    with TestClient(app) as test_client:
        yield test_client
```

Replace `backend/tests/test_screenshots_api.py` with:

```python
from io import BytesIO

from PIL import Image


def png_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (8, 8), color="black").save(buffer, format="PNG")
    return buffer.getvalue()


def test_health_check_returns_ok(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_upload_screenshot_classifies_and_persists(client):
    response = client.post(
        "/api/screenshots",
        files={"file": ("terminal.png", png_bytes(), "image/png")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["original_filename"] == "terminal.png"
    assert body["category"] == "code"
    assert body["confidence"] == 0.93
    assert body["tags"] == ["terminal", "error"]

    list_response = client.get("/api/screenshots")
    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == body["id"]


def test_upload_rejects_non_image(client):
    response = client.post(
        "/api/screenshots",
        files={"file": ("notes.txt", b"not image", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Upload must be a PNG, JPEG, or WebP image."


def test_list_screenshots_filters(client):
    client.post("/api/screenshots", files={"file": ("terminal.png", png_bytes(), "image/png")})

    response = client.get("/api/screenshots", params={"query": "terminal", "category": "code", "tag": "error"})

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_image_streams_uploaded_file(client):
    upload = client.post("/api/screenshots", files={"file": ("terminal.png", png_bytes(), "image/png")}).json()

    response = client.get(f"/api/screenshots/{upload['id']}/image")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG")
```

- [ ] **Step 2: Run API tests to verify failure**

Run:

```bash
cd backend && python -m pytest tests/test_screenshots_api.py -v
```

Expected: FAIL because `create_app` does not accept injected `db_path`, `upload_dir`, or `classifier`.

- [ ] **Step 3: Wire app state and startup DB init**

Replace `backend/app/main.py` with:

```python
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.screenshots import router as screenshots_router
from app.db import init_db
from app.services.classifier import PromptClassifier


def create_app(
    db_path: Path = Path("data/screenshots.db"),
    upload_dir: Path = Path("data/uploads"),
    classifier: Any | None = None,
) -> FastAPI:
    init_db(db_path)
    app = FastAPI(title="ScreenSort API")
    app.state.db_path = db_path
    app.state.upload_dir = upload_dir
    app.state.classifier = classifier or PromptClassifier()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(screenshots_router, prefix="/api")
    return app


app = create_app()
```

- [ ] **Step 4: Implement screenshots routes**

Replace `backend/app/api/screenshots.py` with:

```python
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError

from app.db import get_screenshot, insert_screenshot, list_screenshots
from app.models import ScreenshotRecord
from app.services.storage import save_upload_bytes

router = APIRouter()
ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp"}


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/screenshots", response_model=ScreenshotRecord)
async def upload_screenshot(request: Request, file: UploadFile = File(...)) -> ScreenshotRecord:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Upload must be a PNG, JPEG, or WebP image.")
    content = await file.read()
    stored = save_upload_bytes(request.app.state.upload_dir, file.filename or "screenshot.png", content)
    try:
        with Image.open(stored.path) as image:
            image.verify()
    except UnidentifiedImageError as exc:
        stored.path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Upload must be a valid image file.") from exc
    result = request.app.state.classifier.classify(stored.path)
    return insert_screenshot(
        request.app.state.db_path,
        original_filename=file.filename or stored.stored_filename,
        stored_filename=stored.stored_filename,
        path=str(stored.path),
        category=result.category,
        confidence=result.confidence,
        tags=result.tags,
    )


@router.get("/screenshots", response_model=list[ScreenshotRecord])
def list_uploaded_screenshots(
    request: Request,
    query: str | None = None,
    category: str | None = None,
    tag: str | None = None,
) -> list[ScreenshotRecord]:
    return list_screenshots(request.app.state.db_path, query=query, category=category, tag=tag)


@router.get("/screenshots/{screenshot_id}", response_model=ScreenshotRecord)
def get_uploaded_screenshot(request: Request, screenshot_id: int) -> ScreenshotRecord:
    record = get_screenshot(request.app.state.db_path, screenshot_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Screenshot not found.")
    return record


@router.get("/screenshots/{screenshot_id}/image")
def get_uploaded_screenshot_image(request: Request, screenshot_id: int) -> FileResponse:
    record = get_screenshot(request.app.state.db_path, screenshot_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Screenshot not found.")
    path = Path(record.path)
    media_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg" if path.suffix.lower() in {".jpg", ".jpeg"} else "image/webp"
    return FileResponse(path, media_type=media_type, filename=record.original_filename)
```

- [ ] **Step 5: Run API tests to verify pass**

Run:

```bash
cd backend && python -m pytest tests/test_screenshots_api.py -v
```

Expected: PASS.

---

## Task 6: Frontend Project Skeleton

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/postcss.config.js`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/index.css`
- Create: `frontend/src/test/setup.ts`

- [ ] **Step 1: Add frontend package config**

Create `frontend/package.json`:

```json
{
  "name": "screensort-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "@vitejs/plugin-react": "latest",
    "vite": "latest",
    "typescript": "latest",
    "react": "latest",
    "react-dom": "latest",
    "react-router-dom": "latest",
    "lucide-react": "latest"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "latest",
    "@testing-library/react": "latest",
    "@testing-library/user-event": "latest",
    "@types/react": "latest",
    "@types/react-dom": "latest",
    "autoprefixer": "latest",
    "jsdom": "latest",
    "postcss": "latest",
    "tailwindcss": "latest",
    "vitest": "latest"
  }
}
```

- [ ] **Step 2: Add Vite/TypeScript/Tailwind config**

Create `frontend/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>ScreenSort</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

Create `frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["DOM", "DOM.Iterable", "ES2020"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"],
  "references": []
}
```

Create `frontend/vite.config.ts`:

```ts
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
  },
});
```

Create `frontend/tailwind.config.js`:

```js
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {},
  },
  plugins: [],
};
```

Create `frontend/postcss.config.js`:

```js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 3: Add React shell**

Create `frontend/src/index.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  margin: 0;
  background: #0f172a;
  color: #e2e8f0;
}
```

Create `frontend/src/main.tsx`:

```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
```

Create `frontend/src/App.tsx`:

```tsx
import { NavLink, Navigate, Route, Routes } from 'react-router-dom';

function Placeholder({ title }: { title: string }) {
  return <h1 className="text-2xl font-semibold">{title}</h1>;
}

export default function App() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `rounded-lg px-4 py-2 text-sm font-medium ${isActive ? 'bg-cyan-400 text-slate-950' : 'text-slate-300 hover:bg-slate-800'}`;

  return (
    <div className="min-h-screen bg-slate-950">
      <header className="border-b border-slate-800 bg-slate-900/80">
        <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <span className="text-xl font-bold text-white">ScreenSort</span>
          <div className="flex gap-2">
            <NavLink to="/upload" className={linkClass}>Upload</NavLink>
            <NavLink to="/library" className={linkClass}>Library</NavLink>
          </div>
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <Routes>
          <Route path="/" element={<Navigate to="/upload" replace />} />
          <Route path="/upload" element={<Placeholder title="Upload" />} />
          <Route path="/library" element={<Placeholder title="Library" />} />
        </Routes>
      </main>
    </div>
  );
}
```

Create `frontend/src/test/setup.ts`:

```ts
import '@testing-library/jest-dom/vitest';
```

- [ ] **Step 4: Install deps and run build**

Run:

```bash
cd frontend && npm install && npm run build
```

Expected: build succeeds.

---

## Task 7: Frontend API Client

**Files:**
- Create: `frontend/src/api/client.ts`

- [ ] **Step 1: Create typed API client**

Create `frontend/src/api/client.ts`:

```ts
export type ScreenshotRecord = {
  id: number;
  original_filename: string;
  stored_filename: string;
  path: string;
  category: string;
  confidence: number;
  tags: string[];
  created_at: string;
};

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api';

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? 'Request failed.');
  }
  return response.json() as Promise<T>;
}

export async function uploadScreenshot(file: File): Promise<ScreenshotRecord> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await fetch(`${API_BASE_URL}/screenshots`, {
    method: 'POST',
    body: formData,
  });
  return parseResponse<ScreenshotRecord>(response);
}

export type ScreenshotFilters = {
  query?: string;
  category?: string;
  tag?: string;
};

export async function listScreenshots(filters: ScreenshotFilters = {}): Promise<ScreenshotRecord[]> {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  const suffix = params.toString() ? `?${params.toString()}` : '';
  const response = await fetch(`${API_BASE_URL}/screenshots${suffix}`);
  return parseResponse<ScreenshotRecord[]>(response);
}

export function imageUrl(id: number): string {
  return `${API_BASE_URL}/screenshots/${id}/image`;
}
```

- [ ] **Step 2: Run type check/build**

Run:

```bash
cd frontend && npm run build
```

Expected: PASS.

---

## Task 8: Dropzone Component

**Files:**
- Create: `frontend/src/components/Dropzone.tsx`
- Create: `frontend/src/components/Dropzone.test.tsx`

- [ ] **Step 1: Write failing dropzone tests**

Create `frontend/src/components/Dropzone.test.tsx`:

```tsx
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import Dropzone from './Dropzone';

describe('Dropzone', () => {
  it('calls onFile when user selects an image', () => {
    const onFile = vi.fn();
    render(<Dropzone onFile={onFile} disabled={false} />);
    const file = new File(['png'], 'shot.png', { type: 'image/png' });

    fireEvent.change(screen.getByLabelText('Choose screenshot'), { target: { files: [file] } });

    expect(onFile).toHaveBeenCalledWith(file);
  });
});
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
cd frontend && npm test -- src/components/Dropzone.test.tsx
```

Expected: FAIL because `Dropzone` does not exist.

- [ ] **Step 3: Implement dropzone**

Create `frontend/src/components/Dropzone.tsx`:

```tsx
import { UploadCloud } from 'lucide-react';
import { DragEvent, useState } from 'react';

type DropzoneProps = {
  onFile: (file: File) => void;
  disabled: boolean;
};

export default function Dropzone({ onFile, disabled }: DropzoneProps) {
  const [dragging, setDragging] = useState(false);

  const pickFile = (files: FileList | null) => {
    const file = files?.[0];
    if (file && file.type.startsWith('image/')) onFile(file);
  };

  const onDrop = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    setDragging(false);
    pickFile(event.dataTransfer.files);
  };

  return (
    <label
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-10 text-center transition ${
        dragging ? 'border-cyan-300 bg-cyan-300/10' : 'border-slate-700 bg-slate-900'
      } ${disabled ? 'cursor-not-allowed opacity-60' : 'hover:border-cyan-400'}`}
    >
      <UploadCloud className="mb-4 h-10 w-10 text-cyan-300" />
      <span className="text-lg font-semibold text-white">Drop screenshot here</span>
      <span className="mt-2 text-sm text-slate-400">PNG, JPG, JPEG, or WebP</span>
      <input
        aria-label="Choose screenshot"
        className="sr-only"
        type="file"
        accept="image/png,image/jpeg,image/webp"
        disabled={disabled}
        onChange={(event) => pickFile(event.target.files)}
      />
    </label>
  );
}
```

- [ ] **Step 4: Run test to verify pass**

Run:

```bash
cd frontend && npm test -- src/components/Dropzone.test.tsx
```

Expected: PASS.

---

## Task 9: Upload Page

**Files:**
- Create: `frontend/src/pages/UploadPage.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Implement upload page**

Create `frontend/src/pages/UploadPage.tsx`:

```tsx
import { useState } from 'react';
import { imageUrl, ScreenshotRecord, uploadScreenshot } from '../api/client';
import Dropzone from '../components/Dropzone';

export default function UploadPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [result, setResult] = useState<ScreenshotRecord | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  const submit = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setError(null);
    try {
      setResult(await uploadScreenshot(selectedFile));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <section className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
      <div>
        <p className="text-sm font-semibold uppercase tracking-wide text-cyan-300">Upload</p>
        <h1 className="mt-2 text-3xl font-bold text-white">Classify a screenshot</h1>
        <p className="mt-3 max-w-2xl text-slate-400">Drop a screenshot and ScreenSort will assign a category plus tags using CLIP zero-shot image matching.</p>
        <div className="mt-8">
          <Dropzone onFile={setSelectedFile} disabled={uploading} />
        </div>
        {selectedFile && <p className="mt-4 text-sm text-slate-300">Selected: {selectedFile.name}</p>}
        {error && <p className="mt-4 rounded-lg bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</p>}
        <button
          className="mt-6 rounded-xl bg-cyan-400 px-5 py-3 font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-50"
          disabled={!selectedFile || uploading}
          onClick={submit}
        >
          {uploading ? 'Classifying…' : 'Upload and classify'}
        </button>
      </div>
      <aside className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <h2 className="text-xl font-semibold text-white">Result</h2>
        {!result && <p className="mt-4 text-slate-400">Upload result appears here.</p>}
        {result && (
          <div className="mt-4 space-y-4">
            <img src={imageUrl(result.id)} alt={result.original_filename} className="max-h-72 w-full rounded-xl object-contain bg-slate-950" />
            <div>
              <p className="text-sm text-slate-400">Category</p>
              <p className="text-2xl font-bold text-cyan-300">{result.category}</p>
              <p className="text-sm text-slate-400">Confidence {(result.confidence * 100).toFixed(1)}%</p>
            </div>
            <div className="flex flex-wrap gap-2">
              {result.tags.map((tag) => <span key={tag} className="rounded-full bg-slate-800 px-3 py-1 text-sm text-slate-200">{tag}</span>)}
            </div>
          </div>
        )}
      </aside>
    </section>
  );
}
```

- [ ] **Step 2: Wire upload route**

Replace `frontend/src/App.tsx` with:

```tsx
import { NavLink, Navigate, Route, Routes } from 'react-router-dom';
import UploadPage from './pages/UploadPage';

function Placeholder({ title }: { title: string }) {
  return <h1 className="text-2xl font-semibold">{title}</h1>;
}

export default function App() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `rounded-lg px-4 py-2 text-sm font-medium ${isActive ? 'bg-cyan-400 text-slate-950' : 'text-slate-300 hover:bg-slate-800'}`;

  return (
    <div className="min-h-screen bg-slate-950">
      <header className="border-b border-slate-800 bg-slate-900/80">
        <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <span className="text-xl font-bold text-white">ScreenSort</span>
          <div className="flex gap-2">
            <NavLink to="/upload" className={linkClass}>Upload</NavLink>
            <NavLink to="/library" className={linkClass}>Library</NavLink>
          </div>
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <Routes>
          <Route path="/" element={<Navigate to="/upload" replace />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/library" element={<Placeholder title="Library" />} />
        </Routes>
      </main>
    </div>
  );
}
```

- [ ] **Step 3: Run build**

Run:

```bash
cd frontend && npm run build
```

Expected: PASS.

---

## Task 10: Library Page

**Files:**
- Create: `frontend/src/components/ScreenshotCard.tsx`
- Create: `frontend/src/pages/LibraryPage.tsx`
- Create: `frontend/src/pages/LibraryPage.test.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Write failing library test**

Create `frontend/src/pages/LibraryPage.test.tsx`:

```tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import LibraryPage from './LibraryPage';

const records = [
  {
    id: 1,
    original_filename: 'terminal.png',
    stored_filename: '1.png',
    path: 'data/uploads/1.png',
    category: 'code',
    confidence: 0.93,
    tags: ['terminal', 'error'],
    created_at: '2026-04-27T00:00:00Z',
  },
];

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(records), { status: 200 })));
});

describe('LibraryPage', () => {
  it('loads screenshots and refetches when search changes', async () => {
    const user = userEvent.setup();
    render(<LibraryPage />);

    expect(await screen.findByText('terminal.png')).toBeInTheDocument();
    await user.type(screen.getByLabelText('Search screenshots'), 'term');

    await waitFor(() => expect(fetch).toHaveBeenCalledWith(expect.stringContaining('query=term')));
  });
});
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
cd frontend && npm test -- src/pages/LibraryPage.test.tsx
```

Expected: FAIL because `LibraryPage` does not exist.

- [ ] **Step 3: Implement screenshot card**

Create `frontend/src/components/ScreenshotCard.tsx`:

```tsx
import { imageUrl, ScreenshotRecord } from '../api/client';

type ScreenshotCardProps = {
  screenshot: ScreenshotRecord;
};

export default function ScreenshotCard({ screenshot }: ScreenshotCardProps) {
  return (
    <article className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900">
      <img src={imageUrl(screenshot.id)} alt={screenshot.original_filename} className="h-48 w-full object-cover bg-slate-950" />
      <div className="space-y-3 p-4">
        <div>
          <h2 className="truncate font-semibold text-white">{screenshot.original_filename}</h2>
          <p className="text-sm text-slate-400">{new Date(screenshot.created_at).toLocaleString()}</p>
        </div>
        <div>
          <span className="rounded-full bg-cyan-400/10 px-3 py-1 text-sm font-medium text-cyan-300">{screenshot.category}</span>
          <span className="ml-2 text-sm text-slate-400">{(screenshot.confidence * 100).toFixed(1)}%</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {screenshot.tags.map((tag) => <span key={tag} className="rounded-full bg-slate-800 px-2.5 py-1 text-xs text-slate-300">{tag}</span>)}
        </div>
      </div>
    </article>
  );
}
```

- [ ] **Step 4: Implement library page**

Create `frontend/src/pages/LibraryPage.tsx`:

```tsx
import { useEffect, useState } from 'react';
import { listScreenshots, ScreenshotRecord } from '../api/client';
import ScreenshotCard from '../components/ScreenshotCard';

export default function LibraryPage() {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('');
  const [tag, setTag] = useState('');
  const [screenshots, setScreenshots] = useState<ScreenshotRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    listScreenshots({ query, category, tag })
      .then((records) => {
        if (!cancelled) {
          setScreenshots(records);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to load screenshots.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [query, category, tag]);

  return (
    <section>
      <p className="text-sm font-semibold uppercase tracking-wide text-cyan-300">Library</p>
      <h1 className="mt-2 text-3xl font-bold text-white">Browse screenshots</h1>
      <div className="mt-6 grid gap-4 md:grid-cols-3">
        <label className="text-sm text-slate-300">
          Search screenshots
          <input
            aria-label="Search screenshots"
            className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-white outline-none focus:border-cyan-400"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="filename, category, tag"
          />
        </label>
        <label className="text-sm text-slate-300">
          Category
          <input
            className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-white outline-none focus:border-cyan-400"
            value={category}
            onChange={(event) => setCategory(event.target.value)}
            placeholder="code"
          />
        </label>
        <label className="text-sm text-slate-300">
          Tag
          <input
            className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-white outline-none focus:border-cyan-400"
            value={tag}
            onChange={(event) => setTag(event.target.value)}
            placeholder="terminal"
          />
        </label>
      </div>
      {loading && <p className="mt-8 text-slate-400">Loading screenshots…</p>}
      {error && <p className="mt-8 rounded-lg bg-red-500/10 px-4 py-3 text-sm text-red-300">{error}</p>}
      {!loading && !error && screenshots.length === 0 && <p className="mt-8 text-slate-400">No screenshots found.</p>}
      <div className="mt-8 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {screenshots.map((screenshot) => <ScreenshotCard key={screenshot.id} screenshot={screenshot} />)}
      </div>
    </section>
  );
}
```

- [ ] **Step 5: Wire library route**

Replace `frontend/src/App.tsx` with:

```tsx
import { NavLink, Navigate, Route, Routes } from 'react-router-dom';
import LibraryPage from './pages/LibraryPage';
import UploadPage from './pages/UploadPage';

export default function App() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `rounded-lg px-4 py-2 text-sm font-medium ${isActive ? 'bg-cyan-400 text-slate-950' : 'text-slate-300 hover:bg-slate-800'}`;

  return (
    <div className="min-h-screen bg-slate-950">
      <header className="border-b border-slate-800 bg-slate-900/80">
        <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <span className="text-xl font-bold text-white">ScreenSort</span>
          <div className="flex gap-2">
            <NavLink to="/upload" className={linkClass}>Upload</NavLink>
            <NavLink to="/library" className={linkClass}>Library</NavLink>
          </div>
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <Routes>
          <Route path="/" element={<Navigate to="/upload" replace />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/library" element={<LibraryPage />} />
        </Routes>
      </main>
    </div>
  );
}
```

- [ ] **Step 6: Run test and build**

Run:

```bash
cd frontend && npm test -- src/pages/LibraryPage.test.tsx && npm run build
```

Expected: PASS.

---

## Task 11: Final Verification

**Files:**
- Modify as needed only if verification fails.

- [ ] **Step 1: Run backend tests**

Run:

```bash
cd backend && python -m pytest -v
```

Expected: all backend tests PASS.

- [ ] **Step 2: Run frontend tests and build**

Run:

```bash
cd frontend && npm test && npm run build
```

Expected: all frontend tests PASS and build succeeds.

- [ ] **Step 3: Start backend**

Run:

```bash
cd backend && uvicorn app.main:app --reload
```

Expected: server listens on `http://127.0.0.1:8000`.

- [ ] **Step 4: Start frontend**

Run in another terminal:

```bash
cd frontend && npm run dev
```

Expected: Vite prints local URL, usually `http://localhost:5173/`.

- [ ] **Step 5: Manual UI verification**

Open frontend URL. Verify:
- `/upload` renders dropzone.
- PNG/JPG upload returns category, confidence, and tags.
- result card shows image preview.
- `/library` shows uploaded screenshot.
- search box filters by filename/tag/category.
- category and tag filters call backend and update results.

---

## Self-Review

Spec coverage:
- FastAPI backend: Tasks 1, 5.
- PyTorch CLIP zero-shot classifier: Task 4.
- SQLite metadata store: Task 2.
- Local image storage: Task 3.
- Upload/list/detail/image endpoints: Task 5.
- React + TypeScript + Tailwind frontend: Tasks 6-10.
- Upload page: Tasks 8-9.
- Library/search page: Task 10.
- Backend/frontend tests: Tasks 1-5, 8, 10, 11.
- Manual verification: Task 11.

Placeholder scan: no TBD/TODO/fill-later language.

Type consistency: `ScreenshotRecord`, `ClassificationResult`, API paths, and route names match across backend/frontend tasks.
