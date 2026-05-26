import re

import httpx
from pydantic import BaseModel


class WiktionaryResult(BaseModel):
    part_of_speech: str | None
    definitions: list[str]
    example_sentence: str | None
    example_translation: str | None


class WiktionaryClient:
    BASE_URL = "https://en.wiktionary.org/api/rest_v1/page/definition"
    HEADERS = {
        "User-Agent": "lexharvest/0.1 \
        (https://github.com/chris-beischl/lexharvest)"
    }

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(headers=self.HEADERS)

    async def lookup(self, word: str, language_code: str) -> WiktionaryResult | None:
        response = await self._client.get(f"{self.BASE_URL}/{word}")
        if response.status_code == 404:
            return None
        response.raise_for_status()

        entries = response.json().get(language_code)
        if not entries:
            return None

        entry = entries[0]
        defs = entry["definitions"][:3]

        # find first example
        example, translation = None, None
        for d in defs:
            if parsed := d.get("parsedExamples"):
                example = re.sub(r"<[^>]+>", "", parsed[0]["example"])
                translation = re.sub(r"<[^>]+>", "", parsed[0].get("translation", ""))
                break

        return WiktionaryResult(
            part_of_speech=entry.get("partOfSpeech"),
            definitions=[re.sub(r"<[^>]+>", "", d["definition"]) for d in defs],
            example_sentence=example,
            example_translation=translation,
        )

    async def aclose(self) -> None:
        await self._client.aclose()
