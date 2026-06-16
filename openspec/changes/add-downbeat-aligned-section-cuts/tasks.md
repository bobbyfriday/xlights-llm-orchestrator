## 1. Downbeat-aware snapping in structure.py

- [x] 1.1 Add a helper to collect downbeat times from `analysis.beats` (using `Beat.is_downbeat` / `bar_position == 1`); empty when no bar info.
- [x] 1.2 Add `_snap_downbeat(t, beats, downbeats, tol_s)`: nearest downbeat within `tol_s`, else `_snap` (nearest beat). Define `DOWNBEAT_SNAP_TOL_S` constant (seed ≈ 0.6s / one beat).
- [x] 1.3 In `cap_long_segments`, build candidate seams with `_snap_downbeat` (so off-beat seams collapse to their bar line) and keep the existing `[lo, cap]` window filter (a seam whose bar line falls past the cap is naturally dropped).
- [x] 1.4 After the cut is chosen (including the no-seam spacing fallback), nudge it to the nearest downbeat that is `> prev + min_piece` and `<= cap` when within `tol_s`; otherwise keep the beat-snapped cut.
- [x] 1.5 Confirm the min-piece floor, cap, tiny-tail fold, and idempotence/no-op paths are preserved.

## 2. Hermetic tests

- [x] 2.1 Cut prefers an in-window downbeat over a louder off-beat seam near the cap (the Christmas-Canon-shaped case: downbeat at ~28.7 vs off-beat energy seam at ~31.8 whose bar line is past the cap).
- [x] 2.2 `_snap_downbeat`: snaps to a downbeat within tolerance; leaves a seam >tolerance from any downbeat on its beat; equals `_snap` when `downbeats` is empty.
- [x] 2.3 No-bar-positions analysis → identical output to pre-change (graceful fallback).
- [x] 2.4 Snapping never yields a sub-min-piece or over-cap section; tiny-tail fold still applies.
- [x] 2.5 Idempotence + no-op-when-all-fit preserved.
- [x] 2.6 Run the full hermetic suite (`pytest`); regenerate the golden snapshot if instrumental boundaries shifted, and confirm the diff is only boundary bar-alignment.

## 3. Live verification

- [x] 3.1 Recompute Christmas Canon analysis sections (delete/`--no-cache` the analysis) and confirm the intro cut moves from 31.777s to the ~28.7s downbeat, and the other intro boundaries land on bar lines.
- [x] 3.2 Tune `DOWNBEAT_SNAP_TOL_S` (and add the earliest-within-strength-band rule if needed) so the intro resolves to ~28.7s without distorting other songs' cuts.

## 4. Land

- [ ] 4.1 Open a PR per the project workflow; do not commit to `main` directly.
