## Why

When a long instrumental span is subdivided (`cap_long_segments` in `xlights-core/audio/structure.py`),
the cut is chosen by energy-seam strength and then snapped to the nearest **beat** — never to a
**downbeat / bar line**. On Christmas Canon the intro cut landed at **31.777s**, which is *beat 4* of
its bar (`bar_position==4`, a weak pickup), drifting ~3s past the musically-correct phrase boundary
at **28.677s — a true downbeat** (`bar_position==1`) with a coincident harmonic change. Sections that
start off the bar line read as "off" to the ear. The prior "strongest seam, not the latest" fix
stopped cuts pinning to the length cap, but it still has no notion of bar alignment, so a loud
off-beat seam near the cap beats an earlier downbeat phrase boundary.

## What Changes

- Make long-section cut selection **downbeat-aware**: candidate seams snap to the nearest downbeat
  when one is within a small tolerance (using the existing `Beat.bar_position` / `Beat.is_downbeat`,
  a clean 4/4 grid), and selection prefers a bar-aligned phrase boundary over a louder off-beat seam
  near the cap. Energy strength still breaks ties among comparable candidates; the fallback to even
  spacing is unchanged.
- A chosen cut that lands off the bar SHALL be nudged to the nearest in-window downbeat when one
  exists within tolerance, so section boundaries land on bar lines.
- Preserve all current guarantees: no section exceeds the cap, the minimum-piece floor holds, tiny
  tails fold, and the pass stays idempotent and no-op when everything already fits.

## Capabilities

### New Capabilities
<!-- none — refines existing long-section subdivision behavior -->

### Modified Capabilities
- `show-orchestration`: the long-section subdivision requirement ("Long-section cuts land on the
  strongest seam, not the latest") gains downbeat alignment — cuts prefer the bar line, falling back
  to the strongest seam, then to spacing.

## Impact

- `packages/xlights-core/src/xlights_core/audio/structure.py` — a downbeat-aware snap/selection in
  `cap_long_segments` (and the shared `_snap` boundary helper); reads `analysis.beats[].bar_position`.
  No schema change (`Beat.bar_position` / `is_downbeat` already exist).
- Hermetic tests for: cut prefers an in-window downbeat over a louder off-beat near the cap; snap
  tolerance bounds; graceful fallback when bar positions are absent; idempotence/no-op preserved.
- Live-verify on `mp3/christmas canon.mp3`: the intro cut moves from 31.777s to the ~28.7s downbeat.
- No change to lyric-marker-driven sections beyond bar-aligning their boundaries within tolerance.
  Lands via PR.
