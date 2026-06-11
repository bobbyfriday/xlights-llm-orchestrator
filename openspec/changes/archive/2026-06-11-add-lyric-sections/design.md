## Context

Structure flows: audio segmenter → `sa.segments` → structure analyst ("anchor your section times to these") → MusicBrief sections → Director ShowPlan → timing tracks. `align_lyrics` already emits timed `sections: [{label, start}]` (marker label + the aligned start of the first line after it), but the fetch strips markers (`remove_section_headers=True`) so the list is always empty, and nothing consumes it anyway. Candy cane lane: 4 audio segments over 3.5 min; Genius has 8 markers.

## Goals / Non-Goals

**Goals:** lyric-marker-derived section boundaries (more, shorter, lyric-aligned sections) flowing through the existing pipeline untouched; code owns boundaries, labels are LLM priors; graceful for instrumental/marker-less songs; existing caches upgrade once.

**Non-Goals:** subdividing marker-less songs (repeated-line pseudo-sections — future); LRC sources; agent contract changes; aesthetic section-length tuning beyond lyric boundaries.

## Decisions

**D1 — Refine `sa.segments` in place, not a parallel structure.** The panel anchors to segments; the brief, Director, QA, and timing tracks all follow. One enrichment point, zero contract changes. Alternative — feed markers to the analyst as hints only: rejected; boundary placement is deterministic data, not judgment (code-owns-realization).

**D2 — Refiner rules** (`refine_segments_with_lyrics(analysis)`, xlights-core audio):
- Trigger: ≥2 timed markers in `analysis.lyrics["sections"]`; else no-op.
- Boundaries: each marker's start snapped to the nearest beat (`sa.beats`; no beats → unsnapped); intro = 0 → first marker; outro split after the last timed line's end when the remaining tail ≥ 8s.
- Merge: a section < 10s merges into its predecessor (intro < 10s merges forward into the first marker section).
- Instrumental in-fill: inside any marker-to-marker (or marker-to-end) span > 25s that contains no timed lyric lines in its latter part, retain the audio segmentation's boundaries that fall there — the segmenter knows instrumental structure where lyrics are silent.
- Labels: `Segment.segment_id` = the marker label (e.g. "Chorus"); intro/outro/in-fill segments keep algorithmic ids ("intro", "outro", original ids). Docstring updated: lyric labels are ground truth when present.
- Idempotent: boundaries already matching (within one beat) produce identical output.

**D3 — Cache upgrade via a `headers_fetch` flag.** `align_lyrics`'s dict gains `headers_fetch: True` set by `attach_lyrics` after a marker-aware fetch. `run.py` re-attaches when lines exist but the flag is missing (one-time upgrade of pre-change caches, e.g. candy's); marker-less songs get the flag too, so they never re-align again. Alternative — version the whole analysis cache: rejected, re-runs stems/QM unnecessarily.

**D4 — Panel render carries labels.** `_segments(sa)` adds the id/label as today (`id` field) — the structure analyst prompt gains one line: segments with lyric-derived labels (Verse/Chorus/…) are ground truth; label them accordingly and spend judgment on themes/energy, not boundary re-derivation.

**D5 — Repetition map stays LLM-derived** (synthesizer) but now sees two identically-labeled Chorus segments with matching durations — strengthening recurrence detection (escalation) without new code.

## Risks / Trade-offs

- [A marker's first line fails to align → marker dropped → a missing boundary] → graceful (existing `align_lyrics` behavior); the audio in-fill rule keeps long unlabeled spans subdivided; candy aligns 38/44 lines, all 8 markers' lead lines among them.
- [Genius markers wrong/odd granularity ("Refrain", per-line marks)] → min-length merge absorbs over-marking; labels are priors, the analysts still control themes.
- [More sections → more Generator calls + longer placement] → ~10 vs 4 sections ≈ 2.5× generate calls (flash-tier; cheap); per-section weave budgets keep total cells bounded by song length, not section count.
- [Old cache mismatch: refined segments saved, but `song_description`/`creative_brief` orchestrator caches still reflect 4 sections] → those are keyed separately; live verification invalidates them for candy; future songs are consistent from first run.

## Migration Plan

Additive; instrumental songs and marker-less fetches behave exactly as today (flag set, no refinement). Rollback = revert the fetch flag; the refiner no-ops on empty sections.

## Open Questions

- Whether to also split at `repeated`-line cluster boundaries when no markers exist — deferred (noted as future work).
