import asyncio
from dataclasses import dataclass
from typing import cast

from tqdm import tqdm

from lexharvest.agents.splitter import SplitDecision, SplitterAgent
from lexharvest.db.models import RawEntry, VocabEntry
from lexharvest.db.repository import LexRepository
from lexharvest.normalizers.base import BaseNormalizer, PosHint, strip_article


@dataclass
class PipelineStats:
    processed: int = 0
    split: int = 0  # parent entries split into children
    done: int = 0  # completed to VocabEntry
    errors: int = 0


class Pipeline:
    def __init__(
        self,
        repo: LexRepository,
        splitter: SplitterAgent,
        normalizer: BaseNormalizer,
        concurrency: int = 1,
    ):
        self.repo = repo
        self.splitter = splitter
        self.normalizer = normalizer
        self.concurrency = concurrency

    async def run(self) -> PipelineStats:
        stats = PipelineStats()
        pending = self.repo.get_raw_entries_by_status("pending")
        sem = asyncio.Semaphore(self.concurrency)

        async def bounded(entry: RawEntry) -> None:
            async with sem:
                await self._process(entry, stats)

        tasks = [bounded(entry) for entry in pending]
        for coro in tqdm(asyncio.as_completed(tasks), total=len(tasks)):
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

    def _run_normalize(self, hint_form: str, pos_hint: PosHint, language: str) -> str:
        canonical = strip_article(hint_form, language)
        if " " not in canonical:
            canonical = self.normalizer.normalize(canonical, pos_hint)
        return canonical

    async def _run_dict_lookup(self, canonical_form: str, language: str) -> None:
        pass  # TODO

    async def _run_enrich(self) -> None:
        pass  # TODO

    async def _process(self, entry: RawEntry, stats: PipelineStats) -> None:
        # try/except wraps everything; on exception → status="error", log
        # 1. splitter.split()
        #    → should_split: insert children as new RawEntry(split_from_id=parent.id,
        #                    surface_form=hint_form, pos_hint=..., raw_translations=subset)
        #                    mark parent status="split", return
        # 2. normalizer.normalize(surface_form, pos_hint or "other") → canonical_form
        # 3. dict lookup   ← stub (TODO)
        # 4. enricher      ← stub (TODO)
        # 5. insert VocabEntry(needs_review=True), mark RawEntry status="done"
        # log each step via repo.log()

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
            canonical_form = self._run_normalize(hint_form, pos_hint, entry.target_language)
            self.repo.update_raw_entry(entry.id, canonical_form=canonical_form)
            self.repo.log(entry.id, "normalize", "success", canonical_form)

            # 3. dict lookup  (TODO)
            # 4. enrich       (TODO)

            # 5. write vocab stub
            existing = self.repo.get_vocab_entry(canonical_form, entry.target_language)
            if existing is not None:
                assert existing.id is not None
                self.repo.update_raw_entry(entry.id, status="done", vocab_entry_id=existing.id)
                self.repo.log(
                    entry.id, "db_write", "skipped", f"linked to existing vocab {existing.id}"
                )
            else:
                vocab = VocabEntry(
                    canonical_form=canonical_form,
                    target_language=entry.target_language,
                    source_language=entry.source_language,
                    translations=entry.raw_translations,
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
