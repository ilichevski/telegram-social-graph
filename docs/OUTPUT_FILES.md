# Output Files

Each run writes a directory like:

```text
artifacts/run-latest/
```

## Files

### `report.html`

Human-readable interactive report.

### `summary.json`

Top-level run metadata plus the main payloads used by the report.

### `graph.json`

Graph nodes, edges, and graph summary.

### `graph.graphml`

Graph export for tools like:

- Gephi
- yEd
- NetworkX pipelines

### `snapshot_now.json`

The current snapshot payload for the selected `as_of_date`.

### `weekly_snapshots.json`

Network-level weekly history across the chosen date range.

### `relationship_timeseries.json`

Per-person weekly timeseries.

### `person_reports.json`

Per-person summary cards derived from the timeseries.

### `network_timeseries.json`

Compact network-level time series.

## Minimal structure examples

### `summary.json`

```json
{
  "analysis_config": {
    "as_of_date": "2026-05-02",
    "start_date": "2026-01-31",
    "end_date": "2026-05-02",
    "cadence_days": 7,
    "window_days": 90,
    "short_window_days": 30
  },
  "weekly_snapshots": [],
  "relationship_timeseries": [],
  "person_reports": []
}
```

### `weekly_snapshots.json`

```json
[
  {
    "as_of_date": "2026-05-02",
    "active_relationships": 91,
    "mean_closeness": 0.2704,
    "mean_mutual_warmth": 0.4984
  }
]
```

### `relationship_timeseries.json`

```json
[
  {
    "peer_id": "user123",
    "peer_label": "Alice",
    "snapshots": [
      {
        "as_of_date": "2026-05-02",
        "messages_total_90d": 120,
        "warmth_out": 0.61,
        "warmth_in": 0.58,
        "reciprocity": 0.84
      }
    ]
  }
]
```
