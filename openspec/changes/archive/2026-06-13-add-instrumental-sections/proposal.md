## Why

Instrumental songs (Carol of the Bells) get no lyric markers, so they fall back to the coarse audio segmenter: 73s/69s sections. Each section becomes one look, and anything past ~35s of one look reads as boring (user verdict — the same verdict that drove add-lyric-sections, whose refiner can't help here: no lyrics, nothing to refine from). The analysis already carries the music's own seams — `harmonic_changes` (tonal-change points) and `energy_arc` (RMS over time) — and a beat grid to snap to; nothing consumes them for structure.

## What Changes

- **Deterministic instrumental refiner**: new `refine_segments_for_instrumental(analysis, max_section_s=32.0, min_piece_s=12.0)` in `xlights_core.audio.structure` — the lyric refiner's complement (runs only when no timed lyric lines exist; never both). Each audio segment longer than the max is cut greedily at the strongest candidate seam inside `[prev + min, prev + max]`: harmonic changes preferred, energy-delta peaks as fallback, the beat nearest the window cap as last resort. Every cut beat-snapped; no piece exceeds the max; tiny tails fold into the previous piece. Pieces are labeled parent id + ordinal ("A" → "A1","A2",...).
- **Wired into the analyzer**: `AudioAnalyzer.refine_instrumental(analysis, path)` calls the refiner and on change re-saves the analysis cache (augment-and-resave, like `attach_lyrics`).
- **Pipeline call site**: `run.py` invokes it right after the lyric-attach block, only when the analysis still has no timed lines — best-effort try/except, never blocks the run.
- **Panel prior**: the structure analyst's prompt gains one sentence — numbered sub-segments (A1/A2) are beat-snapped subdivisions of ONE musical part; give them related but EVOLVING looks, don't re-derive boundaries.
- Downstream for free: the Director plans ~2-4× more, shorter sections for instrumentals; the Section timing track inherits the finer labels.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `music-interpretation`: WHEN a song has no timed lyric lines, audio segments longer than ~32s SHALL be subdivided at beat-snapped musical seams (harmonic changes, then energy deltas, then time) into pieces of roughly 12–32s labeled under their parent segment.

## Impact

- `xlights-core/audio`: `structure.py` (new refiner), `analyzer.py` (`refine_instrumental` augment-and-resave).
- `xlights-orchestrator`: `pipeline/run.py` (call site after lyric attach), `agents/panel.py` (one prompt sentence).
- Caches: instrumental analyses upgrade in place on next run (idempotent — already-fine caches no-op); lyric songs untouched.
- Risk surface: harmonic-change density varies by song — the greedy window plus the time-based last resort bounds every piece regardless.
