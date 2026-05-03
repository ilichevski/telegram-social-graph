# Telegram Social Graph

Local-first service for building a social graph from Telegram exports.

It parses your Telegram Desktop JSON export on your own machine, builds relationship snapshots and weekly history, and can optionally use a local `Ollama` model to estimate warmth, mutuality, and tension.

## License

This repository is released under the [Unlicense](./LICENSE). Anyone can use it for free, with no usage restrictions.

## Privacy

- Your Telegram export is processed locally.
- No Telegram data is included in this repository.
- Generated analysis files should stay out of version control.
- Optional LLM enrichment is designed for a local `Ollama` runtime, not a cloud API.

## What it does

- imports Telegram Desktop machine-readable JSON exports
- builds a local social graph from private chats
- tracks reciprocity, responsiveness, initiation balance, and activity volume
- builds snapshots on a chosen date and weekly history over time
- produces `graph.json`, `summary.json`, `relationship_timeseries.json`, and `report.html`
- optionally enriches chat warmth with a local `Ollama` model

## Requirements

- macOS or Linux
- Python `3.9+`
- Telegram Desktop export in `Machine-readable JSON`
- optional: `Ollama` for local LLM enrichment

## Quick start

### 1. Clone the repository

```bash
git clone https://github.com/ilichevski/telegram-social-graph.git
cd telegram-social-graph
```

### 2. Create the local environment

```bash
./scripts/setup_local.sh
```

This creates `.venv` and installs the package in editable mode.

### 3. Export your Telegram data

Use Telegram Desktop:

1. `Settings`
2. `Advanced`
3. `Export Telegram Data`
4. choose `Machine-readable JSON`

For the first run, exporting text is enough.

### 4. Put the export into the expected folder

Create this directory in the repo:

```bash
mkdir -p data/telegram-export
```

Then put your Telegram export there, for example:

- `data/telegram-export/result.json`
- or a directory containing multiple exported JSON files

`data/` is ignored by git, so your export will not be committed.

### 5. Run the analysis

```bash
./scripts/analyze_export.sh
```

This uses:

- `as_of_date = today`
- weekly snapshots over the last `91` days
- `window_days = 90`
- `cadence_days = 7`

Output goes to:

```text
artifacts/run-latest/
```

Open:

```text
artifacts/run-latest/report.html
```

## Optional: local LLM enrichment

If you want the service to score warmth with a local model, install `Ollama` first.

### Install Ollama

On macOS:

```bash
brew install --cask ollama
```

Or install it manually from:

- <https://ollama.com/>

### Pull the local models

```bash
./scripts/pull_models.sh
```

By default this pulls:

- `qwen3:8b`
- `embeddinggemma`

### Run analysis with local LLM enrichment

```bash
WITH_LLM=1 ./scripts/analyze_export.sh
```

## Makefile shortcuts

If you prefer `make`:

```bash
make setup
make models
make analyze
make analyze-llm
make test
make api
```

## Main files you get

After a run, the output directory contains:

- `report.html`
  interactive local report
- `summary.json`
  run metadata and aggregate metrics
- `graph.json`
  nodes and edges
- `graph.graphml`
  graph export for tools like Gephi
- `weekly_snapshots.json`
  network-level weekly history
- `relationship_timeseries.json`
  per-person timeseries
- `person_reports.json`
  per-person snapshot summary

## Run with a custom export path

You do not have to use `./data/telegram-export`.

Example:

```bash
EXPORT_PATH="/absolute/path/to/Telegram Export" ./scripts/analyze_export.sh
```

Custom output directory:

```bash
OUTPUT_DIR="./artifacts/my-run" ./scripts/analyze_export.sh
```

## Run with custom dates

Example:

```bash
AS_OF_DATE=2026-05-02 \
START_DATE=2026-01-31 \
WITH_LLM=1 \
./scripts/analyze_export.sh
```

## CLI usage

Direct CLI entrypoint:

```bash
social-graph analyze /path/to/export --output ./artifacts/run-001
```

Important flags:

- `--as-of-date YYYY-MM-DD`
- `--start-date YYYY-MM-DD`
- `--end-date YYYY-MM-DD`
- `--cadence-days 7`
- `--window-days 90`
- `--short-window-days 30`
- `--with-llm`

Rebuild the HTML report:

```bash
social-graph report ./artifacts/run-001/graph.json \
  --summary-json ./artifacts/run-001/summary.json \
  --output ./artifacts/run-001/report.html
```

## HTTP API

Start the local API:

```bash
make api
```

Health check:

```bash
curl http://127.0.0.1:8000/healthz
```

## Troubleshooting

### `python3` not found

Install Python `3.9+` and rerun:

```bash
./scripts/setup_local.sh
```

### `ollama` not found

Install Ollama first, then run:

```bash
./scripts/pull_models.sh
```

### `export path does not exist`

Either:

- put your export in `./data/telegram-export`

or run:

```bash
EXPORT_PATH="/absolute/path/to/export" ./scripts/analyze_export.sh
```

### `report.html` is missing

Check whether the run finished successfully and inspect:

- `artifacts/run-latest/summary.json`

### The report looks too small or too large

Open `report.html` in a normal browser window, not a terminal preview.

## Developer notes

Tests:

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
```

Project layout:

```text
src/social_graph_service/
tests/
scripts/
```
