from argparse import ArgumentParser
from pathlib import Path

from dotenv import load_dotenv

from lexharvest.agents.enricher import EnricherAgent
from lexharvest.agents.splitter import SplitterAgent
from lexharvest.config import (
    load_db_config,
    load_duolingo_config,
    load_enricher_config,
    load_llm_config,
    load_normalizer_config,
)
from lexharvest.db.models import RawEntry
from lexharvest.db.repository import LexRepository
from lexharvest.db.schema import init_db
from lexharvest.dictionaries.wiktionary import WiktionaryClient
from lexharvest.exporters import EXPORTER_REGISTRY
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
    )
    parser.add_argument(
        "--export-format",
        type=str,
        default="anki-apkg",
        choices=EXPORTER_REGISTRY.keys(),
        help="Export format to use when --export is specified",
    )
    parser.add_argument(
        "--anki-template",
        type=str,
        default="anki_template.toml",
        help="Path to Anki export template TOML file (only used if --export-format is \
            an Anki format)",
    )
    parser.add_argument(
        "--overwrite-export",
        action="store_true",
        default=False,
        help="Whether to overwrite the export file if it already exists",
    )
    args = parser.parse_args()

    if args.export is not None and not args.overwrite_export:
        export_path = Path(args.export)
        if export_path.exists():
            print(
                f"Error: Export file '{export_path}' already exists. Use "
                "--overwrite-export to overwrite it."
            )
            return

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

    enricher_config = load_enricher_config(args.config)
    language_hints_path = enricher_config.get("language_hints_path")
    language_hints_path = Path(language_hints_path) if language_hints_path else None

    enricher = EnricherAgent(
        provider=llm_config["provider"],
        model_name=llm_config["model"],
        base_url=llm_config["base_url"],
        target_language=target_language,
        source_language=source_language,
        language_hints_path=language_hints_path,
    )

    normalizer_config = load_normalizer_config(args.config)
    target_normalizer = SpaCyNormalizer(
        normalizer_config["target_language"], normalizer_config["target_model"]
    )
    source_normalizer = SpaCyNormalizer(
        normalizer_config["source_language"], normalizer_config["source_model"]
    )

    dict_client = WiktionaryClient()
    try:
        pipeline = Pipeline(
            repo=repo,
            splitter=splitter,
            target_normalizer=target_normalizer,
            source_normalizer=source_normalizer,
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
        f"{stats.dict_misses} | Enriched: {stats.enriched} | Enrich errors: "
        f"{stats.enrich_errors} | Needs review: {stats.needs_review}"
    )

    if args.export:
        output_path = Path(args.export)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        entries = repo.get_vocab_entries_by_status("done")

        exporter_cls = EXPORTER_REGISTRY[args.export_format]
        exporter = exporter_cls(template_path=Path(args.anki_template))
        exporter.export(entries, output_path)
        print(f"Exported {len(entries)} entries to {output_path}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
