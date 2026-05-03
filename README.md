# Social Graph Service

Local-first service for building a social graph from Telegram exports on macOS. The MVP keeps parsing and scoring on-device and can optionally call a local `Ollama` model for emotional scoring.

## Privacy

- Telegram exports are processed locally.
- No Telegram data is bundled in this repository.
- Optional LLM enrichment is designed for a local `Ollama` runtime, not a cloud API.
- Generated analysis artifacts should stay outside version control.

## MVP scope

- Import Telegram Desktop JSON exports.
- Normalize private and group messages into a local graph model.
- Detect media-rich messages such as photos, voice notes, videos, GIFs, and stickers.
- Score reciprocity, responsiveness, initiation balance, and heuristic warmth.
- Handle private groups exported as `my own messages only` with self-activity summaries instead of fake reciprocity.
- Optionally enrich edges with local LLM judgments through `Ollama`.
- Export results as JSON and GraphML.
- Expose both a CLI and a small HTTP API.

## Quick start

1. Create a virtualenv and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

2. Run an analysis over a Telegram export folder:

```bash
social-graph analyze ./telegram-export --output ./artifacts/run-001
```

3. Optionally enable local LLM enrichment:

```bash
OLLAMA_MODEL=qwen3:8b social-graph analyze ./telegram-export --output ./artifacts/run-002 --with-llm
```

4. Start the HTTP API:

```bash
uvicorn social_graph_service.api:app --reload
```

## Expected inputs

The importer currently targets Telegram Desktop machine-readable JSON exports. It supports:

- a single exported chat whose JSON root contains `messages`
- an export directory with multiple `result.json` or `*.json` files

## Output files

- `graph.json`: nodes, edges, and metrics
- `graph.graphml`: graph for Gephi, yEd, or NetworkX tooling
- `summary.json`: run metadata and aggregate counts
- `report.html`: local human-readable report with ranked relationships

## Generate a report again

```bash
social-graph report ./artifacts/run-001/graph.json --summary-json ./artifacts/run-001/summary.json --output ./artifacts/run-001/report.html
```
