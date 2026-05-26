from typing import Literal

from pydantic import BaseModel

Status = Literal["pending", "processing", "processed", "skipped", "duplicate", "split", "error"]
LogStatus = Literal["success", "failure", "skipped"]
VocabStatus = Literal["normalized", "dict_looked_up", "enriched", "done"]


class VocabEntry(BaseModel):
    id: int | None = None
    canonical_form: str
    target_language: str
    source_language: str
    status: VocabStatus = "normalized"
    is_phrase: bool = False
    part_of_speech: str | None = None
    gender: str | None = None
    irregular: bool = False
    translations: list[str]
    example_sentence: str | None = None
    disambiguation_note: str | None = None
    needs_review: bool = False
    dict_source: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class RawEntry(BaseModel):
    id: int | None = None
    surface_form: str
    target_language: str
    source_language: str
    raw_translations: list[str]
    is_phrase: bool = False
    canonical_form: str | None = None
    vocab_entry_id: int | None = None
    status: Status = "pending"
    split_from_id: int | None = None
    pos_hint: str | None = None
    skip_reason: str | None = None
    error_message: str | None = None
    scraped_at: str | None = None
    processed_at: str | None = None
