from argparse import ArgumentParser
from pathlib import Path

from dotenv import load_dotenv

from lexharvest.agents.enricher import EnricherAgent
from lexharvest.agents.splitter import SplitterAgent
from lexharvest.config import (
    load_db_config,
    load_duolingo_config,
    load_llm_config,
    load_normalizer_config,
)
from lexharvest.db.models import RawEntry
from lexharvest.db.repository import LexRepository
from lexharvest.db.schema import init_db
from lexharvest.dictionaries.wiktionary import WiktionaryClient
from lexharvest.exporters.anki import AnkiExporter
from lexharvest.normalizers.spacy_normalizer import SpaCyNormalizer
from lexharvest.pipeline import Pipeline
from lexharvest.scrapers.duolingo import DuolingoExtractor


async def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--config", default="config.toml", type=str)
    parser.add_argument("--skip-scrape", action="store_true", default=False)
    parser.add_argument("--retry-errors", action="store_true", default=False)
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Number of concurrent processing tasks",
    )
    parser.add_argument(
        "--dict-concurrency",
        type=int,
        default=1,
        help="Number of concurrent Wiktionary lookup requests",
    )
    parser.add_argument(
        "--export",
        type=str,
        default=None,
        metavar="FILENAME",
        help="Export completed entries as an Anki-ready CSV to the given file path",
    )
    args = parser.parse_args()

    load_dotenv()

    scraper_config = load_duolingo_config(args.config)
    target_language = scraper_config.target_language
    source_language = scraper_config.source_language

    db_config = load_db_config(args.config)
    conn = init_db(db_config["path"])
    repo = LexRepository(conn)

    if args.retry_errors:
        errors = repo.get_raw_entries_by_status("error")
        for e in errors:
            assert e.id is not None
            repo.update_raw_entry(e.id, status="pending", error_message=None)
        print(f"Reset {len(errors)} errored entries to pending")

    if not args.skip_scrape:
        inserted = 0
        skipped = 0
        extractor = DuolingoExtractor(scraper_config)
        all_lexeme = extractor.extract()

        for lexeme in all_lexeme:
            if repo.get_raw_entry(lexeme.text, language=target_language) is not None:
                skipped += 1
                continue

            entry = RawEntry(
                surface_form=lexeme.text,
                target_language=target_language,
                source_language=source_language,
                raw_translations=lexeme.translations,
            )
            repo.insert_raw_entry(entry)
            inserted += 1

        print(f"Inserted: {inserted} | Skipped (duplicate): {skipped}")

    llm_config = load_llm_config(args.config)
    splitter = SplitterAgent(
        provider=llm_config["provider"],
        model_name=llm_config["model"],
        base_url=llm_config["base_url"],
    )

    enricher = EnricherAgent(
        provider=llm_config["provider"],
        model_name=llm_config["model"],
        base_url=llm_config["base_url"],
    )

    normalizer_config = load_normalizer_config(args.config)
    normalizer = SpaCyNormalizer(normalizer_config["language"], normalizer_config["model"])

    dict_client = WiktionaryClient()
    try:
        pipeline = Pipeline(
            repo=repo,
            splitter=splitter,
            normalizer=normalizer,
            dict_client=dict_client,
            enricher=enricher,
            concurrency=args.concurrency,
            dict_concurrency=args.dict_concurrency,
        )
        stats = await pipeline.run()
    finally:
        await dict_client.aclose()

    print(
        f"Processed: {stats.processed} | Split: {stats.split} | Done: {stats.done} "
        f"| Errors: {stats.errors} | Dict hits: {stats.dict_hits} | Dict misses: "
        f"{stats.dict_misses} | | Enriched: {stats.enriched} | Enrich errors: "
        f"{stats.enrich_errors}"
    )

    if args.export:
        output_path = Path(args.export)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        entries = repo.get_vocab_entries_by_status("done")
        AnkiExporter().export(entries, output_path)
        print(f"Exported {len(entries)} entries to {output_path}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
