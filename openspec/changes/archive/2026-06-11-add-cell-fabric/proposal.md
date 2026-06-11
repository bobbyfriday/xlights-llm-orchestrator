## Why

The 130,229-effect community audit (docs/effects-layering-analysis.md) quantified why our shows read as "static / not really alive": community sequences are ~58% continuous-MOTION effects placed as 0.3–0.9s beat-quantized cells at ~1,300 effects/min (woven from ~49 distinct designs/min, ≈12× reuse each), while ours are ~83% punctuation/static (On 22%, Twinkle 23%) at ~270/min over long washes. Community curves motion params (Rotation 30%), sets blend modes (Brightness 36%, masks 16%) and Wipe transitions; we set none of those. The Generator prompt also still carries the disproven claim "blend modes are not settable" (T_CHOICE_LayerMethod round-trips via addEffect — re-verified).

## What Changes

- **Cell recipes (LLM judgment):** the Generator designs ~3–6 `CellRecipe`s per section — effect, role (carrier/texture/accent/bed), target groups, cell length in beats, alternation pattern, blend, motion curve, transition. New `SectionWeave` on `SectionEffects` (additive; `None` = current behavior).
- **The weaver (code realization):** a new deterministic `pipeline/weave.py` expands recipes into beat-snapped `EffectInstruction` cells across the section — alternating across groups, palettes via existing palette realization, blends via `T_CHOICE_LayerMethod`, motion value curves (Rotation/Twist/Radius/Position) via the existing value-curve serializer, Wipe in/out transitions. Density is bounded and scales with section intensity; layer budget capped.
- **Deterministic fallback weave** when the LLM omits/invalidates the weave (carrier = SingleStrand chase on the rhythm pool) — the fabric never depends on perfect LLM output.
- **Beat-layer rebalance:** when a carrier recipe covers the rhythm pool, `place_beat_accents` drops its every-beat On chase (keeps downbeat sparkle + hero onsets) — the carrier IS the beat now; On/Twinkle demote to accents/beds.
- **Generator prompt revision:** ask for the weave, document recipe semantics, correct the stale "blend modes are not settable" line, and remove the duplicated dead scene-note block in `render_input`.
- **Duration taxonomy v0.3:** catalog §2.1 "sustained" → "cell-able" (default 1–2 bar cells; explicit long-bed exceptions); `normalize_durations` chops non-bed cell-able placements like the existing HIT chop.
- **QA advisory:** rules QA surfaces motion-effect share per section (advisory finding, not an objective gate) so fabric regressions are visible to the Judge.

## Capabilities

### New Capabilities

(none — this extends show generation, not a new capability)

### Modified Capabilities

- `show-orchestration`: sections SHALL be realized as beat-quantized cells expanded deterministically from per-section cell recipes; recipes (effects, groups, alternation, cell length, blend, motion curves, transitions) SHALL be LLM-directable with a deterministic fallback; cell density SHALL be bounded and scale with section intensity; motion-effect share SHALL be surfaced to QA as an advisory.

## Impact

- `xlights-orchestrator`: `show_plan.py` (CellRecipe/SectionWeave, additive), new `pipeline/weave.py`, `pipeline/run.py` (weave expansion in generate + regen), `pipeline/beats.py` (carrier-aware beat accents, `normalize_durations` cell-able class), `agents/generator.py` + `agents/prompts/generator.md` (weave ask, blend-mode correction, dead-block removal), `qa/rules.py` (motion-share advisory).
- `xlights-core`: `knowledge/value_curves.py` (motion-param curve synthesis keyed by effect type — exact `E_VALUECURVE_*` keys verified against the mined corpus before freezing).
- Docs: `xlights-effects-catalog.md` §2.1 v0.3.
- Back-compat: `weave=None` reproduces today's instruction stream bit-for-bit; old caches keep working (fallback weave only on fresh generation).
- Live risk surface: more addEffect calls per run (density target makes placement take longer); bounded by the density cap.
