import sqlite3
from pathlib import Path

CREATE_VOCAB_ENTRIES = """
CREATE TABLE IF NOT EXISTS vocab_entries (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_form      TEXT NOT NULL,
    target_language     TEXT NOT NULL,
    source_language     TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'normalized',  -- see VocabStatus in models.py
    is_phrase           INTEGER NOT NULL DEFAULT 0,
    part_of_speech      TEXT,
    gender              TEXT,
    irregular           INTEGER NOT NULL DEFAULT 0,
    translations        TEXT NOT NULL,          -- JSON array
    definitions         TEXT,                          -- JSON array, from dict lookup
    example_sentence    TEXT,
    example_translation TEXT,
    disambiguation_note TEXT,
    needs_review        INTEGER NOT NULL DEFAULT 0,
    dict_source         TEXT,
    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT DEFAULT (datetime('now')),
    UNIQUE(canonical_form, target_language)
);
"""

CREATE_RAW_ENTRIES = """
CREATE TABLE IF NOT EXISTS raw_entries (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    surface_form        TEXT NOT NULL,
    target_language     TEXT NOT NULL,
    source_language     TEXT NOT NULL,
    raw_translations    TEXT NOT NULL,          -- JSON array
    is_phrase           INTEGER NOT NULL DEFAULT 0,
    canonical_form      TEXT,
    vocab_entry_id      INTEGER,
    status              TEXT NOT NULL DEFAULT 'pending',  -- see Status in models.py
    split_from_id       INTEGER,
    pos_hint            TEXT,
    skip_reason         TEXT,
    error_message       TEXT,
    scraped_at          TEXT DEFAULT (datetime('now')),
    processed_at        TEXT,
    FOREIGN KEY(vocab_entry_id) REFERENCES vocab_entries(id),
    FOREIGN KEY(split_from_id)  REFERENCES raw_entries(id)
);
"""

CREATE_PROCESSING_LOG = """
CREATE TABLE IF NOT EXISTS processing_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_entry_id    INTEGER NOT NULL,
    step            TEXT NOT NULL,      -- normalize | dict_lookup | enrich | db_write
    status          TEXT NOT NULL,      -- success | failure | skipped
    detail          TEXT,
    timestamp       TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(raw_entry_id) REFERENCES raw_entries(id)
);
"""


def init_db(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute(CREATE_VOCAB_ENTRIES)
    conn.execute(CREATE_RAW_ENTRIES)
    conn.execute(CREATE_PROCESSING_LOG)
    conn.commit()

    conn.row_factory = sqlite3.Row

    return conn
