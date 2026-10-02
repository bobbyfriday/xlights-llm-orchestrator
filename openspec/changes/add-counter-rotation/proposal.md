# add-counter-rotation

## Why

Every rotational effect we place spins the same direction, always. The 2026-07-07 corpus comparison (memory: `corpus-alignment-2026-07`; 17 community .xsq = 27,099 effects vs 3 recent run caches = 3,852 instructions) measured community same-type stacked pairs running in **opposite directions**: SingleStrand 63%, Spirals 47%, Pinwheel 30%. Community Spirals placements split 690 clockwise / 334 counter-clockwise / 638 value-curve-animated; our pipeline has produced **zero** counter-clockwise spirals, ever. Three mechanical gaps cause this:

1. `Spirals` has no `directions` row in `EFFECT_META` — `direction_setting()` returns `{}` silently for it, so any requested direction no-ops and the mined look's frozen (almost always positive) `E_SLIDER_Spirals_Rotation` wins.
2. `motion_curve_setting()` spin curves ramp `0 → +hi` only — never negative.
3. Two of the four curated peak composites claim counter-motion that no-ops: `kaleidoscope` (Morph ltr + Morph rtl — Morph has no direction knob at all, verified zero direction/rotation keys in the mined corpus) and `bloom` (Spirals ltr + Fan rtl — Spirals unmapped, Fan only maps center_out/center_in). Both render as two identical effects blended Max.

## What Changes

- `EFFECT_META` gains corpus-verified `directions` rows for `Spirals` and `Ripple` (signed rotation sliders), enabling `direction_setting()`/the weave/`expand_composite` to actually steer them.
- `direction_setting()` learns nothing new — the existing `(key, value)` mechanism already works once rows exist (extra_settings override frozen look values at emit, verified in `_merge_extra_settings`).
- Spin motion curves (`motion_curve_setting`) accept a negative direction: a new `spin_sign` parameter (or equivalent) so rotation ramps can run `0 → -hi`.
- **Auto counter-rotation pass**: when the SAME rotational effect is stacked on the SAME target with overlapping time (weave recipes, composite layers, or generator instructions), the upper layer automatically receives the opposite spin — the rotational twin of the existing chase counter-phase rule in `_valid_recipes`. Seeded/deterministic (no RNG), so goldens are stable and recurring sections rhyme.
- `CURATED_COMPOSITES` redefined so every claimed counter-motion is real: `kaleidoscope` becomes a counter-rotating **Spirals** pair (Morph cannot be steered by knob — verified), `bloom` keeps Spirals+Fan but with directions that map (`ltr`/`rtl` on Spirals now real; Fan uses `center_out`/`center_in`).
- Golden pipeline snapshot regenerated once (expected churn: direction keys appear in extra_settings; composite effect types change at peaks).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `show-orchestration`: new requirement — rotational effects support signed direction, and same-type rotational stacks on one target counter-rotate deterministically; curated composites must produce real (not no-op) counter-motion.

## Impact

- `packages/xlights-orchestrator/src/xlights_orchestrator/pipeline/effect_meta.py` — 2 new `directions` rows (Spirals, Ripple).
- `packages/xlights-orchestrator/src/xlights_orchestrator/pipeline/weave.py` — counter-rotation pairing in `_valid_recipes`/`expand_composite`; `CURATED_COMPOSITES` redefinition.
- `packages/xlights-core/src/xlights_core/knowledge/value_curves.py` — signed spin ramps.
- `packages/xlights-orchestrator/src/xlights_orchestrator/pipeline/generate.py` — hook for the generator-instruction counter-rotation pass (small).
- Tests: `tests/test_effect_meta.py` (frozen-literal table check), weave/composite unit tests, golden regen.
- No API, schema, or xLights-client changes. No new dependencies.
