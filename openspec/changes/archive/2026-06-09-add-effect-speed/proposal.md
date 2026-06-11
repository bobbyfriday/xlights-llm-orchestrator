## Why
The guide: *"effect speed should track the song's intensity curve,"* and "same speed everywhere" is a named mistake. Our looks use default speed (the speed key isn't even in the mined settings), so every section moves at the same rate. This drives effect speed from section energy.

## What Changes
- An **energy→speed** code pass: each section wash effect gets `E_SLIDER_<EffectType>_Speed` set by `section.intensity` (slower in quiet sections, faster in loud ones), appended via `extra_settings`. The speed key follows the corpus convention `E_SLIDER_<Effect>_Speed`; appending a key an effect doesn't use is harmless (ignored).

**Non-goals:** direction-follows-pitch (6b, separate — needs a pitch extractor); BPM-exact locking (coarse energy map); per-effect speed-range calibration (one sane range).

## Capabilities
### Modified Capabilities
- `show-orchestration`: section effect speed scales with the section's energy, so motion is slower in quiet sections and faster in loud ones (no longer one flat speed).

## Impact
- **`xlights-orchestrator`**: an `effect_speed_setting` helper + a code pass in `run.py` on wash instructions. Reuses the `extra_settings` append path.
- **Builds on** normalized `section.intensity` and the corpus `E_SLIDER_<Effect>_Speed` convention.
