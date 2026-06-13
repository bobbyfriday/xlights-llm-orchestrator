## Context

Lyric songs get fine sections from Genius markers via `refine_segments_with_lyrics`; instrumentals keep the coarse audio segmentation (Carol: `N1 0–0.2`, `A 0.2–73`, `A 73–141.6`, `N3 141.6–165.7`). Structure flows segments → structure analyst → MusicBrief → Director → timing tracks, so refining `sa.segments` in place is the one enrichment point (same as D1 of add-lyric-sections). The analysis already measures the needed seams: `harmonic_changes: list[float]`, `energy_arc: list[EnergyPoint]`, `beats`.

## Goals / Non-Goals

**Goals:** no instrumental section over ~32s; cuts on the music's own seams, beat-snapped; deterministic and idempotent; graceful degradation (no beats → unsnapped; no seams → time-based); zero contract changes; existing caches upgrade in place.

**Non-Goals:** touching lyric-refined songs (complement, never both); semantic labels for the pieces (A1/A2 are ordinals — the analysts assign meaning); re-running the audio segmenter; live verification in this change.

## Decisions

**D1 — Complement trigger.** Run only when `analysis.lyrics` is None or has no timed `lines` — exactly the lyric refiner's complement, gated again at the run.py call site (after lyric attach has had its chance). No-op (False) when every segment already fits `max_section_s`, which also makes a second pass over refined output a no-op (idempotence).

**D2 — Candidate seams, tiered.** `harmonic_changes` when present (tonal seams, all equal strength), else energy-delta peaks (`|rms[i] - rms[i-1]|` at the later point's time), else nothing. Candidates are beat-snapped up front so a chosen cut stays inside its window after snapping. A fallback chain rather than a mix: harmonic points are the music's own seams; energy deltas are a proxy.

**D3 — Greedy walk with a tail-aware cap.** From the segment start, the next cut is the strongest candidate (ties → latest) inside `[prev + min_piece_s, prev + cap]` where `cap = min(prev + max_section_s, seg_end - min_piece_s)` (falling back to `seg_end - MIN_SECTION_S`, then `prev + max_section_s`, when the segment is nearly done). The cap is what guarantees no sliver tail with the default parameters — the last piece always gets ≥ `min_piece_s`. No candidate in the window → cut at the beat nearest the cap (no beats → the cap itself). A piece never exceeds `max_section_s`; a sub-`MIN_SECTION_S` tail (reachable only when `max_section_s < min_piece_s + MIN_SECTION_S`, i.e. non-default parameters) folds into the previous piece like the lyric refiner's merge.

**D4 — Labels nest under the parent with a per-parent-id counter.** Parent "A" → "A1","A2",...; two coarse segments both named "A" continue one ordinal sequence (A1–A4 then A5–A8) so ids stay unique across the song. Short segments are appended untouched — same objects, byte-for-byte.

**D5 — Augment-and-resave + panel prior.** `AudioAnalyzer.refine_instrumental` mirrors `attach_lyrics`' tail: refine, refresh per-section instrumentation from persisted stems (best-effort), rewrite the `_content_key` cache file. The structure analyst's prompt gains one sentence: numbered sub-segments are subdivisions of ONE musical part — related but EVOLVING looks (continuity with escalation), boundaries are not theirs to re-derive.

## Risks / Trade-offs

- [Harmonic-change density varies wildly] → the greedy window bounds piece length regardless; the time-based last resort still beat-snaps.
- [Cuts inside a held note/phrase] → beat-snapping plus seam preference minimizes it; pieces are sub-segments of one part and the panel prior asks for evolving (not contrasting) looks across them.
- [More sections → more Generator calls] → Carol goes 4 → 10 sections; flash-tier generate calls, bounded by song length as before.
- [run.py constructs a fresh `AudioAnalyzer()` even under an injected `analyze`] → cheap (a Path assignment); the call is try/except'd so missing files/caches in tests degrade to a log line.

## Migration Plan

Additive. Lyric songs and short instrumentals behave exactly as today. Cached instrumental analyses refine and resave on the next run; re-runs no-op. Rollback = drop the run.py call; the refiner is inert without it.

## Open Questions

- Whether per-stem onset density should rank candidate windows once stems are routinely present — deferred.
