## 1. Downbeat-align the lyric refiner

- [x] 1.1 In `refine_segments_with_lyrics`, compute `downbeats = _downbeats(analysis)` once.
- [x] 1.2 Replace `_snap` with `_snap_downbeat(..., beats, downbeats)` at the three boundary sites: lyric-marker cuts, the outro tail, and long-span in-fill boundaries.

## 2. Tests

- [x] 2.1 A lyric marker within tolerance of a downbeat snaps to it; one farther than tolerance keeps its beat; the intro span ends on the snapped boundary.
- [x] 2.2 Existing lyric/instrumental tests still pass (bar-less grids → graceful fallback).
- [x] 2.3 Full hermetic suite green.

## 3. Live verification

- [x] 3.1 Run `refine_segments_with_lyrics` against the real Christmas Canon analysis and confirm the intro boundary moves from 29.118s to the 28.677s downbeat and subsequent section starts are bar-aligned.

## 4. Land

- [x] 4.1 Open a PR per the project workflow; do not commit to `main` directly.
