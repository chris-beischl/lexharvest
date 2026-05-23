import os
from pathlib import Path
from typing import Any

import tomllib
from dotenv import load_dotenv

from .scrapers.duolingo import DuolingoConfig


def load_config(config_path: str | Path = "config.toml") -> dict[str, Any]:
    with open(Path(config_path), "rb") as f:
        return tomllib.load(f)


def load_duolingo_config(config_path: str | Path = "config.toml") -> DuolingoConfig:
    load_dotenv()
    config = load_config(config_path)
    return DuolingoConfig(**config["duolingo"], auth_token=os.environ["DUOLINGO_AUTHENTIFICATION"])


def load_db_config(config_path: str | Path = "config.toml") -> Any:
    return load_config(config_path)["database"]
