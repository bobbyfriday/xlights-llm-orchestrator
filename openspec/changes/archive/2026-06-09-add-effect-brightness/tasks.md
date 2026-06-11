## 1. Brightness mapping
- [x] 1.1 `wash_brightness(intensity) -> float` in beats.py or a brightness helper: `lerp(50,180,intensity)` on the 0–400 scale
## 2. Code pass
- [x] 2.1 In run.py (both generate sites), set `ins.extra_settings.update(value_curve_setting("Brightness", level, level))` for wash instructions, `level=wash_brightness(section.intensity)`
## 3. Tests & verification
- [x] 3.1 `wash_brightness`: monotonic in intensity; 0→~50, 1→~180
- [x] 3.2 the pass sets a valid constant Brightness value curve on wash instructions; higher intensity → higher Min/Max; existing tests pass
- [x] 3.3 Live (batched): re-gen → quiet sections visibly dimmer, loud sections brighter; dark-palette sections read better
