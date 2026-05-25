from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.output import NativeOutput

from lexharvest.llm.factory import build_model
from lexharvest.normalizers.base import PosHint

SYSTEM_PROMPT = """You are a vocabulary analyst for language learning.

Given a word in the target language and its translations, decide if it represents
multiple distinct meanings that require separate vocabulary entries.

Split when: the same word form covers genuinely different meanings with different
parts of speech (e.g. a noun AND a verb with different lemmas).

Do NOT split when: translations are just synonyms or register variants of the same meaning.

IMPORTANT: Only split if the EXACT same word form functions as genuinely different
parts of speech in the target language. Do NOT create entries for related words with
different forms (e.g. do not split 'alquilar' into a verb and 'el alquiler' — those
are different words entirely).
Base your decision on the target language word's properties, not on whether the
translations happen to look like different parts of speech.

For each entry after splitting, provide:
- hint_form: the word as it should appear (e.g. 'el cuento' for noun, 'contar' for verb)
- translations: the subset of translations relevant to this entry
- pos_hint: the part of speech

If should_split is false, return entries as an empty list."""


class SplitEntry(BaseModel):
    hint_form: str
    translations: list[str]
    pos_hint: PosHint


class SplitDecision(BaseModel):
    should_split: bool
    entries: list[SplitEntry]


class SplitterAgent:
    def __init__(self, provider: str, model_name: str, base_url: str | None = None):
        _model, use_native = build_model(provider, model_name, base_url)

        output_type = NativeOutput(SplitDecision) if use_native else SplitDecision
        self._agent = Agent(
            model=_model,
            output_type=output_type,
            system_prompt=SYSTEM_PROMPT,
        )

    async def split(
        self,
        word: str,
        translations: list[str],
        target_language: str,
        source_language: str,
    ) -> SplitDecision:

        prompt = (
            f"word: '{word}' ({target_language})\ntranslations ({source_language}): {translations}"
        )

        result = await self._agent.run(prompt)
        return result.output
