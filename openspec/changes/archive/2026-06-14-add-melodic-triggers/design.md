## Context

The trigger layer (`pipeline/triggers.py`) has a `drum_onsets` detector and a `drum_prominent`
section-eligibility, both hardcoded to the drums stem. Per-stem onsets exist for every stem
(Christmas Canon: drums 1067, guitar 754, other 707, piano 425, vocals 373, bass 279). The
realizer already rotates the target pool per event, so "different group per note" is free once a
non-drum stem can be selected. Detectors currently take `(sa, sections)` — they can't see the
trigger's fields.

## Goals / Non-Goals

**Goals:** any stem can drive a trigger (piano first); a piano-note trigger that walks the props;
a holiday red/green/white palette bias. **Non-Goals:** pitch-to-prop mapping (which note → which
prop by pitch); new stems; changing the drum trigger's behavior.

## Decisions

**D1 — Pass the spec to detectors.** Change the detector signature to `(sa, sections, spec)` so a
detector can read `spec.stem`. All four existing detectors get the third arg (ignored where unused).

**D2 — `stem_onsets` detector + `stem` field.** `TriggerSpec.stem` (default `"drums"`).
`stem_onsets` reads that stem's onsets with energy-magnitude (same machinery as `drum_onsets`).
`drum_onsets` becomes `stem_onsets` with the stem forced to drums (one code path, back-compat name).

**D3 — `stem_prominent` eligibility.** Generalize `drum_prominent`: a section qualifies when
`spec.stem`'s share ≥ `DRUM_PROMINENT_SHARE` in that section's instrumentation. `drum_prominent`
stays as the drums-specific spelling; `stem_prominent` uses `spec.stem`.

**D4 — Piano-note trigger (cookbook).** `detector: stem_onsets`, `stem: piano`,
`sections: stem_prominent`, `groups: rhythm` (rotates arches/canes/mini-trees per note → the
melody walks the props), a bright `On` pop (`per_model`, `on_top`, alternating-anchor color),
`select: rotate` so it's a recurring texture, not constant. Density `per_onset` — gated to
piano-prominent sections it stays a melodic accent, not a wash.

**D5 — Holiday palette bias (Director prompt, not code).** Add to the per-section palette guidance:
"If the song is a Christmas/holiday piece, prefer the traditional **red + green + white** primary
palette with 1–2 accent colors (gold, cool white, ice blue), unless the song's mood clearly calls
for something else — and note these read with strong LED contrast (red vs green are hue-distant)."
Judgment stays the LLM's (it knows the song is holiday from the brief); this is a bias, not a rule.

## Risks / Trade-offs

- [Piano notes are dense → busy] → gated to piano-prominent sections + `select: rotate` (a subset) + on_top opaque pops that read individually; tune density/effect in the cookbook after watching.
- [`stem_prominent` finds nothing on some songs] → no trigger fires there (correct, like guitar_solo staying silent) — not an error.
- [Forcing red/green/white everywhere flattens variety] → it's a prompt bias for holiday songs only, with an explicit "unless the mood calls for else"; non-holiday songs untouched.
- [Detector-signature change] → internal; all call sites updated, tests cover.

## Migration Plan

Additive: `stem` defaults to drums, so existing cookbook entries are unchanged; non-holiday songs
see no palette change. Branch `change/add-melodic-triggers`, PR (user merges).

## Open Questions

- Whether a "spread" pool (rotate across ALL main groups, not just the rhythm three) reads better for a melodic line — start with `rhythm`, tune live.
- Pitch-aware mapping (note height → prop) is a richer future idea, deferred.
