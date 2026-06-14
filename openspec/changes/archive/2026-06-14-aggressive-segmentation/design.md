## Context

`refine_segments_for_instrumental` already had the right machinery — greedy seam-cutting capped at `INSTR_MAX_SECTION_S` (32s), preferring harmonic-change points, then energy-delta peaks, then beat-snapped time. But it was gated `if lyr.get("lines"): return False`, so it never ran on a song with lyrics. The lyric refiner (`refine_segments_with_lyrics`) cuts only at lyric markers and in-fills long instrumental spans **using existing audio-segment boundaries** — which don't exist inside a passage the audio segmenter didn't split (Canon's intro). So the cap never reached lyric songs' long lyric-free spans.

## Goals / Non-Goals

**Goals:** no section over the cap, regardless of lyrics; reuse the existing seam-cutting; keep the lyric and instrumental refiners' current behavior/tests intact. **Non-Goals:** changing the cap value or the seam heuristics; re-segmenting at the show-plan level (this is the analysis layer); subdividing *short* sections.

## Decisions

**D1 — Extract `cap_long_segments`, drop the lyrics gate.** The cutting loop becomes a standalone `cap_long_segments(analysis, max_section_s, min_piece_s)` that operates on whatever `analysis.segments` are present, with no lyrics check. It keeps the early-out (all fit → False) so it's idempotent and a safe no-op.

**D2 — Apply it in the analyzer, not inside the refiners.** The cap runs as an orchestration step in `analyzer.attach_lyrics` (after `refine_segments_with_lyrics`), and `refine_segments_for_instrumental` delegates to it (keeping its lyrics gate as the no-lyrics entry point). Putting the cap at the orchestration layer keeps each refiner single-purpose and its unit tests unchanged — the lyric refiner is still tested in isolation without the cap perturbing its output.

**D3 — Keep the 32s cap.** `INSTR_MAX_SECTION_S` (32s) is the established "a look past ~35s reads as boring" threshold; the bug was never applying it to lyric songs, not the value. Easy to lower later if finer sections are wanted.

## Risks / Trade-offs

- [More sections → more director/generator LLM calls per song] → bounded by the 32s cap (a 4-min song → ~8–12 sections, not 40); cuts land on real musical seams, so they're meaningful, not arbitrary.
- [Subdividing a labeled lyric section that happens to be long] → pieces inherit the parent label + ordinal (`Chorus` → `Chorus1`, `Chorus2`), which is the same scheme the instrumental path already uses; the director still sees the lineage.
- [A genuinely static long passage gets artificial cuts] → accepted (the user explicitly wants aggression on large segments); cuts prefer harmonic/energy seams, so they fall where the music actually changes.

## Migration Plan

Additive at the analysis layer. Cached analyses re-cap on the next augment-and-resave (or a `--no-cache` run). Branch `change/aggressive-segmentation`, PR (user merges).

## Open Questions

- Whether to expose the cap as a per-run knob (e.g. a CLI/env override) for users who want finer or coarser sections — deferred until there's a second opinion on 32s.
