## 1. Implementation

- [x] 1.1 In `pipeline/beats.py`, add `ATMOSPHERIC`, `BED_EFFECTS`, `GLOW_BRIGHTNESS`, and `dim_beds_under_atmosphere(instructions)` — cap a bed's brightness at the glow level when an atmospheric feature coexists on the same target overlapping in time; never brighten; skip beds with a blend mode set.
- [x] 1.2 In `pipeline/run.py`, call `dim_beds_under_atmosphere` in the generate path (over the full instruction list), the regen path (per section), and the cache-load branch.

## 2. Tests (hermetic)

- [x] 2.1 A bright On wash coexisting with Snowflakes on the same target is capped to the glow level.
- [x] 2.2 A bed already dimmer than the glow is left unchanged; a blend-mode accent is left unchanged.
- [x] 2.3 A bed with no atmospheric feature is left unchanged.
- [x] 2.4 A bed on a DIFFERENT target than the feature is left unchanged (same-element only); a value-curve brightness is replaced with the static glow.
- [x] 2.5 Full suite passes.

## 3. Verify + land

- [x] 3.1 Live: re-emit the snowflake intro and confirm the flakes read against a dim glow (no full wash bleed-through).
- [x] 3.2 Archive, commit, push branch, open PR (user merges).
