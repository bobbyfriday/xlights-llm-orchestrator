## Context
`C_SLIDER_Brightness` is 0–100 (dim only); value-curve Brightness is 0–400 (100=normal, can boost). #1 gives `value_curve_setting("Brightness", lo, hi)` + the `extra_settings` append path. The wash instructions are the generator's section effects (the beat/hero accents are added separately and already bright).

## Goals / Non-Goals
**Goals:** energy→wash-brightness, dim quiet + boost loud, works on any look, deterministic. **Non-Goals:** within-section swells; blackouts (#3); focal-point role arbitration (LLM).

## Decisions
### `wash_brightness(intensity) -> float`
Map `intensity` [0,1] → a brightness level on the 0–400 scale: `lerp(MIN_B=50, MAX_B=180, intensity)` (quiet ≈ 50% of normal, loud ≈ 1.8×). Constant value curve (start==end==level) so brightness is a flat multiplier for the section.
### Code pass
At both generate sites in `run.py`, after the wash palette pass: for each wash instruction set `ins.extra_settings.update(value_curve_setting("Brightness", level, level))` where `level = wash_brightness(section.intensity)`. Only the generator's wash effects (not the beat/hero accents). Idempotent (overwrites the Brightness key).
## Risks / Trade-offs
- **Boost realism** — >100 brightens but can clip; cap MAX_B at ~180–200. Tune live.
- **Quiet too dark** — MIN_B floor (50) keeps quiet sections visible, not black (blackouts are #3's deliberate choice).
- **Constant vs ramp** — flat per-section level now; swells later.
## Open Questions
- Exact MIN_B/MAX_B by eye — start 50/180, tune in the combined live re-gen.
