## Why

Candy cane lane planned 4 sections of 60–90s each — each looked good, but a minute-plus of one look reads as boring (user verdict). Genius lyrics carry the song's real structure as section markers, and for this song has 8 of them (live-verified: Verse 1, Pre-Chorus, Chorus, Post-Chorus, Verse 2, Pre-Chorus, Chorus, Post-Chorus) → ~10 sections including intro/outro. The pipeline already has all the machinery, severed at one link: `fetch_lyrics` passes `remove_section_headers=True` (we strip the markers ourselves), while `align_lyrics` already parses `[marker]` lines and emits timed `sections: [{label, start}]` that nothing consumes.

## What Changes

- **Fetch keeps the markers**: `remove_section_headers=False` in the Genius fetch. The aligner already strips markers from the line stream, so timed lines, narrative, and the Lyrics timing track are unaffected.
- **Deterministic structure refiner**: new `refine_segments_with_lyrics(analysis)` — when ≥2 timed markers exist, rebuild `sa.segments` with boundaries at marker starts snapped to the beat grid, an intro segment before the first marker, an outro/instrumental segment after the last timed line, minimum-length merging, and audio-segment boundaries preserved inside long marker-less (instrumental) spans. Segment labels become the marker labels — ground truth, not guesses.
- **Wired into lyric attach** (analyzer): refine after alignment, augment-and-resave the analysis cache. Lyrics gain a `headers_fetch` flag so caches fetched under the old header-stripping behavior re-fetch once and upgrade; marker-less songs don't re-align every run.
- **Panel prior**: the structure analyst's segment render carries the lyric-derived labels with a prompt note that they are ground truth to keep, not re-derive.
- Downstream for free: the Director plans over ~2× more, shorter, lyric-aligned sections; recurring Chorus/Pre-Chorus labels strengthen the repetition map (escalation); the Section timing track gets real labels.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `music-interpretation`: WHEN timed lyric section markers are available, song structure SHALL derive section boundaries from them — beat-snapped, minimum-length merged, labeled by the markers — with the audio segmentation as the fallback and as the in-fill for instrumental spans.

## Impact

- `xlights-orchestrator/lyrics.py` (fetch flag), `pipeline/run.py` (re-attach condition), `agents/panel.py` (label-aware segment render + prompt note).
- `xlights-core/audio`: new refiner module + `analyzer.attach_lyrics` wiring; `schema.Segment.segment_id` docstring (lyric labels are ground truth when present).
- Caches: existing analyses upgrade once via the `headers_fetch` flag; instrumental songs (mad russian) unaffected.
- Risk surface: marker alignment depends on the first line after each marker aligning — unaligned marker lines drop that marker (graceful, existing behavior).
