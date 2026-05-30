import asyncio
import json
from dataclasses import dataclass
from typing import cast

from tqdm import tqdm

from lexharvest.agents.enricher import EnricherAgent, EnrichmentResult
from lexharvest.agents.splitter import SplitDecision, SplitterAgent
from lexharvest.db.models import RawEntry, VocabEntry
from lexharvest.db.repository import LexRepository
from lexharvest.dictionaries.wiktionary import WiktionaryClient
from lexharvest.normalizers.base import BaseNormalizer, PosHint, strip_article


@dataclass
class PipelineStats:
    processed: int = 0
    split: int = 0  # parent entries split into children
    done: int = 0  # completed to VocabEntry
    errors: int = 0
    dict_hits: int = 0
    dict_misses: int = 0
    enriched: int = 0
    enrich_errors: int = 0
    needs_review: int = 0  # entries the LLM flagged as uncertain


class Pipeline:
    def __init__(
        self,
        repo: LexRepository,
        splitter: SplitterAgent,
        target_normalizer: BaseNormalizer,
        source_normalizer: BaseNormalizer,
        dict_client: WiktionaryClient,
        enricher: EnricherAgent,
        concurrency: int = 1,
        dict_concurrency: int = 1,
    ):
        self.repo = repo
        self.splitter = splitter
        self.target_normalizer = target_normalizer
        self.source_normalizer = source_normalizer
        self.dict_client = dict_client
        self.enricher = enricher
        self.concurrency = concurrency
        self.dict_concurrency = dict_concurrency

    async def run(self) -> PipelineStats:
        stats = PipelineStats()
        sem = asyncio.Semaphore(self.concurrency)
        dict_sem = asyncio.Semaphore(self.dict_concurrency)

        # Phase 1: pending raw_entries → split → normalize → VocabEntry(normalized)
        pending = self.repo.get_raw_entries_by_status("pending")

        async def normalize(entry: RawEntry) -> None:
            async with sem:
                await self._normalize_entry(entry, stats)

        tasks = [normalize(e) for e in pending]
        for coro in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="normalize"):
            await coro

        # Phase 2: VocabEntry(normalized) → dict lookup → dict_looked_up
        normalized = self.repo.get_vocab_entries_by_status("normalized")

        async def dict_lookup(vocab: VocabEntry) -> None:
            async with dict_sem:
                try:
                    await self._run_dict_lookup(vocab)
                    stats.dict_hits += 1
                except Exception:
                    stats.dict_misses += 1  # will retry next run (status stays "normalized")

        tasks2 = [dict_lookup(v) for v in normalized]
        for coro in tqdm(asyncio.as_completed(tasks2), total=len(tasks2), desc="dict lookup"):
            await coro

        # Phase 3: VocabEntry(dict_looked_up) → enrich → done
        to_enrich = self.repo.get_vocab_entries_by_status("dict_looked_up")

        async def enrich(vocab: VocabEntry) -> None:
            async with sem:
                try:
                    result = await self._run_enrich(vocab)
                    stats.enriched += 1
                    if result.needs_review:
                        stats.needs_review += 1
                except Exception:
                    stats.enrich_errors += 1  # status stays "dict_looked_up", retried next run

        tasks3 = [enrich(v) for v in to_enrich]
        for coro in tqdm(asyncio.as_completed(tasks3), total=len(tasks3), desc="enrich"):
            await coro

        return stats

    async def _run_split(self, entry: RawEntry) -> SplitDecision:
        for attempt in range(5):
            try:
                return await self.splitter.split(
                    word=entry.surface_form,
                    translations=entry.raw_translations,
                    target_language=entry.target_language,
                    source_language=entry.source_language,
                )
            except Exception as e:
                if "429" in str(e) and attempt < 4:
                    await asyncio.sleep(2**attempt)
                    continue
                raise
        raise RuntimeError("unreachable")

    def _run_normalize_target(self, hint_form: str, pos_hint: PosHint, language: str) -> str:
        canonical = strip_article(hint_form, language)
        if " " not in canonical:
            canonical = self.target_normalizer.normalize(canonical, pos_hint)
        return canonical

    def _run_normalize_source(
        self, raw_translations: list[str], pos_hint: PosHint, language: str
    ) -> list[str]:
        translations = []
        for t in raw_translations:
            translation = strip_article(t, language)
            if " " not in translation:
                translation = self.source_normalizer.normalize(translation, pos_hint)
            translations.append(translation)

        # remove duplicates
        seen = set()
        unique_translations = []
        for t in translations:
            if t not in seen:
                seen.add(t)
                unique_translations.append(t)
        return unique_translations

    async def _run_dict_lookup(self, vocab: VocabEntry) -> None:
        assert vocab.id is not None
        result = await self.dict_client.lookup(vocab.canonical_form, vocab.target_language)
        if result is None:
            self.repo.update_vocab_entry(vocab.id, status="dict_looked_up")
            return

        self.repo.update_vocab_entry(
            vocab.id,
            status="dict_looked_up",
            part_of_speech=result.part_of_speech,
            example_sentence=result.example_sentence,
            example_translation=result.example_translation,
            definitions=json.dumps(result.definitions),
            dict_source="wiktionary",
        )

    async def _run_enrich(self, vocab: VocabEntry) -> EnrichmentResult:
        assert vocab.id is not None
        enriched = await self.enricher.enrich(vocab)
        self.repo.update_vocab_entry(
            vocab.id,
            status="done",
            gender=enriched.gender,
            article=enriched.article,
            irregular=enriched.irregular,
            is_phrase=enriched.is_phrase,
            translations=enriched.translations or vocab.translations,
            part_of_speech=None if enriched.is_phrase else vocab.part_of_speech,
            disambiguation_note=enriched.disambiguation_note,
            example_translation=enriched.example_translation,
            needs_review=enriched.needs_review,
        )
        return enriched

    async def _normalize_entry(self, entry: RawEntry, stats: PipelineStats) -> None:
        assert entry.id is not None
        try:
            # 1. split --------------------------------------------------------
            if entry.split_from_id is None:
                decision = await self._run_split(entry)
                self.repo.log(entry.id, "split", "success", None)

                if decision.should_split:
                    for split_entry in decision.entries:
                        child = RawEntry(
                            surface_form=split_entry.hint_form,
                            target_language=entry.target_language,
                            source_language=entry.source_language,
                            raw_translations=split_entry.translations,
                            pos_hint=split_entry.pos_hint,
                            split_from_id=entry.id,
                        )
                        self.repo.insert_raw_entry(child)
                    self.repo.update_raw_entry(entry.id, status="split")
                    stats.split += 1
                    return

                hint_form = decision.entries[0].hint_form
                pos_hint = decision.entries[0].pos_hint
            else:
                # already a split child — hint_form and pos_hint set by parent
                hint_form = entry.surface_form
                pos_hint = cast(PosHint, entry.pos_hint or "other")

            # 2. normalize ----------------------------------------------------
            canonical_form = self._run_normalize_target(hint_form, pos_hint, entry.target_language)
            translations = self._run_normalize_source(
                entry.raw_translations, pos_hint, entry.source_language
            )
            self.repo.update_raw_entry(entry.id, canonical_form=canonical_form)
            self.repo.log(entry.id, "normalize", "success", canonical_form)

            # 3. create/link VocabEntry ---------------------------------------
            existing = self.repo.get_vocab_entry(canonical_form, entry.target_language)
            if existing is not None:
                assert existing.id is not None
                self.repo.update_raw_entry(entry.id, status="done", vocab_entry_id=existing.id)
                self.repo.log(
                    entry.id,
                    "db_write",
                    "skipped",
                    f"linked to existing vocab {existing.id}",
                )
            else:
                vocab = VocabEntry(
                    canonical_form=canonical_form,
                    target_language=entry.target_language,
                    source_language=entry.source_language,
                    translations=translations,
                    needs_review=True,
                )
                vocab_id = self.repo.insert_vocab_entry(vocab)
                self.repo.update_raw_entry(entry.id, status="done", vocab_entry_id=vocab_id)
                self.repo.log(entry.id, "db_write", "success", None)
            stats.done += 1

        except Exception as e:
            self.repo.update_raw_entry(entry.id, status="error", error_message=str(e))
            self.repo.log(entry.id, "pipeline", "failure", str(e))
            stats.errors += 1

        finally:
            stats.processed += 1
