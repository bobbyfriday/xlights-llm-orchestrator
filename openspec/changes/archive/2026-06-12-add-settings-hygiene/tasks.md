## 1. Speed + stale keys

- [x] 1.1 `beats.py`: `SPEED_KEYS` per-effect (key, lo, hi, fmt) from the corpus survey; `effect_speed_setting` emits the real key (slider int / textctrl 1-decimal) or nothing
- [x] 1.2 `editing.py`: `DROP_KEYS` strip in the look assembly (seed: `E_CHECKBOX_Chase_3dFade1`)

## 2. Grid size

- [x] 2.1 `layout_semantics.patch_rgbeffects`: SEM_ groups get `GridSize="1200"` (idempotent; user groups untouched)

## 3. Tests & verification

- [x] 3.1 Hermetic: speed map per effect (real key + range; speedless → {}); DROP_KEYS stripped from assembled settings; GridSize written only on SEM_ groups, idempotent
- [x] 3.2 Live: place SingleStrand/Color Wash/Twinkle cells → no ApplySetting errors in the xLights log; rgbeffects patched (warnings gone after next restart); speed values visible in readback
- [x] 3.3 Commit on the stacked branch (rides the add-led-readability PR train)
