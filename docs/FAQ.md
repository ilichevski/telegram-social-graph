# FAQ

## Does this upload my Telegram data anywhere?

Not by default.

The service is designed to run locally on your machine. If you enable `--with-llm`, it is intended to talk to a local `Ollama` instance, not a cloud API.

## What Telegram export format do I need?

Use `Telegram Desktop` and choose `Machine-readable JSON`.

## Can I use this without Ollama?

Yes.

The graph, snapshots, weekly history, reciprocity, response speed, and most scoring logic work without any local model.

## What does Ollama add?

It adds local emotional scoring for:

- `you -> them warmth`
- `them -> you warmth`
- `mutuality`
- `tension`

## Do I need to export media files too?

No.

Text-only exports are enough to get started. Media-aware logic exists, but the first useful run does not require full media export.

## Where do I put my export?

Default location:

```text
./data/telegram-export
```

Or run with:

```bash
EXPORT_PATH="/absolute/path/to/export" ./scripts/analyze_export.sh
```

## What if I want a historical view?

The default helper script already builds weekly snapshots over the last `91` days.

You can override dates with:

```bash
AS_OF_DATE=2026-05-02 START_DATE=2026-01-31 ./scripts/analyze_export.sh
```

## What should I open after the run?

Usually:

```text
artifacts/run-latest/report.html
```

## Can I publish my output files?

Only if you are comfortable exposing your own relationship data.

For most people, the answer should be no.
