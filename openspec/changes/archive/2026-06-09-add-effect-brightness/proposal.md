## Why
The guide: *"brightness should track the song's intensity curve,"* *"dim everything to ~20% during a solo,"* *"deep blues are dimmer on pixels — bump brightness."* We place fixed-brightness looks, so every section reads at the same level and the dark-palette wash looks flat (what you saw on screen). This adds an energy-driven brightness lever using the value curves from #1.

## What Changes
- An **energy→brightness** code pass: the section **wash** effects get a brightness keyed to `section.intensity` — quiet sections dimmer, loud sections **boosted** (so the energetic parts pop and dark palettes don't read flat).
- Implemented as a constant value-curve brightness (0–400 scale, 100=normal) attached via `extra_settings` (from #1), so it works on any look.
- Beats/hero stay bright (their contrast is handled by the brightened palette); the wash carries the dynamics.

**Non-goals:** within-section swells/ramps (constant per-section level for now); per-prop-role dimming beyond wash vs accent (the focal-point arbitration is the guide-injected LLM's job); blackouts (#3).

## Capabilities
### Modified Capabilities
- `show-orchestration`: section wash brightness scales with the section's energy (dim quiet, boost loud), so the show has dynamic range instead of one flat level.

## Impact
- **`xlights-orchestrator`**: a brightness pass in `run.py` setting `extra_settings` brightness on wash instructions at both generate sites; reuses #1's `value_curve_setting`.
- **Builds on** #1 (value curves) + normalized `section.intensity`. Directly targets the dim/flat wash.
