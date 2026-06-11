## 1. Speed mapping
- [x] 1.1 `effect_speed_setting(effect_type, intensity) -> {E_SLIDER_<type>_Speed: val}`, val = 8..40 by intensity
## 2. Wire
- [x] 2.1 In run.py wash loop (both sites): `ins.extra_settings.update(effect_speed_setting(ins.effect_type, _si))`
## 3. Tests
- [x] 3.1 quiet < loud speed; key is `E_SLIDER_<type>_Speed`; value in range
- [x] 3.2 existing tests pass
- [x] 3.3 Live (gated): place Spirals/Pinwheel with the appended speed key → stored intact + renders faster at higher value
