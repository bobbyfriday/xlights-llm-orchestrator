## 1. Refiner

- [x] 1.1 New `refine_segments_for_instrumental(analysis, max_section_s=32.0, min_piece_s=12.0)` (xlights-core audio/structure.py): no timed lyric lines + any segment > max → greedy beat-snapped cuts at harmonic changes, energy-delta peaks, or time-based last resort; tail-aware cap (no slivers); tiny-tail fold; parent+ordinal labels; no-op otherwise; idempotent
- [x] 1.2 `analyzer.refine_instrumental(analysis, path)`: call the refiner; on True refresh section instrumentation + resave the analysis cache (augment-and-resave, like attach_lyrics)

## 2. Pipeline + panel

- [x] 2.1 `run.py`: after the lyric-attach block, when the analysis still has no timed lines, call `refine_instrumental` best-effort (try/except, log, never block)
- [x] 2.2 `panel.py`: structure analyst prompt sentence — numbered sub-segments (A1/A2) are subdivisions of ONE part; related but EVOLVING looks, keep boundaries

## 3. Tests & verification

- [x] 3.1 Hermetic (tests/test_instrumental_sections.py): harmonic snap split, energy fallback, time-based last resort, no slivers, tiny-tail fold, label ordering/parenting, byte-for-byte pass-through, timed-lyrics disable, all-short no-op, idempotence, Carol worked example, panel render
- [ ] 3.2 Live: Carol of the Bells re-run → coarse 73s/69s "A" segments become ~18s A1–A8 pieces in the analysis cache; brief/plan sections all under ~32s; show generates at the new granularity
