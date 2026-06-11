## Context
Corpus speed keys follow `E_SLIDER_<Effect>_Speed` (Pinwheel/Wave/Plasma/Butterfly/Spirals/Meteors/…), values ~0–50 (median 15). Our looks omit speed (default), so we APPEND it via `extra_settings`. Appending a key an effect doesn't use is ignored (safe).
## Goals / Non-Goals
**Goals:** energy→speed on wash effects; corpus key convention; safe append. **Non-Goals:** direction (6b); BPM lock; per-effect range calibration.
## Decisions
### `effect_speed_setting(effect_type, intensity) -> dict`
`key = f"E_SLIDER_{effect_type}_Speed"`; `val = round(SPEED_MIN(8) + (SPEED_MAX(40)-SPEED_MIN)*intensity)`; return `{key: str(val)}`. Beat accents are `On` (no speed) — only the wash effects get it.
### Code pass
At both generate sites, in the wash loop: `ins.extra_settings.update(effect_speed_setting(ins.effect_type, _si))` (uses the same `_si` effective intensity as brightness/coverage).
## Risks / Trade-offs
- **Key convention mismatch** — `E_SLIDER_{type}_Speed` may not match every effect's exact key (e.g. SingleStrand→FX_Speed); a mismatch is a harmless no-op (xLights ignores unknown keys). Live-verify a couple of effects actually speed up.
- **Range** — 8–40 covers most; outliers (some go to 800) ignored. Tune live.
## Open Questions
- Whether to fold a global tempo factor on top of energy — energy alone gives per-section variation; add tempo later if wanted.
