## 1. Implementation
- [x] 1.1 `audio/tuning.py`: new core-side tuning surface; move the lyric/section/seam show-feel
  constants out of `structure.py` (names unchanged, re-exported via the import).
- [x] 1.2 `audio/structure.py` `cap_long_segments`: soft target + ±flex window (ceiling =
  target + flex); rank by real-energy-break (relative `SEAM_MIN_STRENGTH_FRAC` bar) then
  nearest-the-target; weak/harmonic-only → nearest seam; no seam → beat near the target.

## 2. Tests
- [x] 2.1 Dense harmonic noise + one energy break → cut at the break near the target, not a closer
  weak harmonic.
- [x] 2.2 Flat window cuts at the target (25s), not the ceiling edge.
- [x] 2.3 Existing harmonic-only / energy-fallback / worked-example tests updated for the new
  target/ceiling; full suite green (minus the env-gated `[audio]`/`ffmpeg` modules).

## 3. Verify + land
- [ ] 3.1 Real audio (Canon): cuts land on the energy re-entries, reachable past the old 32s cap
  (pending an environment with the `[audio]` extra).
- [x] 3.2 Commit + push to the branch (user merges).
