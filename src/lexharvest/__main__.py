from argparse import ArgumentParser

from lexharvest.config import load_db_config, load_duolingo_config
from lexharvest.db.models import RawEntry
from lexharvest.db.repository import LexRepository
from lexharvest.db.schema import init_db
from lexharvest.scrapers.duolingo import DuolingoExtractor


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--config", default="config.toml", type=str)
    parser.add_argument("--skip-scrape", action="store_true", default=False)
    args = parser.parse_args()

    scraper_config = load_duolingo_config(args.config)
    target_language = scraper_config.target_language
    source_language = scraper_config.source_language

    db_config = load_db_config(args.config)
    conn = init_db(db_config["path"])
    repo = LexRepository(conn)

    inserted = 0
    skipped = 0
    if not args.skip_scrape:
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


if __name__ == "__main__":
    main()
