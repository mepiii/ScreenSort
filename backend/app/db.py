"""Purpose: SQLite metadata persistence. Callers: API routes and tests. Deps: sqlite3, json, pathlib, app.models. API: init_db, insert_screenshot, delete_screenshot, get_screenshot, get_screenshot_by_source_path, list_screenshots. Side effects: creates directories, migrates schema, creates/reads/writes SQLite database files."""
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.models import ScreenshotRecord

SCHEMA = """
CREATE TABLE IF NOT EXISTS screenshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_filename TEXT NOT NULL,
    stored_filename TEXT NOT NULL,
    path TEXT NOT NULL,
    source_path TEXT,
    ingest_method TEXT NOT NULL DEFAULT 'upload',
    category TEXT NOT NULL,
    confidence REAL NOT NULL,
    tags TEXT NOT NULL,
    created_at TEXT NOT NULL,
    ocr_text TEXT
);
"""


def _quote_fts_term(term: str) -> str:
    escaped = term.replace('"', '""')
    return f'"{escaped}"'


def _build_fts_query(query: str) -> str:
    terms = [_quote_fts_term(term) for term in re.findall(r"\w+", query)]
    return " AND ".join(terms)


def _ensure_fts(conn: sqlite3.Connection) -> None:
    try:
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS screenshots_fts USING fts5(
                screenshot_id UNINDEXED,
                original_filename,
                category,
                tags_text,
                ocr_text
            )
            """
        )
    except sqlite3.OperationalError as exc:
        if "fts5" in str(exc).lower():
            raise RuntimeError("SQLite FTS5 support is required.") from exc
        raise


def _rebuild_stale_fts(conn: sqlite3.Connection) -> None:
    columns = {row[1] for row in conn.execute("PRAGMA table_info(screenshots_fts)")}
    if "ocr_text" not in columns:
        conn.execute("DROP TABLE screenshots_fts")
        _ensure_fts(conn)


def _backfill_fts(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        INSERT INTO screenshots_fts (screenshot_id, original_filename, category, tags_text, ocr_text)
        SELECT screenshots.id, screenshots.original_filename, screenshots.category, screenshots.tags, COALESCE(screenshots.ocr_text, '')
        FROM screenshots
        WHERE NOT EXISTS (
            SELECT 1 FROM screenshots_fts WHERE screenshots_fts.screenshot_id = screenshots.id
        )
        """
    )


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(SCHEMA)
        columns = {row[1] for row in conn.execute("PRAGMA table_info(screenshots)")}
        if "source_path" not in columns:
            conn.execute("ALTER TABLE screenshots ADD COLUMN source_path TEXT")
        if "ingest_method" not in columns:
            conn.execute("ALTER TABLE screenshots ADD COLUMN ingest_method TEXT NOT NULL DEFAULT 'upload'")
        if "ocr_text" not in columns:
            conn.execute("ALTER TABLE screenshots ADD COLUMN ocr_text TEXT")
        _ensure_fts(conn)
        _rebuild_stale_fts(conn)
        _backfill_fts(conn)
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_screenshots_source_path ON screenshots(source_path) WHERE source_path IS NOT NULL"
        )


def _deserialize_tags(raw_tags: str) -> list[str]:
    try:
        tags = json.loads(raw_tags)
    except (TypeError, json.JSONDecodeError):
        return []
    return tags if isinstance(tags, list) and all(isinstance(tag, str) for tag in tags) else []


def _row_to_record(row: sqlite3.Row) -> ScreenshotRecord:
    return ScreenshotRecord(
        id=row["id"],
        original_filename=row["original_filename"],
        stored_filename=row["stored_filename"],
        path=row["path"],
        source_path=row["source_path"],
        ingest_method=row["ingest_method"],
        category=row["category"],
        confidence=row["confidence"],
        tags=_deserialize_tags(row["tags"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        ocr_text=row["ocr_text"],
    )


def insert_screenshot(
    db_path: Path,
    original_filename: str,
    stored_filename: str,
    path: str,
    category: str,
    confidence: float,
    tags: list[str],
    source_path: str | None = None,
    ingest_method: str = "upload",
    ocr_text: str | None = None,
) -> ScreenshotRecord:
    created_at = datetime.now(timezone.utc).isoformat()
    tags_json = json.dumps(tags)
    tags_text = " ".join(tags)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_fts(conn)
        cursor = conn.execute(
            """
            INSERT INTO screenshots (original_filename, stored_filename, path, source_path, ingest_method, category, confidence, tags, created_at, ocr_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (original_filename, stored_filename, path, source_path, ingest_method, category, confidence, tags_json, created_at, ocr_text),
        )
        screenshot_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO screenshots_fts (screenshot_id, original_filename, category, tags_text, ocr_text)
            VALUES (?, ?, ?, ?, ?)
            """,
            (screenshot_id, original_filename, category, tags_text, ocr_text or ""),
        )
        row = conn.execute("SELECT * FROM screenshots WHERE id = ?", (screenshot_id,)).fetchone()
    return _row_to_record(row)


def delete_screenshot(db_path: Path, screenshot_id: int) -> None:
    with sqlite3.connect(db_path) as conn:
        _ensure_fts(conn)
        conn.execute("DELETE FROM screenshots_fts WHERE screenshot_id = ?", (screenshot_id,))
        conn.execute("DELETE FROM screenshots WHERE id = ?", (screenshot_id,))


def get_screenshot(db_path: Path, screenshot_id: int) -> ScreenshotRecord | None:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM screenshots WHERE id = ?", (screenshot_id,)).fetchone()
    return _row_to_record(row) if row else None


def get_screenshot_by_source_path(db_path: Path, source_path: str) -> ScreenshotRecord | None:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM screenshots WHERE source_path = ?", (source_path,)).fetchone()
    return _row_to_record(row) if row else None


def list_screenshots(
    db_path: Path,
    query: str | None = None,
    category: str | None = None,
    tag: str | None = None,
) -> list[ScreenshotRecord]:
    clauses: list[str] = []
    params: list[str] = []
    normalized_query = query.strip() if query else None
    if normalized_query:
        fts_query = _build_fts_query(normalized_query)
        if fts_query:
            clauses.append("id IN (SELECT screenshot_id FROM screenshots_fts WHERE screenshots_fts MATCH ?)")
            params.append(fts_query)
    if category:
        clauses.append("category = ?")
        params.append(category)
    used_json_filter = bool(tag)
    if tag:
        clauses.append("EXISTS (SELECT 1 FROM json_each(screenshots.tags) WHERE value = ?)")
        params.append(tag)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"SELECT * FROM screenshots {where} ORDER BY created_at DESC, id DESC"
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError as exc:
            if not used_json_filter or "json_each" not in str(exc):
                raise
            used_json_filter = False
            clauses.pop()
            where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            rows = conn.execute(f"SELECT * FROM screenshots {where} ORDER BY created_at DESC, id DESC", params[:-1]).fetchall()
    records = [_row_to_record(row) for row in rows]
    return [record for record in records if tag in record.tags] if tag and not used_json_filter else records
