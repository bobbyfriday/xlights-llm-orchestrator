## 1. Implementation

- [x] 1.1 `audio/structure.py`: extract `cap_long_segments(analysis, max_section_s, min_piece_s)` (the seam-cutting loop, no lyrics gate); `refine_segments_for_instrumental` delegates to it (keeps its lyrics gate as the no-lyrics entry).
- [x] 1.2 `audio/analyzer.py`: call `cap_long_segments` after `refine_segments_with_lyrics` (subdivide long lyric-free spans), before the instrumentation refresh + cache save.

## 2. Tests (hermetic)

- [x] 2.1 `cap_long_segments` subdivides a long segment EVEN with lyrics present (the bug), all pieces ≤ cap, short sections untouched.
- [x] 2.2 No-op when all sections fit; idempotent on its own output.
- [x] 2.3 Existing lyric + instrumental refiner tests still pass (refiner behavior unchanged).

## 3. Verify + land

- [x] 3.1 Real-data check: Christmas Canon's 101s intro → four ≤32s sections cut at harmonic seams (longest section 100s → 31s).
- [x] 3.2 Archive, commit, push, open PR (user merges).
