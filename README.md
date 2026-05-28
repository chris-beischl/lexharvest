# lexharvest

Personal vocabulary pipeline: extract words from Duolingo, enrich them via an LLM agent, and export to CSV for use in any vocabulary trainer.

## What it does

1. **Extract** — fetches your learned vocabulary from Duolingo via the unofficial API
2. **Enrich** — runs each word through a normalizer and dictionary lookup, then an LLM agent fills in gender, irregular flag, example sentence, and disambiguation notes
3. **Export** — writes a clean CSV ready for Anki or any other vocabulary trainer

Ambiguous words (e.g. *cuento* as noun vs. verb) are split into separate entries by the agent. Words not found in any dictionary are skipped and logged.

---

## Setup

**Requirements:** Python 3.12+, [uv](https://docs.astral.sh/uv/)

```sh
git clone <repo>
cd lexharvest
uv sync
```

Copy the example config files:

```sh
cp .env.example .env
cp config.toml.example config.toml
touch duolingo_payload.json
```

---

## Getting your Duolingo credentials

Duolingo doesn't have a public API, so you need to grab your session credentials from the browser. This takes about 2 minutes.

### Step 1 — Open the vocabulary page

Go to [duolingo.com/practice-hub/words](https://www.duolingo.com/practice-hub/words). You should see your full word list.

![Duolingo vocabulary page](docs/screenshots/01_vocabulary_page.png)

---

### Step 2 — Open DevTools and go to the Network tab

Open your browser's developer tools (`F12` or `Cmd+Option+I` on Mac) and switch to the **Network** tab. Reload the page if no requests appear.

Filter by `lex` to narrow down the requests. Look for a request called **`learned-lexemes`** and click on it.

![DevTools network tab](docs/screenshots/02_devtools_headers.png)

---

### Step 3 — Copy your credentials into `.env` and `config.toml`

In the **Headers** tab of the `learned-lexemes` request, find:

- **`Authorization`** — copy the full value (starts with `Bearer eyJ...`) and paste it into `.env`:
  ```
  DUOLINGO_AUTHENTIFICATION=Bearer eyJ...
  ```
- **URL** — the URL contains your `user_id`, `target_language`, and `source_language`:
  ```
  /users/{user_id}/courses/{target_language}/{source_language}/learned-lexemes
  ```
  Update these three values in `config.toml`.

---

### Step 4 — Copy the request payload into `duolingo_payload.json`

In Safari: scroll to the bottom of the **Headers** tab and click the arrow next to **Request data** to expand it — the entire content is the payload.

In Chrome/Firefox: switch to the **Payload** tab.

![DevTools payload](docs/screenshots/03_devtools_payload.png)

Copy the entire JSON body and paste it into `duolingo_payload.json`.

![Payload content](docs/screenshots/04_payload_content.png)

---

### Step 5 — Configure your LLM

Open `config.toml` and set your provider and model:

```toml
[llm]
provider = "ollama"       # "ollama" | "openai" | "anthropic"
model = "gemma4:e2b"
# base_url = "http://localhost:11434/v1"   # ollama only
```

For cloud providers, add the corresponding API key to `.env`:

```
OPENAI_API_KEY=sk-...
# or
ANTHROPIC_API_KEY=sk-ant-...
```

---

### Step 6 — Install the spaCy language model

The normalizer uses a spaCy model for your target language. You need to install it manually — find the right model for your language on the [spaCy models page](https://spacy.io/usage/models), then install it with:

```sh
uv run python -m spacy download <model-name>
```

For example, for Spanish:

```sh
uv run python -m spacy download es_core_news_sm
```

Update `config.toml` with the model name you chose:

```toml
[normalizer]
model = "es_core_news_sm"
```

---

## Run

```sh
uv run python -m lexharvest
```

**Flags:**

| Flag | Description |
|---|---|
| `--skip-scrape` | Skip fetching from Duolingo, process existing DB entries only |
| `--retry-errors` | Reset all errored entries to pending and reprocess them |
| `--concurrency N` | Number of concurrent LLM calls (default: 1) |
| `--dict-concurrency N` | Number of concurrent Wiktionary requests (default: 1) |
