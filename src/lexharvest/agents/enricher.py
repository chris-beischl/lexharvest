from typing import Literal

from pydantic import BaseModel
from pydantic_ai import Agent

from lexharvest.db.models import VocabEntry

SYSTEM_PROMPT = """You are enriching a vocabulary entry for a language learner.

Given a word in the target language with its translations in the source language and
dictionary data in English, fill in the missing linguistic metadata.

- gender: grammatical gender appropriate for the target language (e.g. masculine,
  feminine, neuter). null if not applicable to this word or language.
- is_phrase: true for multi-word expressions, idioms, and verbal periphrases
  (e.g. tener que, a veces, terminar de). false for single words and compound
  nouns (e.g. lentes de sol). When unsure, ask: do these words need to appear
  together to carry the intended meaning?
- disambiguation_note: write exclusively in the source language specified in the
  input. Only include if this word is easily confused with another, or if a phrase
  has a non-obvious or idiomatic meaning (e.g. verbal periphrases like
  'terminar de + inf'). null if not needed.
- example_translation: translate the provided example sentence into the source
  language naturally. null if no example is provided.
- needs_review: true if you are uncertain about any field."""


class EnrichmentResult(BaseModel):
    gender: Literal["masculine", "feminine"] | None  # nouns only, None otherwise
    is_phrase: bool
    disambiguation_note: str | None  # brief, in German, only if genuinely confusable
    example_translation: str | None  # German translation of example_sentence
    needs_review: bool  # True if uncertain about any field


class EnricherAgent:
    def __init__(self, provider: str, model_name: str, base_url: str | None = None):
        from pydantic_ai.output import NativeOutput

        from lexharvest.llm.factory import build_model

        model, use_native = build_model(provider, model_name, base_url)
        output_type = NativeOutput(EnrichmentResult) if use_native else EnrichmentResult
        self._agent = Agent(model, output_type=output_type, system_prompt=SYSTEM_PROMPT)

    async def enrich(self, vocab: VocabEntry) -> EnrichmentResult:
        prompt = (
            f"word: '{vocab.canonical_form}' ({vocab.target_language})\n"
            f"source_language: {vocab.source_language}\n"
            f"part_of_speech: {vocab.part_of_speech or 'unknown'}\n"
            f"definitions: {vocab.definitions}\n"
            f"translations ({vocab.source_language}): {vocab.translations}\n"
            f"example: {vocab.example_sentence or 'none'}"
        )
        result = await self._agent.run(prompt)
        return result.output
