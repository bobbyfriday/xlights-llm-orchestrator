## 1. Table rows + signed spin curves

- [x] 1.1 In `packages/xlights-orchestrator/src/xlights_orchestrator/pipeline/effect_meta.py`, add `directions` to the existing `Spirals` and `Ripple` rows exactly as specified in design.md D1 (`E_SLIDER_Spirals_Rotation` ±20, `E_SLIDER_Ripple_Rotation` ±20; keep all other fields of those rows unchanged; add a row comment noting corpus provenance: 84 Spirals looks carry the key, 16 negative).
- [x] 1.2 In `packages/xlights-core/src/xlights_core/knowledge/value_curves.py`, add keyword-only `sign: int = 1` to `motion_curve_setting`; for `kind == "spin"` use `end = (hi if sign >= 0 else lo) * (0.3 + 0.7 * level)`; sweep kind ignores sign. All existing callers unchanged.
- [x] 1.3 Extend `tests/test_effect_meta.py` anchor tests: `DIRECTION_KNOBS["Spirals"]["rtl"] == ("E_SLIDER_Spirals_Rotation", "-20")` and the Ripple pair; run `uv run pytest tests/test_effect_meta.py`.
- [x] 1.4 Add a value-curves unit test: `motion_curve_setting("Spirals", "rotation", 0.5, sign=-1)` produces a ramp whose end is negative (parse the `P2`/max out of the returned curve string the same way existing tests do — check `tests/` for the current pattern first).

## 2. Auto counter-rotation pass

- [x] 2.1 In `packages/xlights-orchestrator/src/xlights_orchestrator/pipeline/weave.py`, define `ROTATIONAL_EFFECTS` derived from `EFFECT_META` (ltr+rtl pair present, not chase_family) per design.md D3 — do NOT hand-list the set.
- [x] 2.2 In `_valid_recipes` (weave.py, after the existing chase counter-phase block ~line 264): same-effect-type pairs in `ROTATIONAL_EFFECTS` with overlapping groups and both directions empty → first gets `"ltr"`, second `"rtl"`. Never override a non-empty direction.
- [x] 2.3 In `expand_composite` (weave.py ~line 454): same-type rotational layers with empty directions → layer 0 `"ltr"`, later layer `"rtl"`; thread `sign=-1` into `motion_curve_setting` for odd layer indexes when the layer has a spin-kind motion curve.
- [x] 2.4 Add `counter_rotate_stacks(instrs)` to weave.py per design.md D3 (group by target+type for `ROTATIONAL_EFFECTS`, sort by `(layer, start_ms)`, flip the direction key on the 2nd/4th/… time-overlapping instruction via `extra_settings`, skip instructions already carrying that key). Call it in `realize_section` in `pipeline/generate.py` immediately before `clamp_hard_caps(kept, ...)`.
- [x] 2.5 Unit tests (follow the existing weave test style — find them with `grep -rl expand_weave tests/`): (a) two LLM Spirals recipes on the same groups come out ltr/rtl; (b) `counter_rotate_stacks` flips the upper of two overlapping Spirals on one target and is idempotent; (c) an explicit direction survives both passes; (d) non-overlapping same-type instructions are untouched.

## 3. Curated composites

- [x] 3.1 Replace the `kaleidoscope` and `bloom` entries in `CURATED_COMPOSITES` (weave.py ~line 432) exactly per design.md D4; update the block comments (do not claim Morph counter-motion anywhere).
- [x] 3.2 Update/extend the composite unit test: expanding `kaleidoscope` yields two Spirals instructions with opposite-sign `E_SLIDER_Spirals_Rotation` and `T_CHOICE_LayerMethod: Max` on the upper layer; every `bloom` layer's `direction_setting` resolves non-empty.

## 4. Golden regen + verification

- [x] 4.1 Run the full suite (`uv run pytest`); then regenerate the golden once: `XLO_REGEN_GOLDEN=1 uv run pytest tests/test_golden_pipeline.py`. Inspect the golden diff: ONLY expected changes are new `E_SLIDER_Spirals_Rotation` / `E_SLIDER_Ripple_Rotation` keys in extra_settings and the peak-composite effect swap (Morph→Spirals). Anything else in the diff = investigate before committing.
- [ ] 4.2 Commit golden regen as its own commit; open a PR to `main` (branch `feat/counter-rotation`; never commit directly to main). PR description must note the intentional visual-behavior change: `alternate`/`bounce` on Spirals/Ripple cells now flips rotation per bar (previously a silent no-op).
