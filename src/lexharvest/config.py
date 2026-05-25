import os
from pathlib import Path
from typing import Any, TypedDict

import tomllib
from dotenv import load_dotenv

from .scrapers.duolingo import DuolingoConfig


class LlmConfig(TypedDict):
    provider: str
    model: str
    base_url: str | None


def load_config(config_path: str | Path = "config.toml") -> dict[str, Any]:
    with open(Path(config_path), "rb") as f:
        return tomllib.load(f)


def load_duolingo_config(config_path: str | Path = "config.toml") -> DuolingoConfig:
    load_dotenv()
    config = load_config(config_path)
    return DuolingoConfig(**config["duolingo"], auth_token=os.environ["DUOLINGO_AUTHENTIFICATION"])


def load_db_config(config_path: str | Path = "config.toml") -> Any:
    return load_config(config_path)["database"]


def load_llm_config(config_path: str | Path = "config.toml") -> LlmConfig:
    cfg = load_config(config_path)["llm"]
    return LlmConfig(
        provider=cfg["provider"],
        model=cfg["model"],
        base_url=cfg.get("base_url"),
    )


def load_normalizer_config(config_path: str | Path = "config.toml") -> Any:
    config = load_config(config_path)
    normalizer_config = {
        **config["normalizer"],
        "language": config["duolingo"]["target_language"],
    }
    return normalizer_config
