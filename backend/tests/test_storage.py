"""Purpose: upload storage service tests. Callers: pytest. Deps: pathlib tmp_path, app.services.storage. API: test functions. Side effects: writes temporary upload files."""

import pytest

from app.services.storage import resolve_upload_path, save_upload_bytes


def test_save_upload_bytes_sanitizes_name_and_writes_bytes(tmp_path):
    content = b"image-bytes"

    stored = save_upload_bytes(tmp_path, "../../bad name.png", content)

    assert ".." not in stored.stored_filename
    assert stored.stored_filename.endswith(".png")
    assert stored.path == tmp_path / stored.stored_filename
    assert stored.path.read_bytes() == content


def test_resolve_upload_path_rejects_path_escape(tmp_path):
    with pytest.raises(ValueError):
        resolve_upload_path(tmp_path, "../secret.png")


def test_resolve_upload_path_rejects_absolute_path(tmp_path):
    with pytest.raises(ValueError):
        resolve_upload_path(tmp_path, str(tmp_path / "secret.png"))


def test_resolve_upload_path_rejects_nested_path(tmp_path):
    with pytest.raises(ValueError):
        resolve_upload_path(tmp_path, "nested/file.png")
