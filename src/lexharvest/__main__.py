from argparse import ArgumentParser

from lexharvest.config import load_duolingo_config
from lexharvest.scrapers.duolingo import DuolingoExtractor


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("--config", default="config.toml", type=str)
    args = parser.parse_args()

    config = load_duolingo_config(args.config)
    extractor = DuolingoExtractor(config)
    print(len(extractor.extract()))


if __name__ == "__main__":
    main()
