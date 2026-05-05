# How To Read The Report

The HTML report is meant to answer two questions:

1. Who matters in the network right now?
2. How is the relationship changing over time?

## Main board

Each bubble is one relationship.

- left half: how warm `you -> them` looks
- right half: how warm `them -> you` looks
- greener: warmer
- redder: colder
- arrow badge: communication volume trend

## Date selector

The top timeline changes the snapshot date.

Important: a snapshot is not “messages from that day only”. It is a relationship estimate as of that date, based on a trailing evidence window.

## Sorting modes

- `Volume`: most active relationships first
- `Warmth`: warmest relationships first
- `Change`: strongest recent movement first

## Detail panel

When you click a person, the right panel shows:

- `Messages 90d`
- `Reciprocity`
- `You -> them`
- `Them -> you`
- `Volume delta`
- `Warmth index`

## Interpreting the metrics

### Reciprocity

`0.0 -> 1.0`

- `1.0`: very balanced exchange
- lower values: more one-sided communication

### You -> them / Them -> you

`0.0 -> 1.0`

This is the current warmth estimate in each direction.

### Volume delta

- `7d vs 28d`: recent message rate vs the broader recent baseline
- `28d vs 91d`: medium window vs the longer baseline

### Warmth index

- `100`: same daily warmth as the baseline
- above `100`: warmer than the baseline
- below `100`: colder than the baseline

## Synthetic network indices

The dashboard may also show two weekly network-level synthetic indices:

- `Social Connectedness Index`
- `Social Climate Index`

These are intended for trend reading across the visible time window, not diagnosis.

Full scoring details:

- [SCORING_AND_INDICES.md](./SCORING_AND_INDICES.md)

## Media-aware signals

Some relationship metrics are influenced by more than text.

Examples:

- `playfulness`
  can rise from GIFs, stickers, and expressive media habits
- `media intimacy`
  can rise from photos, voice messages, audio, and richer media exchange
- `warmth` and `bond`
  can improve indirectly when richer media exchange suggests a closer tie

If local voice/audio transcription is enabled, spoken content can also affect
support, warmth, and depth.

## What to trust most

Best signals:

- large recent volume
- decent reciprocity
- stable activity across weeks
- similar directional warmth from both sides

Be more careful with:

- very low-volume chats
- highly one-sided chats
- short bursts with very little history
