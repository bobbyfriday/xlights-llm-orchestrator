## Why
At the 2:00 driving beat the show reads boring, and the diagnosis generalizes: (1) the brief picked ONE pulse group, so all 51 beat accents blink on the arches with no chase; (2) the bed lights ~21/79 props in a 0.9 section; (3) the wash runs 36 seconds unchanged; and (4) **the canes and snowflakes are never lit in the entire show** (0 effects) despite being purpose-built rhythm cells and accent props per the guide.

## What Changes
- **Rhythm pool (canes join the beat):** the beat chase is guaranteed ≥2 groups — the brief's pulse_groups extended from the guide's rhythm cells (`SEM_ARCHES`, `SEM_CANES`, `SEM_MINITREES`) so arches/canes trade the beat (call-and-response); spatial sides remain the fallback.
- **Snowflake sparkle on the bar:** downbeats additionally fire short accent hits on `SEM_SNOWFLAKES`/`SEM_SPINNERS` (when available) — accents that fire on hits and stay dark otherwise, per the guide.
- **High-energy ensemble bed:** sections at intensity ≥0.7 get a low-brightness `SEM_BAND_GROUND` (else `SEM_ALL`) bed wash under the features, so the yard never reads quarter-lit at a peak.
- **Wash builds, not idles:** long (>15s) high-energy washes get a **brightness ramp** (the value curves from #1) instead of a flat level — sections build instead of sitting static.

**Non-goals:** Director prompt changes (deterministic guarantees beat prompts); palette/segmentation variation over time (later); per-prop choreography.

## Capabilities
### Modified Capabilities
- `show-orchestration`: the beat layer always chases across ≥2 rhythm-cell groups (canes included), downbeats sparkle the accent props, high-energy sections carry an ensemble bed, and long energetic washes ramp — so driving sections read as motion across the yard, not one blinking group over a static background.
