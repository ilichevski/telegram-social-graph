# Documentation Map

This file is the quick navigation entrypoint for humans and agents.

## Primary references

- `docs/SOCIAL_GRAPH_REFERENCE.md`
  The main technical reference for the project:
  data sources, privacy model, pipeline, metrics, indices, and limitations.

- `docs/SCORING_AND_INDICES.md`
  Practical scoring notes and metric semantics.

- `docs/HOW_TO_READ_REPORT.md`
  Operator-facing guide to understanding the generated dashboard/report.

- `docs/DASHBOARD_RUNTIME_NOTES.md`
  Current dashboard shell/runtime rules and approved UI constraints.

- `docs/OPERATIONS.md`
  Practical operator workflow, sanity checks, preview path, screenshot refresh,
  and the distinction between local analysis and external deployment.

## What to read for specific tasks

### If you need to understand where the data comes from

Start with:

- `docs/SOCIAL_GRAPH_REFERENCE.md`

Sections to prioritize:

- Data Sources
- Privacy Model
- High-Level Pipeline
- Time Model

### If you need to change relationship scoring

Start with:

- `docs/SOCIAL_GRAPH_REFERENCE.md`
- `docs/SCORING_AND_INDICES.md`

Then inspect:

- `src/social_graph_service/temporal_analysis.py`
- `src/social_graph_service/pipeline.py`
- `src/social_graph_service/ollama.py`

### If you need to change dashboard semantics

Start with:

- `docs/DASHBOARD_RUNTIME_NOTES.md`
- `docs/HOW_TO_READ_REPORT.md`

Then inspect:

- `src/social_graph_service/reporting.py`

### If you need to understand weekly synthetic indices

Start with:

- `docs/SOCIAL_GRAPH_REFERENCE.md`

Focus on:

- Social Connectedness
- Social Climate
- Dashboard Semantics

## Canonical operational rules

These are the current high-level rules the project assumes:

- local-first data handling
- optional local-only LLM enrichment
- optional local audio transcription
- 91-day rolling window
- weekly snapshots
- evidence gating for weak ties
- confidence-aware display and ranking
- minimal shell/layout churn in the embedded dashboard

## When updating the system

When the scoring model or dashboard behavior changes:

1. update `SOCIAL_GRAPH_REFERENCE.md`
2. update `SCORING_AND_INDICES.md` if metric semantics changed
3. update `HOW_TO_READ_REPORT.md` if user-visible interpretation changed
4. update `DASHBOARD_RUNTIME_NOTES.md` if shell/runtime constraints changed
5. update `OPERATIONS.md` if operator workflow changed
6. refresh screenshots after visible dashboard changes
