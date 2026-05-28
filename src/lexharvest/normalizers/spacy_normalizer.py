import json
from pathlib import Path

import spacy

from .base import BaseNormalizer, PosHint

_DEFAULT_POS_HINTS = Path(__file__).parent / "pos_hints.json"


class SpaCyNormalizer(BaseNormalizer):
    def __init__(self, language: str, model: str, pos_hints: str | Path = _DEFAULT_POS_HINTS):
        self.language = language
        try:
            self.nlp = spacy.load(model)
        except OSError:
            raise RuntimeError(
                f"Failed to load SpaCy model '{model}'. "
                "Make sure it's installed and available in your environment using"
                f" `uv run python -m spacy download {model}`"
            ) from None

        with open(pos_hints) as f:
            self.pos_hints = json.load(f)[self.language]

    def normalize(self, surface_form: str, pos_hint: PosHint | None = None) -> str:
        prefix = self.pos_hints.get(pos_hint)

        text = f"{prefix} {surface_form}" if prefix else surface_form
        doc = self.nlp(text)

        return doc[-1].lemma_

    def __call__(self, surface_form: str, pos_hint: PosHint | None = None) -> str:
        return self.normalize(surface_form, pos_hint)
