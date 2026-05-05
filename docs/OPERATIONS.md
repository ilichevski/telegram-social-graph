# Operations

This document describes the practical operator workflow for the `Social graph`
repository.

It is intentionally explicit about what is automated, what is local-only, and
what is **not** a production deploy path inside this repo.

## What this repo can do directly

This repo has first-class local entrypoints for:

- local environment setup
- local model download
- local analysis runs
- local report preview
- shell/runtime sanity checks
- README screenshot refresh

## What this repo does **not** define

This repo does **not** contain its own production deployment pipeline.

That matters because the dashboard may be embedded elsewhere, but this
repository itself currently provides:

- analysis
- report generation
- documentation
- local preview

If a generated report is later embedded into another product or site, that
embedding/deployment path belongs to that other repo or system.

## Common entrypoints

### Setup

```bash
./scripts/setup_local.sh
```

Or:

```bash
make setup
```

### Pull local models

```bash
./scripts/pull_models.sh
```

Or:

```bash
make models
```

### Run local analysis

```bash
./scripts/analyze_export.sh
```

Or:

```bash
make analyze
```

### Run local analysis with LLM enrichment

```bash
WITH_LLM=1 ./scripts/analyze_export.sh
```

Or:

```bash
make analyze-llm
```

### Run the API

```bash
make api
```

### Preview a generated report

```bash
./scripts/preview_report.sh
```

Defaults:

- `RUN_DIR=./artifacts/run-latest`
- `PORT=8765`
- `BIND=127.0.0.1`

Example:

```bash
RUN_DIR=./artifacts/run-010 PORT=8770 ./scripts/preview_report.sh
```

### Run a shell/runtime sanity check

```bash
./scripts/shell_sanity_check.sh
```

Or:

```bash
make sanity
```

This checks:

- shell execution
- Python / Node / npm availability
- git remote visibility
- `git push --dry-run origin main`
- a narrow pytest subset

### Refresh README screenshots

```bash
OVERVIEW_SRC=/path/to/overview.png \
DETAIL_SRC=/path/to/detail.png \
./scripts/update_readme_screenshots.sh
```

Or:

```bash
OVERVIEW_SRC=/path/to/overview.png \
DETAIL_SRC=/path/to/detail.png \
make screenshots
```

This updates:

- `docs/images/report-overview.jpg`
- `docs/images/report-detail.jpg`

## Suggested operator workflow

For a normal update cycle:

1. Run `make sanity`
2. Run or refresh analysis
3. Preview the report locally
4. Update documentation if metric semantics changed
5. Refresh README screenshots if the dashboard changed visibly
6. Commit and push to GitHub

## Preview vs production

### Local preview

The preview path in this repo is a local static HTTP server over generated
artifacts.

### Production embedding

If the report is embedded in another app/site, treat that as a separate system.
Do not assume this repository alone defines that deploy path.

## Agent guidance

If you are another agent working in this repo:

- do not claim shell/runtime failure without checking `make sanity`
- do not claim a production deploy path exists unless it is documented in this
  repo or the target embedding repo
- prefer updating local artifacts and docs first
- distinguish clearly between:
  - local analysis path
  - local preview path
  - external embedding/deploy path
