## Why

Christmas Canon's intro brief asks for a "still glow + falling snowflakes," and the brief-fidelity fix correctly placed Snowflakes on SEM_SNOWFLAKES and SEM_ALL — but the snowflakes don't read. Grounded in the saved sequence: each snowflake group carries a bare `On` bed on layer 0 with **no brightness setting** (full 100%, opaque, Normal blend) and the Snowflakes effect on layer 1 above it. The Snowflakes effect renders sprites on a transparent background, so the full opaque wash bleeds through every gap and visually dominates — the flakes disappear into a lit yard. The viewer sees the On, not the snow.

This is not a render-order bug (the feature is already on the top layer and SEM_SNOWFLAKES already wins overlaps over SEM_ALL). It's a brightness/opacity bug: an atmospheric, sparse-background feature can only read against a dim or dark base, and the LLM emitted the base at full brightness.

## What Changes

- **Dim beds under atmosphere (code):** when a sparse/transparent-background feature (Snowflakes, Snowstorm, Meteors, Twinkle, Fireworks) coexists with an opaque wash bed (On, Color Wash, Fill) on the same element and overlaps it in time, **cap** the bed at a low "glow" brightness so the feature reads — the brief's "still glow," realized.
- **Cap, don't skip (code):** every section wash already carries an intensity-keyed `wash_brightness`, so there is no "bare" bed to detect — the bug is that that wash level (e.g. 76 on a calm intro) is still bright enough to drown transparent sprites. The pass caps the coexisting bed at the glow level (never brightens; a bed already dimmer is left alone), and skips beds with a blend mode set (a composited add such as a Max-blend beat accent, not an occluding wash). Same-element only — cross-group occlusion already resolves via render order.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `show-orchestration`: when a sparse/atmospheric feature effect coexists with an opaque wash bed on the same element, the bed's brightness SHALL be capped at a glow level so the feature remains visible.

## Impact

- `pipeline/beats.py` (new `dim_beds_under_atmosphere` pass + the atmospheric/bed effect sets and glow level), `pipeline/run.py` (apply the pass over assembled instructions in generate + regen, and on cache-load so pre-existing caches get the fix).
- Back-compat: sections with no atmospheric feature are unchanged; beds already dimmer than the glow are unchanged; idempotent (capping re-runs safely).
