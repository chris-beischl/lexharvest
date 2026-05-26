from typing import Literal, Protocol

PosHint = Literal["noun", "verb", "adjective", "adverb", "other"]


class BaseNormalizer(Protocol):
    def normalize(self, surface_form: str, pos_hint: PosHint | None = None) -> str: ...


_ARTICLES: dict[str, set[str]] = {
    "es": {"el", "la", "los", "las", "un", "una", "unos", "unas"},
}


def strip_article(hint_form: str, language: str) -> str:
    articles = _ARTICLES.get(language, set())
    parts = hint_form.strip().split(maxsplit=1)
    if len(parts) == 2 and parts[0].lower() in articles:
        return parts[1]
    return hint_form
