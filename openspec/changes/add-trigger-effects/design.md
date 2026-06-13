## Context

`features.py` already maps stem events to effects (guitar→Lightning, drums→Shockwave) but only for instrument *entrances*, hardcoded. The data to do much more is present: per-stem onsets (drums 764, guitar 968 on DJ), per-stem `energy_arc` (RMS over time → onset magnitude), `section_instrumentation` shares (guitar-dominant windows = solos), and timed lyric lines (with per-word timing already computed in `lyrics_align._transcribe`, then discarded). The user wants these as a *curated, hand-editable, sparingly-used* library.

## Goals / Non-Goals

**Goals:** a markdown-defined trigger registry; curated semantic effects placed sparingly (section rotation + per-trigger density); magnitude- and render-scope-driven small/large; color+direction variety per event; word-precise color; entrance-feature folded in. **Non-Goals:** LLM-chosen triggers (curated, code-owned v1); simultaneous same-instant per-prop variety (needs odd/even subgroups — deferred); phonemes/faces.

## Decisions

**D1 — Cookbook is declarative; detectors are code.** `xlights-trigger-cookbook.md` declares each trigger as a labeled block of fields: `detector` (names a code function), `effect`/`look`, `render` (`per_model`|`whole_house`), `rarity` (`per_onset`|`per_section`|`per_show`|`per_event`), `sections` (eligibility: `drum_prominent`|`has_guitar_solo`|`any`|`peak`), `select` (`rotate`|`all`), `color` (`anchor_alternate`|`lyric`|`fixed:<name>`), `direction` (`out`|`in`|`alternate`|`none`), `magnitude` (`top:<pct>`|`any`|`>=:<v>`), `density` (cells per section when per-onset). Parsed best-effort (`agents/guide.py` loader); a malformed/unknown-detector entry is skipped with a log, never fatal — same resilience as the guides. New trigger VARIANTS reusing a detector = pure markdown edits; new detector LOGIC = a small code addition + a cookbook entry.

**D2 — Detector library** (`triggers.py`), each `analysis → [TriggerEvent{time_ms, magnitude 0–1, group?}]`:
- `guitar_solo`: spans where the guitar stem dominates (share/energy) and vocals are absent; magnitude = dominance. One event per solo span (rarity `per_event`).
- `drum_onsets`: drum stem onsets, magnitude = `energy_at(drums.energy_arc, t)` percentile-normalized; filtered by the trigger's `magnitude` (e.g. `any` for periodic small, `top:5` for the big-moment single hit).
- big moments reuse `drum_onsets` gated to top-magnitude hits (the wallops) — NOT a separate "one per section" detector. Magnitude `top:<pct>` makes them naturally rare and length-proportional (a long, busy section yields more top-percentile hits), and a per-section density cap (~10) bounds the max. So a section gets a handful of whole-house shockwaves scaled to how many genuinely big hits it has — song-dependent, not a fixed count.
- `lyric_color`: lyric words matching the color lexicon → event at the word's time, `group` = prominent props, color carried from the word.

**D3 — Render scope is the small/large lever** (not radius): `per_model` → each prop gets a contained, prop-scaled effect; `whole_house` → `Per Preview` on `SEM_ALL`/`SEM_HOUSE`, one gesture radiating across the layout. Maps to existing `render_style` values; Shockwave already falls back to Per Preview.

**D4 — Sparsity is two-scale.** *Section selection*: a deterministic rotation (`select: rotate`) distributes triggers across eligible sections so consecutive sections differ and only a subset feature each accent (e.g. drum-shockwaves on every other drum-prominent section). *Within-section density*: per-trigger — periodic drum shockwaves fire on **drum onsets** (not the beat grid) every hit in a chosen section; the big-moment fires once.

**D5 — Per-event variety, time-distributed.** For the periodic per-model drum shockwaves: successive onsets rotate across the rhythm-pool groups AND alternate contrast-anchor color AND alternate out/in (Shockwave radius: out = start<end, in = start>end — exact values live-round-tripped at build). This is variety across onsets in time; simultaneous same-instant per-prop variety is the deferred odd/even-subgroup follow-up.

**D6 — Word timing: persist what we already compute.** `lyrics_align` keeps each matched line's word list `[{word,start,end}]` (it already locates the word window). `analysis.lyrics["lines"][i]["words"]` becomes available; `lyric_color` reads it. No WhisperX, no new dep. Phoneme-level (faces) is a separate future concern with its own install hurdle.

**D7 — Trigger layer placement.** Runs in `run.py` after the feature layer, before finalize; tags `section_index`; goes through `clamp_layer_budget` + `clamp_hard_caps` with everything else (Strobe/Shimmer caps still apply; layer ceiling respected). Triggers ADD over the fabric; they don't replace it.

## Risks / Trade-offs

- [Overdone — triggers everywhere] → the whole point of D4; section rotation + per-trigger density caps it; the motion/coverage QA still observes the result.
- [Cookbook parse fragility] → best-effort like guides; unknown detector / bad field → skip that trigger, log, never crash.
- [Shockwave out/in via radius may not read as expected] → live round-trip the radius-direction values during the build (project discipline) before freezing the cookbook defaults.
- [Big-moment detection picks dull hits] → `top:<pct>` keeps only the strongest drum onsets globally; a quiet section with no top-percentile hit gets none (better than a forced flat one); the per-section cap bounds busy sections.
- [Word-timestamp persistence bloats the cache] → words are small; only matched lines carry them; acceptable.

## Migration Plan

Additive; absent cookbook → no triggers (back-compat). Branch `change/add-trigger-effects`, PR (user merges). Word-persistence re-aligns once via the existing cache-upgrade path.

## Open Questions

- Big-moment density: magnitude `top:<pct>` + per-section cap (~10) — the right percentile/cap is song-dependent; tune live in the cookbook.
- Whether to expose trigger enable/emphasis to the Director later (v2 LLM gating) — out of scope now.
