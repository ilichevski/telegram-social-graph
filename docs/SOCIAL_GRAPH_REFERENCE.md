# Social Graph Reference

This document is the authoritative technical reference for the local Telegram
social graph project.

It is written for:

- future agents working on the codebase
- engineers extending the pipeline
- operators who need to understand what the dashboard means

The goal is to explain:

- where the data comes from
- what is computed locally
- what optional model layers exist
- how the main relationship metrics are derived
- how the two weekly social indices are built

This document describes the current system behavior as of the latest local
implementation.

## 1. System Goal

The project builds a **local-only social graph** from a Telegram Desktop export.

It estimates:

- current relationship state
- weekly relationship snapshots
- trend over a rolling 91-day window
- directional warmth and bond
- a small number of synthetic network-level social indices

The system is designed to avoid sending raw personal data to third-party cloud
services.

## 2. Data Sources

### Primary input

The main input is a `Telegram Desktop` export directory, typically containing:

- `result.json`
- media subdirectories for photos, voice, audio, video, stickers, GIFs, files

### Current supported scope

The current project focuses on:

- private chats
- weekly snapshots over a rolling 91-day window
- optional media-aware analysis

Groups are intentionally excluded from the current core social graph view when
they are not present or when the analysis is explicitly scoped to private chats.

### Media currently supported

The pipeline can extract and use signals from:

- text
- photos
- voice messages
- audio files
- GIFs
- stickers
- files

Video support exists at the metadata layer, but the current improvement path has
focused primarily on text, audio, and expressive media.

### How media is used

The project does not treat all media equally.

- `photos`
  are treated mainly as expressive closeness / intimacy signals
- `voice messages`
  are treated as higher-bandwidth social signals; when ASR is enabled, their
  transcript also participates in lexical and LLM scoring
- `audio files`
  are handled similarly to voice where usable
- `GIFs`
  contribute primarily to expressive/playful signaling
- `stickers`
  contribute primarily to playfulness and lightweight tone cues
- `files`
  count as media activity, but usually weaker than photos/voice for social
  interpretation

## 3. Privacy Model

### Local-first principle

The project is designed so that personal Telegram data remains local.

### What stays local

These steps run locally:

- Telegram export parsing
- message normalization
- temporal analysis
- heuristic scoring
- media signal extraction
- local dashboard generation

### Optional local model layers

Two local model layers may be used:

- local LLM via `Ollama`
- local voice transcription for `.ogg` / audio messages

### Important nuance

If a local ASR model has not been cached yet, its weights may be downloaded once
from the public model source. This does **not** send the user's Telegram data to
that source. After the model is available locally, inference stays local.

## 4. High-Level Pipeline

The system can be understood as seven layers.

### 4.1 Ingest

The Telegram export is parsed into normalized chat/message objects.

### 4.2 Normalize

Messages are converted into a common structure:

- direction
- timestamp
- chat identity
- sender identity
- text content
- media metadata

### 4.3 Temporal slicing

The relationship state is evaluated on weekly anchors across a 91-day window.

Typical cadence:

- one snapshot every 7 days

### 4.4 Heuristic scoring

The project computes non-LLM behavioral and lexical metrics from text, timing,
and media patterns.

### 4.5 Optional enrichment

If enabled:

- local LLM scores relational/emotional dimensions
- local ASR transcribes voice/audio into text that then participates in the
  same heuristic and LLM layers

### 4.6 Aggregation

The system builds:

- per-relationship snapshot metrics
- weekly time series
- network-level synthetic indices

### 4.7 Presentation

Results are embedded into the dashboard:

- relationship bubbles
- detail cards
- weekly social indices chart
- personal communication style summary

## 5. Time Model

### Snapshot cadence

The system uses weekly snapshots.

For the current implementation, the visible window is usually:

- `91 days`

### Snapshot semantics

Each snapshot estimates relationship state **as of that date**, using recent
evidence windows rather than messages from only one day.

### Common windows

The system often uses:

- `7d`
- `28d`
- `91d`

These are used for:

- volume change
- warmth change
- bond change
- dynamic comparisons

## 6. Directionality

Many metrics are directional and are computed separately for:

- `you -> them`
- `them -> you`

This is important because many relationships are asymmetric.

Examples:

- one person may be warmer
- one person may initiate more
- one person may be less formal
- one person may respond faster

The dashboard preserves this directional split in the detailed relationship
card.

## 7. Main Relationship Metrics

This section explains the major relationship metrics used in the dashboard.

All numeric scores are generally normalized into `0..1` unless explicitly
rendered as `0..100`.

## 7.1 Warmth

`Warmth` is a directional emotional tone estimate.

It is built from:

- lexical warmth signals
- friendly / affectionate phrasing
- supportive language
- low hostility
- low distance
- optional LLM enrichment

This metric tries to answer:

- how warm does this person sound toward the other side?

## 7.2 Support

`Support` is a directional care / reassurance / help signal.

It is built from:

- supportive lexical markers
- reassurance phrasing
- care/help style language
- local LLM support judgments

Support is intentionally separate from warmth. A relationship can be warm but
not especially supportive, or supportive without sounding highly affectionate.

## 7.3 Formality

`Formality` is a directional distance / formality signal.

Higher means:

- more formal
- more distant
- less casual

Lower means:

- more relaxed
- less formal
- often closer in tone

This is why low formality is often treated as a positive contributor to broader
social climate.

## 7.4 Tension

`Tension` is a pair-level friction signal.

Higher means:

- more conflict
- more irritation
- more relational friction

Lower means:

- less visible tension

Low tension often improves the broader network climate score.

## 7.5 Engagement

`Engagement` tries to capture who carries the exchange.

It includes signals such as:

- who initiates
- who sustains the exchange
- who returns after silence
- who contributes more active conversational energy

## 7.6 Responsiveness

`Responsiveness` captures reply speed and reply consistency.

It uses:

- time-to-reply behavior
- consistency of response behavior

This is directional.

## 7.7 Stability

`Stability` measures how consistently active the relationship is across recent
weeks.

It is higher when:

- the relationship appears repeatedly active
- the connection is not just a short spike

## 7.8 Depth

`Depth` is a proxy for more substantial or personal communication.

It is derived from:

- longer messages
- more substantive text
- more personal-feeling exchanges
- optional model interpretation

It is not the same as intimacy, but it is a practical proxy in the current
system.

## 7.9 Playfulness

`Playfulness` is a lightweight expressive or playful communication signal.

It was introduced after media-aware analysis was added.

It can incorporate:

- GIF usage
- sticker usage
- expressive media behavior
- playful tone signals

It is useful because some relationships are lively and playful even when they
are not extremely deep or formal.

### Current main inputs to playfulness

The current playfulness layer is especially influenced by:

- GIF usage
- sticker usage
- expressive media behavior
- lighter relational tone when detectable

## 7.10 Media Intimacy

`Media intimacy` measures closeness implied by richer media exchange.

Examples:

- photos
- voice messages
- expressive media usage

This is still a proxy metric, but it provides useful signal beyond plain text.

### Current main inputs to media intimacy

The current media intimacy layer is especially influenced by:

- photos
- voice messages
- audio usage
- richer expressive media exchange patterns

## 7.11 Warmth Index

`Warmth Index` is an integrated directional emotional score.

It is broader than raw warmth and may incorporate:

- warmth
- support
- low tension contribution
- low formality contribution
- depth contribution
- limited responsiveness contribution

This index is used in the dashboard as a more integrated emotional measure.

## 7.12 Bond Index

`Bond Index` is an integrated directional relationship-strength score.

It is broader than warmth and is designed to capture:

- mutuality
- continuity
- responsiveness
- engagement
- depth
- strength of the ongoing bond

This index is used separately from warmth so that the dashboard can distinguish:

- emotionally warm ties
- structurally strong ties

## 8. Evidence Gating and Confidence

One of the main problems in social-graph estimation is over-trusting tiny or
weak relationships.

The project therefore uses **evidence gating** and **confidence**.

### Why this exists

Without gating:

- tiny chats can look falsely “top warmth”
- rare lexical hits can create extreme support/formality values
- weak evidence can dominate rankings

### What evidence gating does

Evidence gating shrinks unstable signals toward a safer center when:

- message count is too low
- active evidence is thin
- reciprocity is weak
- continuity is poor

### What confidence means

`confidence_score` reflects how trustworthy a relationship estimate is.

It depends on things like:

- amount of evidence
- continuity
- reciprocity
- response coverage

### Display consequence

Sort orders and color intensity should rely on confidence/evidence-adjusted
values rather than raw extreme values from fragile relationships.

## 9. LLM Enrichment

### Purpose

The local LLM is used as a judge, not as the whole system.

The graph is not built solely from the model.

### What the LLM does

It can enrich:

- warmth
- support
- formality
- depth
- engagement
- confidence-related interpretation

### Current approach

The system merges heuristic and LLM layers rather than replacing heuristics.

### Zero-judgment handling

All-zero or empty LLM judgments are treated as invalid/no-judgment and should
not overwrite the heuristic state.

This avoids flattening relationships due to weak or failed model output.

## 10. Voice / Audio Transcription

When enabled, voice/audio content can be locally transcribed.

This allows voice messages to affect:

- lexical analysis
- warmth/support detection
- LLM interpretation

Without transcription, voice/audio still contributes through:

- duration
- frequency
- reciprocity of usage
- richer-media behavioral patterns

This is more informative than using only duration or volume metadata.

## 11. Social Indices

The dashboard currently exposes two weekly network-level indices.

These are designed to summarize the broader social state without creating too
many top-line numbers.

## 11.1 Social Connectedness

`Social Connectedness` estimates how socially connected the user is to the
private-chat network on a given week.

It is built from:

- active ties
- reciprocity
- mean bond strength
- stability
- responsiveness
- two-way contact share
- network spread

Interpretation:

- higher means more socially connected / more structurally active network state
- lower means narrower or weaker recent network connection

## 11.2 Social Climate

`Social Climate` estimates the emotional climate of the user’s network on a
given week.

It is built from:

- warmth
- support
- depth
- playfulness
- media intimacy
- lower formality
- lower tension

Interpretation:

- higher means warmer / more supportive / more open network tone
- lower means colder / more formal / less supportive or less emotionally alive

## 11.3 Calibration

These indices are not intended to be clinical measures.

They are:

- synthetic
- weekly
- calibrated to be readable within the current rolling window

The current dashboard presents them as a line chart with:

- chronological left-to-right direction
- fixed `0..100` axis

## 12. Dashboard Semantics

### Bubble board

The main board visualizes current relationship state.

The bubble design uses:

- directional halves
- warmth and bond rings

### Detail card

Selecting a relationship opens a directional card with metrics such as:

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

### Social indices chart

This is a compact weekly two-line chart that summarizes the 91-day period.

### My Communication Style

This summarizes the user’s average outbound behavior over the visible private
relationship set and weekly snapshots.

## 13. Known Limits

The system is useful, but it is still an inferential layer and has limits.

### Important limitations

- chat exports do not capture the whole of a human relationship
- media proxies are not the same as true psychological intimacy
- lexical support does not equal actual support in real life
- some weak relationships can still be noisy even after gating
- synthetic indices are summaries, not diagnoses

## 14. Practical Reading Guidance

When interpreting results:

- use directional metrics, not just pair averages
- treat confidence seriously
- compare weeks against nearby weeks, not only against absolute numbers
- treat indices as hypothesis generators, not truth

## 15. Files to Know

Core logic is primarily implemented in:

- `src/social_graph_service/telegram_export.py`
- `src/social_graph_service/media_signals.py`
- `src/social_graph_service/voice_asr.py`
- `src/social_graph_service/ollama.py`
- `src/social_graph_service/temporal_analysis.py`
- `src/social_graph_service/pipeline.py`
- `src/social_graph_service/reporting.py`

Useful supporting docs:

- `docs/SCORING_AND_INDICES.md`
- `docs/HOW_TO_READ_REPORT.md`
- `docs/DASHBOARD_RUNTIME_NOTES.md`

## 16. Recommended Update Discipline

When changing the dashboard or metric behavior:

1. keep local preview and production shell aligned
2. prefer payload/logic changes over layout churn
3. document new metrics immediately
4. update screenshots after visible dashboard changes
5. treat this file as the top-level source of truth
