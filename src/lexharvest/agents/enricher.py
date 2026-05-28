import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from pydantic_ai import Agent

from lexharvest.db.models import VocabEntry

BASE_SYSTEM_PROMPT = """You are enriching a vocabulary entry for a language learner.

The target language (the language being learned) is TARGET_LANGUAGE.
The source language (the learner's native language) is SOURCE_LANGUAGE.

Given a word in TARGET_LANGUAGE with its translations in SOURCE_LANGUAGE and
optional dictionary data in English, fill in the missing linguistic metadata.

- gender: ONLY for nouns. Set to "masculine", "feminine", or "neuter" based on the
  grammatical gender of the noun in TARGET_LANGUAGE. For every other part of
  speech — verbs, adjectives, adverbs, prepositions, conjunctions, determiners,
  pronouns, numerals, interjections — set to null, no exceptions.

- article: ONLY for nouns. Provide the definite article as it is actually used with
  this word in TARGET_LANGUAGE. The article MUST be a TARGET_LANGUAGE article —
  never use a SOURCE_LANGUAGE article. IMPORTANT: the article may differ from what
  the gender alone implies — for example, Spanish "agua" is grammatically feminine
  but uses the masculine article "el" in singular to avoid the vowel clash, so
  article is "el" not "la". For every other part of speech, set to null.

- is_phrase: true for multi-word expressions, idioms, and verbal periphrases.
  false for single words and compound nouns. When unsure, ask: do these words need
  to appear together to carry the intended meaning?

- translations: the translations have already been normalized by a linguistic tool.
  Your default answer is null. Only return a replacement list in the rare case that
  the translations are completely broken (e.g. raw HTML, garbled text, or gibberish).
  Do NOT add translations, do NOT rephrase, do NOT expand, do NOT improve — if the
  translations look reasonable at all, return null.

- disambiguation_note: write exclusively in SOURCE_LANGUAGE. Only include if this
  word is easily confused with another, or if a phrase has a non-obvious or idiomatic
  meaning. null if not needed.

- example_translation: translate the provided example sentence into SOURCE_LANGUAGE
  naturally. The translation MUST be in SOURCE_LANGUAGE — never in English or any
  other language. null if no example is provided.

- irregular: true if the word has irregular forms that a learner should be aware of.
  For verbs: irregular conjugation (e.g. ir, ser, tener). For nouns: irregular plural
  (e.g. el lápiz → los lápices). For adjectives: irregular comparative/superlative.
  false if the word follows standard rules. When uncertain, set needs_review to true.

- needs_review: true if you are uncertain about any field."""


class EnrichmentResult(BaseModel):
    gender: Literal["masculine", "feminine", "neuter"] | None  # nouns only, None otherwise
    article: str | None  # definite article appropriate for the target language, if applicable
    is_phrase: bool
    disambiguation_note: str | None  # brief, in German, only if genuinely confusable
    example_translation: str | None  # German translation of example_sentence
    translations: list[str] | None  # normalized translations in the source language
    needs_review: bool  # True if uncertain about any field
    irregular: bool  # True if the word is irregular in any way


class EnricherAgent:
    def __init__(
        self,
        provider: str,
        model_name: str,
        target_language: str,
        source_language: str,
        base_url: str | None = None,
        language_hints_path: Path | None = None,
    ):
        from pydantic_ai.output import NativeOutput

        from lexharvest.llm.factory import build_model

        language_hints = ""
        if language_hints_path is not None:
            with open(language_hints_path) as f:
                hint = json.load(f).get(target_language)
                if hint is not None:
                    language_hints = "\n\n" + hint.strip()

        system_prompt = (
            (BASE_SYSTEM_PROMPT + language_hints)
            .replace("TARGET_LANGUAGE", target_language)
            .replace("SOURCE_LANGUAGE", source_language)
        )

        model, use_native = build_model(provider, model_name, base_url)
        output_type = NativeOutput(EnrichmentResult) if use_native else EnrichmentResult
        self._agent = Agent(model, output_type=output_type, system_prompt=system_prompt)

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
