## 1. Fetch + refiner

- [x] 1.1 `lyrics.py`: fetch with `remove_section_headers=False`
- [x] 1.2 New `refine_segments_with_lyrics(analysis)` (xlights-core audio): ≥2 timed markers → beat-snapped boundaries, intro/outro segments, <10s merge, >25s instrumental-span in-fill from audio segments, marker labels as segment ids; no-op otherwise; idempotent
- [x] 1.3 `analyzer.attach_lyrics`: call the refiner after alignment; set `headers_fetch: true` on the lyrics dict; resave cache

## 2. Pipeline + panel

- [x] 2.1 `run.py`: re-attach lyrics when lines exist but `headers_fetch` missing (one-time cache upgrade)
- [x] 2.2 `panel.py`: structure analyst prompt note — lyric-labeled segments are ground truth (label, don't re-derive)

## 3. Tests & verification

- [x] 3.1 Hermetic: refiner (snap/merge/intro/outro/in-fill/no-op/idempotent), flag plumbing + re-attach condition, panel render labels
- [x] 3.2 Live: candy cane re-run → ~10 labeled segments in the analysis; brief plans Verse/Pre-Chorus/Chorus sections each well under a minute; pipeline generates + refines at the new granularity, 0 systematic skips; Section timing track labeled
