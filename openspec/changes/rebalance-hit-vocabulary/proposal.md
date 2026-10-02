# rebalance-hit-vocabulary

## Why

Our beat punctuation is flat flashes; the community's has geometry. The 2026-07-07 corpus comparison (memory: `corpus-alignment-2026-07`) measured our recent runs at **On 21.7% + Strobe 7.5% + Shimmer 6.0% + Twinkle 5.3% + Lightning 1.9% ≈ 42%** of all placed effects, versus the 17-show community corpus at ≈ 7.5% for those same types. The community's hit of choice is **Shockwave at 12.6%** (their #2 effect overall; ours 3.6%) — a shaped radial pop, median 600 ms, placed on mini trees, stars, snowflakes, spinners, and whole-house groups. Strobe is essentially absent from community shows (**3 placements in 27,099 effects**; we placed 290 in 3 runs). The root causes are concentrated:

1. `place_beat_accents` uses ONE effect type for all five of its sublayers (meter backbone, backbeat, sparkle, hero, bass) — the Director's `accent_effect`, defaulting to `On`. Every accent in a section is the same flat pulse.
2. Generator-chosen Strobe/Shimmer washes get expanded into per-bar pulses by `normalize_durations`, multiplying single bad choices into dozens of placements.

## What Changes

- **Role-differentiated accent effects** in `place_beat_accents`: the sparkle layer (accent props: snowflakes/spinners) and the backbeat answer become radial **Shockwave** hits — reusing the hand-authored radiating-Shockwave settings that already exist in `pipeline/triggers.py` (built to read on accent props, matching community practice). The meter backbone and bass keep `On` (fast per-beat pulses on linear props are correct there — community On lives in the same role). The hero keeps the melodic stem's effect.
- **Strobe demoted to climax-only**: outside peak sections, a generator-placed Strobe is substituted with Shockwave; within peaks the existing 1 s hard cap stands. Shimmer gains a per-section instance cap (its 2-bar duration cap already exists in `clamp_hard_caps`).
- **QA advisory**: warn when a section's flat-flash share (On + Strobe + Shimmer + Twinkle + Lightning) exceeds 0.30 of its instructions in energetic sections — encoding the corpus band so the refine loop, not memory of this analysis, holds the line.
- Generator/Director guide extracts gain one sentence of corpus grounding (community hits with Shockwave, almost never Strobe).
- Golden regen once (accent effect types change).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `show-orchestration`: the deterministic beat-accent layer differentiates effect by rhythmic role (shaped radial hits vs flat pulses); Strobe is reserved for peak sections.
- `show-refinement`: new advisory finding for flat-flash-dominated energetic sections.

## Impact

- `packages/xlights-orchestrator/src/xlights_orchestrator/pipeline/beats.py` — `place_beat_accents` (`_mk` / per-sublayer effect choice), `_accent_look`.
- `packages/xlights-orchestrator/src/xlights_orchestrator/pipeline/triggers.py` — export the radiating-Shockwave settings for reuse (no behavior change there).
- `packages/xlights-orchestrator/src/xlights_orchestrator/qa/rules.py` — Strobe demotion + flat-flash advisory.
- `packages/xlights-orchestrator/src/xlights_orchestrator/pipeline/tuning.py` — new dials (flat-flash advisory threshold, Shimmer instance cap).
- `packages/xlights-orchestrator/src/xlights_orchestrator/agents/prompts/` or `agents/guide_extracts.py` — one-line corpus grounding.
- Tests: beats accent tests, qa rules tests, golden regen. No API/schema changes.
