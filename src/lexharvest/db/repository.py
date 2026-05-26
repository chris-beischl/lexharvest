import json
from sqlite3 import Connection
from typing import Any

from .models import LogStatus, RawEntry, Status, VocabEntry, VocabStatus


class LexRepository:
    def __init__(self, conn: Connection):
        self.conn = conn

    def get_raw_entry(self, surface_form: str, language: str) -> RawEntry | None:
        cursor = self.conn.execute(
            "SELECT * FROM raw_entries WHERE surface_form = ? AND target_language = ?",
            (surface_form, language),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        row_dict = dict(row)
        row_dict["raw_translations"] = json.loads(row_dict["raw_translations"])
        return RawEntry(**row_dict)

    def insert_raw_entry(self, entry: RawEntry) -> int:
        data = entry.model_dump(exclude={"id", "scraped_at", "processed_at"})
        data["raw_translations"] = json.dumps(data["raw_translations"])

        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))

        cursor = self.conn.execute(
            f"INSERT INTO raw_entries ({columns}) VALUES ({placeholders})",
            list(data.values()),
        )
        self.conn.commit()
        assert cursor.lastrowid is not None
        return cursor.lastrowid

    def get_vocab_entry(self, canonical_form: str, language: str) -> VocabEntry | None:
        cursor = self.conn.execute(
            "SELECT * FROM vocab_entries WHERE canonical_form = ? AND target_language = ?",
            (canonical_form, language),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        row_dict = dict(row)
        row_dict["translations"] = json.loads(row_dict["translations"])
        row_dict["definitions"] = (
            json.loads(row_dict["definitions"]) if row_dict["definitions"] else []
        )
        return VocabEntry(**row_dict)

    def insert_vocab_entry(self, entry: VocabEntry) -> int:
        if self.get_vocab_entry(entry.canonical_form, entry.target_language) is not None:
            raise ValueError(
                f"VocabEntry for '{entry.canonical_form}' ({entry.target_language}) already exists"
            )

        data = entry.model_dump(exclude={"id", "created_at", "updated_at"})
        data["translations"] = json.dumps(data["translations"])
        data["definitions"] = json.dumps(data["definitions"])

        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))

        cursor = self.conn.execute(
            f"INSERT INTO vocab_entries ({columns}) VALUES ({placeholders})",
            list(data.values()),
        )
        self.conn.commit()
        assert cursor.lastrowid is not None
        return cursor.lastrowid

    def get_raw_entries_by_status(self, status: Status) -> list[RawEntry]:
        cursor = self.conn.execute("SELECT * FROM raw_entries WHERE status = ?", (status,))
        rows = cursor.fetchall()
        result = []
        for row in rows:
            row_dict = dict(row)
            row_dict["raw_translations"] = json.loads(row_dict["raw_translations"])
            result.append(RawEntry(**row_dict))
        return result

    def get_vocab_entries_by_status(self, status: VocabStatus) -> list[VocabEntry]:
        cursor = self.conn.execute("SELECT * FROM vocab_entries WHERE status = ?", (status,))
        rows = cursor.fetchall()
        result = []
        for row in rows:
            row_dict = dict(row)
            row_dict["translations"] = json.loads(row_dict["translations"])
            row_dict["definitions"] = (
                json.loads(row_dict["definitions"]) if row_dict["definitions"] else []
            )
            result.append(VocabEntry(**row_dict))
        return result

    def update_raw_entry(self, id: int, **kwargs: Any) -> None:
        fields = ", ".join([f"{key} = ?" for key in kwargs])
        self.conn.execute(
            f"UPDATE raw_entries SET {fields} WHERE id = ?",
            list(kwargs.values()) + [id],
        )
        self.conn.commit()

    def update_vocab_entry(self, id: int, **kwargs: Any) -> None:
        fields = ", ".join([f"{key} = ?" for key in kwargs])
        self.conn.execute(
            f"UPDATE vocab_entries SET {fields} WHERE id = ?",
            list(kwargs.values()) + [id],
        )
        self.conn.commit()

    def log(self, raw_entry_id: int, step: str, status: LogStatus, detail: str | None) -> None:
        self.conn.execute(
            "INSERT INTO processing_log (raw_entry_id, step, status, detail) VALUES (?, ?, ?, ?)",
            (raw_entry_id, step, status, detail),
        )
        self.conn.commit()
