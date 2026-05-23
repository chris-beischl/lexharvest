# lexharvest

Personal vocabulary pipeline: extract words from Duolingo, enrich them via an LLM agent, and export to CSV for use in any vocabulary trainer.

## What it does

1. **Extract** — fetches your learned vocabulary from Duolingo via the unofficial API
2. **Enrich** — runs each word through a normalizer and dictionary lookup, then an LLM agent fills in gender, irregular flag, example sentence, and disambiguation notes
3. **Export** — writes a clean CSV ready for Anki or any other vocabulary trainer

Ambiguous words (e.g. *cuento* as noun vs. verb) are split into separate entries by the agent. Words not found in any dictionary are skipped and logged.

## Setup

**Requirements:** Python 3.12+, [uv](https://docs.astral.sh/uv/)

```sh
git clone <repo>
cd lexharvest
uv sync
```

Copy the example config files and fill in your details:

```sh
cp .env.example .env
cp config.toml.example config.toml
touch duolingo_payload.json
```

**`.env`** — your Duolingo Bearer token (copy from browser DevTools → Network → any `learned-lexemes` request → Authorization header)

**`config.toml`** — your user ID, language pair, and paths

**`duolingo_payload.json`** — the POST body from the same DevTools request (copy request body, save as JSON file). See config for the expected path.

## Run

```sh
uv run python -m lexharvest
```
