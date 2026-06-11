## 1. Synthesizer
- [x] 1.1 `knowledge/value_curves.py` `value_curve(param, lo, hi, shape="ramp_up") -> str` → corpus Ramp format; `brightness_ramp(lo_pct,hi_pct)` helper (0–400 scale)
- [x] 1.2 Output round-trips: `value_curve_is_active` TRUE, `classify_value_curve=="parametric"`, `parse_value_curve` recovers Min/Max/Type

## 2. Attach path
- [x] 2.1 `EffectInstruction.extra_settings: dict[str,str] = {}` (additive)
- [x] 2.2 `place_preset(..., extra_settings=None)`: append `,KEY=VALUE` after assemble (values have `|` not `,`); emitter passes `ins.extra_settings or None`

## 3. Tests & verification
- [x] 3.1 `value_curve`/`brightness_ramp` produce valid active parametric curves (round-trip asserts)
- [x] 3.2 `place_preset` with `extra_settings` appends the curve to the settings passed to add_effect (fake client records settings); without → unchanged; existing preset tests pass
- [x] 3.3 Live (gated, batched): place an effect with a brightness ramp → xLights accepts it AND it visibly ramps in the right direction (flip RV if reversed)
