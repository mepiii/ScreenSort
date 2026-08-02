"""Purpose: local upload file storage. Callers: API routes and tests. Deps: pathlib, uuid, dataclasses. API: StoredUpload, save_upload_bytes, resolve_upload_path. Side effects: creates directories and writes upload files."""
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

SAFE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
DEFAULT_SUFFIX = ".png"


@dataclass(frozen=True)
class StoredUpload:
    stored_filename: str
    path: Path


def _safe_suffix(original_filename: str) -> str:
    suffix = Path(original_filename).suffix.lower()
    return suffix if suffix in SAFE_SUFFIXES else DEFAULT_SUFFIX


def resolve_upload_path(upload_dir: Path, stored_filename: str) -> Path:
    if Path(stored_filename).is_absolute():
        raise ValueError("stored filename must be relative")
    root = upload_dir.resolve()
    target = (root / stored_filename).resolve()
    if target.parent != root:
        raise ValueError("stored filename escapes upload directory")
    return target


def save_upload_bytes(upload_dir: Path, original_filename: str, content: bytes) -> StoredUpload:
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_filename = f"{uuid4().hex}{_safe_suffix(original_filename)}"
    path = resolve_upload_path(upload_dir, stored_filename)
    path.write_bytes(content)
    return StoredUpload(stored_filename=stored_filename, path=path)
