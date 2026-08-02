"""Purpose: database helper tests. Callers: pytest. Deps: app.db, sqlite3, pathlib tmp_path. API: test functions. Side effects: creates temporary SQLite databases."""

import sqlite3

from app.db import delete_screenshot, get_screenshot, get_screenshot_by_source_path, init_db, insert_screenshot, list_screenshots


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
    assert loaded.stored_filename == "abc.png"
    assert loaded.path == "data/uploads/abc.png"
    assert loaded.category == "code"
    assert loaded.confidence == 0.91
    assert loaded.tags == ["terminal", "error"]
    assert loaded.source_path is None
    assert loaded.ingest_method == "upload"
    assert loaded.created_at == created.created_at


def test_insert_and_get_screenshot_by_source_path(tmp_path):
    db_path = tmp_path / "screenshots.db"
    init_db(db_path)

    created = insert_screenshot(
        db_path,
        original_filename="source.png",
        stored_filename="stored.png",
        path="data/uploads/stored.png",
        category="code",
        confidence=0.83,
        tags=["terminal"],
        source_path="/watched/source.png",
        ingest_method="watcher",
    )

    loaded = get_screenshot_by_source_path(db_path, "/watched/source.png")

    assert loaded == created
    assert get_screenshot_by_source_path(db_path, "/missing.png") is None


def test_delete_screenshot_removes_record(tmp_path):
    db_path = tmp_path / "screenshots.db"
    init_db(db_path)
    created = insert_screenshot(db_path, "source.png", "stored.png", "data/uploads/stored.png", "code", 0.83, [])

    delete_screenshot(db_path, created.id)

    assert get_screenshot(db_path, created.id) is None


def test_source_path_unique_partial_index(tmp_path):
    db_path = tmp_path / "screenshots.db"
    init_db(db_path)
    insert_screenshot(db_path, "one.png", "one.png", "data/uploads/one.png", "code", 0.83, [], source_path="/watched/source.png")

    try:
        insert_screenshot(db_path, "two.png", "two.png", "data/uploads/two.png", "code", 0.83, [], source_path="/watched/source.png")
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("duplicate source_path insert should fail")

    insert_screenshot(db_path, "upload.png", "upload.png", "data/uploads/upload.png", "code", 0.83, [])
    insert_screenshot(db_path, "upload2.png", "upload2.png", "data/uploads/upload2.png", "code", 0.83, [])
    assert len(list_screenshots(db_path)) == 3


def test_list_screenshots_filters_by_query_category_and_tag(tmp_path):
    db_path = tmp_path / "screenshots.db"
    init_db(db_path)
    insert_screenshot(db_path, "work.png", "1.png", "data/uploads/1.png", "work", 0.8, ["meeting"])
    insert_screenshot(db_path, "chat.png", "2.png", "data/uploads/2.png", "social media", 0.7, ["chat"])
    insert_screenshot(db_path, "work-chat.png", "3.png", "data/uploads/3.png", "work", 0.6, ["chat"])
    insert_screenshot(db_path, "chatter.png", "4.png", "data/uploads/4.png", "work", 0.5, ["chatter"])

    results = list_screenshots(db_path, query="work", category="work", tag="meeting")
    chat_results = list_screenshots(db_path, tag="chat")

    assert len(results) == 1
    assert results[0].original_filename == "work.png"
    assert {record.original_filename for record in chat_results} == {"chat.png", "work-chat.png"}


def test_ocr_text_persisted(tmp_path):
    db_path = tmp_path / "screenshots.db"
    init_db(db_path)

    created = insert_screenshot(db_path, "ocr.png", "ocr.png", "data/uploads/ocr.png", "code", 0.9, [], ocr_text="Traceback fatal error")
    loaded = get_screenshot(db_path, created.id)

    assert loaded is not None
    assert loaded.ocr_text == "Traceback fatal error"
    assert list_screenshots(db_path)[0].ocr_text == "Traceback fatal error"


def test_list_screenshots_query_matches_ocr_text(tmp_path):
    db_path = tmp_path / "screenshots.db"
    init_db(db_path)
    insert_screenshot(db_path, "plain.png", "plain.png", "data/uploads/plain.png", "work", 0.8, ["meeting"], ocr_text="quarterly roadmap")
    insert_screenshot(db_path, "code.png", "code.png", "data/uploads/code.png", "code", 0.8, ["error"], ocr_text="sqlite fts search failure")

    results = list_screenshots(db_path, query="fts")

    assert [record.original_filename for record in results] == ["code.png"]


def test_list_screenshots_query_preserves_category_filter(tmp_path):
    db_path = tmp_path / "screenshots.db"
    init_db(db_path)
    insert_screenshot(db_path, "work.png", "work.png", "data/uploads/work.png", "work", 0.8, [], ocr_text="shared needle")
    insert_screenshot(db_path, "code.png", "code.png", "data/uploads/code.png", "code", 0.8, [], ocr_text="shared needle")

    results = list_screenshots(db_path, query="needle", category="code")

    assert [record.original_filename for record in results] == ["code.png"]


def test_list_screenshots_query_preserves_exact_tag_filter(tmp_path):
    db_path = tmp_path / "screenshots.db"
    init_db(db_path)
    insert_screenshot(db_path, "exact.png", "exact.png", "data/uploads/exact.png", "work", 0.8, ["chat"], ocr_text="unique needle")
    insert_screenshot(db_path, "prefix.png", "prefix.png", "data/uploads/prefix.png", "work", 0.8, ["chatter"], ocr_text="unique needle")

    results = list_screenshots(db_path, query="needle", tag="chat")

    assert [record.original_filename for record in results] == ["exact.png"]


def test_delete_screenshot_removes_from_search(tmp_path):
    db_path = tmp_path / "screenshots.db"
    init_db(db_path)
    created = insert_screenshot(db_path, "delete.png", "delete.png", "data/uploads/delete.png", "work", 0.8, [], ocr_text="vanishing needle")

    delete_screenshot(db_path, created.id)

    assert list_screenshots(db_path, query="vanishing") == []


def test_blank_query_returns_unfiltered_records(tmp_path):
    db_path = tmp_path / "screenshots.db"
    init_db(db_path)
    insert_screenshot(db_path, "blank.png", "blank.png", "data/uploads/blank.png", "work", 0.8, [], ocr_text="needle")

    assert [record.original_filename for record in list_screenshots(db_path, query="   ")] == ["blank.png"]


def test_fts_query_quotes_operators(tmp_path):
    db_path = tmp_path / "screenshots.db"
    init_db(db_path)
    insert_screenshot(db_path, "literal.png", "literal.png", "data/uploads/literal.png", "work", 0.8, [], ocr_text='OR NEAR "quoted" * -')

    assert [record.original_filename for record in list_screenshots(db_path, query='OR NEAR "quoted" * -')] == ["literal.png"]


def test_legacy_schema_migration_is_idempotent_and_defaults_work(tmp_path):
    db_path = tmp_path / "screenshots.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE screenshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL,
                path TEXT NOT NULL,
                category TEXT NOT NULL,
                confidence REAL NOT NULL,
                tags TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            INSERT INTO screenshots (original_filename, stored_filename, path, category, confidence, tags, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("legacy.png", "1.png", "data/uploads/1.png", "work", 0.8, '["chat"]', "2026-01-01T00:00:00+00:00"),
        )

    init_db(db_path)
    init_db(db_path)
    loaded = list_screenshots(db_path, query="legacy")

    assert len(loaded) == 1
    assert loaded[0].source_path is None
    assert loaded[0].ingest_method == "upload"
    assert loaded[0].ocr_text is None
    assert loaded[0].tags == ["chat"]


def test_legacy_fts_schema_rebuilds_and_backfills_ocr_text(tmp_path):
    db_path = tmp_path / "screenshots.db"
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("DROP TABLE screenshots_fts")
        conn.execute(
            """
            CREATE VIRTUAL TABLE screenshots_fts USING fts5(
                screenshot_id UNINDEXED,
                original_filename,
                category,
                tags_text
            )
            """
        )
        conn.execute(
            """
            INSERT INTO screenshots (original_filename, stored_filename, path, category, confidence, tags, created_at, ocr_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("old-fts.png", "old-fts.png", "data/uploads/old-fts.png", "work", 0.8, "[]", "2026-01-01T00:00:00+00:00", "rebuilt needle"),
        )

    init_db(db_path)
    init_db(db_path)

    assert [record.original_filename for record in list_screenshots(db_path, query="rebuilt")] == ["old-fts.png"]


def test_invalid_tags_deserialize_to_empty_list(tmp_path):
    db_path = tmp_path / "screenshots.db"
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO screenshots (original_filename, stored_filename, path, category, confidence, tags, created_at)
            VALUES ('bad.png', 'bad.png', 'data/uploads/bad.png', 'work', 0.1, '{"bad": true}', '2026-01-01T00:00:00+00:00')
            """
        )

    assert list_screenshots(db_path)[0].tags == []
