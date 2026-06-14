## Why

Christmas Canon's intro was a single **100-second section** — far too long to direct (one look, one palette, one set of effects across a sixth of the song). Grounded in the code: the two structure refiners are mutually exclusive per song — `refine_segments_for_instrumental` (which caps long segments at 32s by cutting at musical seams) **bails entirely if the song has any timed lyrics** (structure.py gate). The lyric refiner only cuts at lyric markers, so a stretch with no lyrics — a long instrumental intro, solo, or bridge — never gets subdivided. Canon has lyrics, so its 101s lyric-free intro stayed whole.

So a song with lyrics + any long instrumental span gets a giant, un-directable section. This blocks meaningful per-section editing (the editable brief) and forces one blanket look over a long, evolving passage.

## What Changes

- **Universal long-section cap (code):** extract the seam-cutting logic into `cap_long_segments(analysis, max_section_s=32, min_piece_s=12)` with **no lyrics gate** — it subdivides any segment over the cap at harmonic-change points (then energy-delta peaks, then beat-snapped time), labeling pieces parent-id + ordinal (`Intro` → `Intro1..Intro4`). Idempotent; no-op when everything already fits.
- **Run it after both refiners (code):** the analyzer calls `cap_long_segments` after the lyric refiner (so lyric songs' long instrumental spans get subdivided), and `refine_segments_for_instrumental` now delegates to it (the no-lyrics path is unchanged).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `show-orchestration`: no song section SHALL exceed the long-section cap — long instrumental spans are subdivided at musical seams regardless of whether the song has lyrics.

## Impact

- `audio/structure.py` (`cap_long_segments`; `refine_segments_for_instrumental` delegates), `audio/analyzer.py` (cap after the lyric refiner). Back-compat: instrumental songs unchanged (same cap, same path); lyric songs gain subdivision of their long lyric-free spans. Verified on Canon: the 101s intro → four ≤32s sections cut at harmonic seams.
