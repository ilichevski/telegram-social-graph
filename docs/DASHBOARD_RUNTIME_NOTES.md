# Dashboard Runtime Notes

This document describes the current `Relationship Snapshot` dashboard behavior
for local previews and production embedding.

## Approved UI Constraints

These constraints are intentional and should not be changed casually:

- Reuse the current production shell for the embedded dashboard.
- Do not introduce new layout blocks, typography systems, or spacing systems
  without explicit review.
- Prefer changing only payload values and narrowly scoped in-place rendering
  logic.
- Validate changes locally before production rollout.

## Social Indices

The dashboard exposes two weekly synthetic indices over the visible 91-day
window:

- `Social Connectedness`
  Built from active ties, reciprocity, bond strength, stability,
  responsiveness, two-way contact share, and network spread.
- `Social Climate`
  Built from warmth, support, depth, playfulness, media intimacy, lower
  formality, and lower tension.

These indices are presented as a compact two-line chart rather than a grid of
weekly cards.

### Display Rules

- X-axis is chronological left-to-right.
- Y-axis is fixed to `0..100`.
- Labels should be visually quieter than the main dashboard typography.
- The graph should not push or collide with the next section.

## My Communication Style

The `My Communication Style` block summarizes outbound behavior across all
private relationships and weekly snapshots inside the current 91-day window.

Current outbound metrics shown:

- warmth
- warmth index
- support
- media intimacy
- playfulness
- engagement
- bond index
- responsiveness
- formality
- depth

## Detail Card

Per-relationship detail cards may include directional metrics such as:

- warmth index
- support
- engagement
- bond index
- responsiveness
- formality
- stability
- depth
- tension
- playfulness

## Local-to-Production Workflow

When iterating on the dashboard:

1. Modify the local current-shell preview.
2. Verify that layout has not drifted.
3. Promote the exact same shell/payload combination to production.
4. Refresh documentation and screenshots after rollout.
