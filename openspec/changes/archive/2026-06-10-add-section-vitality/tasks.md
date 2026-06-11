> **Build result:** RHYTHM_POOL extends thin pulse_groups with the guide rhythm cells (arches/canes/minitrees → call-and-response chase); ACCENT_GROUPS (snowflakes/spinners) fire short hits on downbeats only; ensemble_bed adds a 60%-brightness SEM_BAND_GROUND/SEM_ALL bed under intensity-≥0.7 sections; long (>15s) energetic washes get brightness_ramp(0.7L→L) builds instead of flat levels. Wired at both generate sites. 210 tests pass.

## 1. Beat layer (canes + flakes)
- [x] 1.1 `RHYTHM_POOL=(SEM_ARCHES,SEM_CANES,SEM_MINITREES)`: extend pulse_groups to ≥2 from the pool; sides fallback unchanged
- [x] 1.2 `ACCENT_GROUPS=(SEM_SNOWFLAKES,SEM_SPINNERS)`: downbeats also hit available accent groups (short, accent color)
## 2. Bed + builds
- [x] 2.1 `ensemble_bed(section, intensity, available, idx)`: intensity ≥0.7 → an On bed on SEM_BAND_GROUND else SEM_ALL (skip if already targeted), section palette, ~60% wash brightness; wired at both generate sites
- [x] 2.2 Long (>15s) washes at intensity ≥0.7: `brightness_ramp(0.7×level, level)` instead of the constant slider
## 3. Tests
- [x] 3.1 Single pulse_group + canes available → chase spans arches+canes; downbeat hits include snowflakes; cap respected
- [x] 3.2 Bed added at 0.8 (not at 0.4; not duplicated); long energetic wash carries a Brightness value-curve ramp, short/quiet keeps the slider
- [x] 3.3 Suite passes
