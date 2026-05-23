from typing import Literal, Protocol

PosHint = Literal["noun", "verb", "adjective", "adverb", "other"]


class BaseNormalizer(Protocol):
    def normalize(self, surface_form: str, pos_hint: PosHint | None = None) -> str | None: ...
