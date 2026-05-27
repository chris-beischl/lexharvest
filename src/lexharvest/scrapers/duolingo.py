import json
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field


class DuolingoLexeme(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)  # don't fail on unknown fields
    text: str
    translations: list[str]
    audio_url: str | None = Field(default=None, alias="audioURL")
    is_new: bool = Field(alias="isNew")


@dataclass
class DuolingoConfig:
    user_id: str
    target_language: str
    source_language: str
    auth_token: str  # full value from DevTools: "Bearer eyJhbGci..."
    accept_language: str  # load from config.toml
    payload_file: str  # path to duolingo_payload.json
    page_size: int = 50
    base_url: str = "https://www.duolingo.com/2017-06-30"


class DuolingoExtractor:
    _STATIC_HEADERS = {
        "Content-Type": "application/json; charset=UTF-8",
        "Accept": "application/json; charset=UTF-8",
        "Origin": "https://www.duolingo.com",
        "Referer": "https://www.duolingo.com/practice-hub/words",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0",
    }

    def __init__(self, config: DuolingoConfig):
        self.config = config

    def extract(self) -> list[DuolingoLexeme]:
        all_lexemes: list[DuolingoLexeme] = []
        start = 0

        payload = self._load_payload()

        while True:
            batch = self._fetch_batch(payload, start)
            all_lexemes.extend(batch)

            if len(batch) < self.config.page_size:
                break
            start += self.config.page_size

        return all_lexemes

    def _fetch_batch(self, payload: dict[str, Any], start: int) -> list[DuolingoLexeme]:
        limit = self.config.page_size

        params: dict[str, str | int] = {
            "limit": limit,
            "sortBy": "LEARNED_DATE",
            "startIndex": start,
        }
        url = self._build_url()
        headers = self._build_headers()

        r = httpx.post(url, params=params, headers=headers, json=payload)
        if r.status_code in (401, 403, 406):
            print(f"Error {r.status_code}: {r.text}")
            raise RuntimeError(
                "Duolingo session expired — refresh DUOLINGO_AUTHENTIFICATION in .env"
            )
        r.raise_for_status()

        data = r.json()

        batch = data.get("learnedLexemes", [])
        return [DuolingoLexeme(**lexeme) for lexeme in batch]

    def _load_payload(self) -> Any:
        with open(self.config.payload_file) as f:
            return json.load(f)

    def _build_headers(self) -> dict[str, str]:
        return {
            **self._STATIC_HEADERS,
            "Authorization": self.config.auth_token,
            "Accept-Language": self.config.accept_language,
        }

    def _build_url(self) -> str:
        return (
            f"{self.config.base_url}/users/{self.config.user_id}"
            f"/courses/{self.config.target_language}/{self.config.source_language}"
            f"/learned-lexemes"
        )
