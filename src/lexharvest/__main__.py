from argparse import ArgumentParser

from dotenv import load_dotenv

from lexharvest.agents.splitter import SplitterAgent
from lexharvest.config import load_db_config, load_duolingo_config, load_llm_config
from lexharvest.db.models import RawEntry
from lexharvest.db.repository import LexRepository
from lexharvest.db.schema import init_db
from lexharvest.scrapers.duolingo import DuolingoExtractor


async def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--config", default="config.toml", type=str)
    parser.add_argument("--skip-scrape", action="store_true", default=False)
    args = parser.parse_args()

    load_dotenv()

    scraper_config = load_duolingo_config(args.config)
    target_language = scraper_config.target_language
    source_language = scraper_config.source_language

    db_config = load_db_config(args.config)
    conn = init_db(db_config["path"])
    repo = LexRepository(conn)

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

    splitter = SplitterAgent(f"{llm_config['provider']}:{llm_config['model']}")

    # smoke test: run splitter on first pending entry
    pending = repo.get_raw_entries_by_status("pending")
    if pending:
        entry = pending[0]
        decision = await splitter.split(
            word=entry.surface_form,
            translations=entry.raw_translations,
            target_language=entry.target_language,
            source_language=entry.source_language,
        )
        print(f"Tested: '{entry.surface_form}' → split={decision.should_split}")
        for e in decision.entries:
            print(f"  {e.hint_form} [{e.pos_hint}]: {e.translations}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
