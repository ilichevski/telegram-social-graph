# Scoring And Indices

This document explains the main relationship metrics, how they are blended, and how the synthetic network indices are computed.

It is written for both humans and coding agents working on this project.

## Design principles

The system intentionally separates:

- relationship strength
- emotional warmth
- behavioral responsiveness
- media-based expressiveness
- network-level synthetic summaries

The goal is not to produce one magical “truth score”, but to keep the components inspectable and recomposable.

## Relationship-level metrics

Each private relationship snapshot contains directional and pair-level fields.

### Directional metrics

Directional fields are computed separately for:

- `self -> peer`
- `peer -> self`

Common fields include:

- `warmth_score`
- `support_score`
- `formality_score`
- `tension_score`
- `depth_score`
- `engagement_signal`
- `responsiveness_score`
- `media_intimacy_score`
- `media_playfulness_score`

These are all normalized into approximately `0.0 .. 1.0`.

### Pair-level metrics

Pair-level fields combine the directional signals:

- `reciprocity`
- `mutual_warmth`
- `mutual_support`
- `mutual_formality`
- `mutual_tension`
- `depth_score`
- `stability_score`
- `warmth_index`
- `bond_index`
- `integrated_color_score`
- `confidence_score`

## Evidence gating

Weak relationships can create misleadingly extreme scores if they have:

- very few messages
- very little recent activity
- highly one-sided evidence

To reduce this, the system uses:

### Directional signal confidence

Directional signals are shrunk using:

- `count_90d`
- `count_28d`
- `chars_90d`
- `meaningful_messages_90d`
- `media_messages_90d`

This produces a `signal_confidence` used to shrink unstable directional scores toward a safer floor.

### Pair evidence gate

Pair-level `warmth_index`, `bond_index`, `mutual_support`, and `mutual_formality` are multiplied by a pair evidence gate based on:

- total messages
- `confidence_score`
- `continuity_score`

This reduces false “top” relationships from tiny or stale chats.

## LLM enrichment

Optional local LLM enrichment can update:

- directional warmth
- support
- formality
- depth
- engagement
- mutuality
- tension
- confidence

Important:

- zero-judgment payloads are ignored
- the heuristic layer remains the fallback
- LLM outputs are blended, not blindly trusted

The intended runtime is local `Ollama`, not a cloud API.

## Warmth and bond

### Warmth index

`warmth_index` is an integrated emotional measure derived from:

- warmth
- support
- lower tension
- lower formality
- depth
- responsiveness
- media intimacy
- playfulness

It is still a relationship-level metric, not a full network metric.

### Bond index

`bond_index` is more structural than warmth. It reflects:

- relationship strength
- reciprocity
- continuity
- engagement
- responsiveness
- depth
- media intimacy

In practice:

- `warmth_index` answers “how emotionally warm is this tie?”
- `bond_index` answers “how strong and alive is this tie?”

## Dashboard bars

In detail cards:

- most bars are direct: larger value = fuller bar
- some bars are inverted:
  - `formality`
  - `tension`

For inverted bars:

- lower numeric value is treated as better / softer / less friction-heavy
- so the bar fill is computed from `1 - value`

This is currently consistent mathematically, but can feel counterintuitive visually.

## Weekly synthetic indices

The dashboard can also compute two network-level weekly indices over the visible window.

These are synthetic summaries meant for trend inspection, not diagnosis.

### 1. Social Connectedness Index

This measures how strongly the person is embedded in a living network.

Components:

- active ties
- reciprocity
- mean bond
- stability
- responsiveness
- live two-way share
- network spread
- a small short-term volume momentum component

Interpretation:

- higher = more socially connected
- lower = narrower, less reciprocal, or less active network

### 2. Social Climate Index

This measures the emotional climate of the network.

Components:

- warmth
- support
- depth
- playfulness
- media intimacy
- lower formality
- lower tension
- a small short-term warmth momentum component

Interpretation:

- higher = warmer, safer, more expressive network climate
- lower = colder, flatter, drier, or more formal network climate

## Current calibration strategy

For the two weekly synthetic indices, the current preferred calibration is hybrid:

- mostly absolute values
- some relative-within-window normalization
- a small momentum term

This avoids two bad extremes:

- overly flat indices that barely move
- overly sensitive indices that overreact to tiny weekly differences

## What these indices are for

These indices are best used for:

- weekly trend inspection
- comparing one period against another
- generating cautious hypotheses about changes in social life

They are not designed for:

- diagnosis
- personality labeling
- definitive psychological claims

Use wording like:

- “social connectedness appears lower this week”
- “network climate appears warmer than earlier in the window”
- “support and responsiveness rose while breadth fell”

not:

- “the person is isolated”
- “the person is depressed”

## If you modify the formulas

When changing scoring logic:

1. preserve local-only privacy assumptions
2. note whether a metric is absolute, relative, or hybrid
3. document whether a bar is direct or inverted
4. re-check low-evidence relationships
5. update dashboard docs if user-visible interpretation changes
