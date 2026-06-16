## Why

`add-downbeat-aligned-section-cuts` (PR #28) made the *instrumental cap* path (`cap_long_segments`)
land section cuts on bar lines. But for a song WITH lyrics, the section boundaries are set by the
*lyric refiner* (`refine_segments_with_lyrics`), which still snapped marker starts, the outro, and
in-fill boundaries to the nearest **beat** via `_snap`. Live on Christmas Canon, the intro therefore
ended at **29.118s — `bar_position 2`** (a weak beat) instead of the **28.677s downbeat** the music
phrases to. The principle is identical (sections start on the downbeat); only this code path was
missed.

## What Changes

- In `refine_segments_with_lyrics`, snap section boundaries with the existing
  `_snap_downbeat` (the helper added in `add-downbeat-aligned-section-cuts`) instead of `_snap`, at
  all three boundary sites: lyric-marker cuts, the outro split, and long-span in-fill boundaries.
- Same tolerance and graceful fallback as the cap path: snap to a bar line within
  `DOWNBEAT_SNAP_TOL_S`, else the nearest beat; no bar positions → unchanged beat snapping.

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `show-orchestration`: the long-section-cut downbeat-alignment requirement is extended so
  lyric-marker-derived section boundaries (not only instrumental cap cuts) also land on bar lines.

## Impact

- `packages/xlights-core/src/xlights_core/audio/structure.py` — three `_snap` → `_snap_downbeat`
  call sites in `refine_segments_with_lyrics` (+ a `downbeats` lookup). No schema/API change.
- Hermetic test: a lyric marker near a bar line snaps to it; one far from any downbeat keeps its
  beat. Verified on the real Christmas Canon analysis: intro 29.118s → 28.677s (a downbeat), and
  every subsequent section start bar-aligned. Lands via PR.
