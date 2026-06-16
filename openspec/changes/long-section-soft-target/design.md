## Context

`cap_long_segments` searched `[prev + min_piece, prev + max_section]` and took the strongest seam,
tie-break earliest (after the seam-strength change). But `max_section` (32s) was both the HARD
ceiling AND the de-facto target: a cut could only land at or before it, so a real break a few
seconds past 32 was unreachable, and a flat window snapped to the cap edge. One number was doing
two jobs.

## Goals / Non-Goals

**Goals:** make section length a soft target (~25s) with symmetric ±10s flex so cuts land on the
audible break even slightly past the target; stop flat windows drifting to the ceiling; keep the
no-energy / harmonic-only / no-seam fallbacks working; centralize the audio-structure knobs in a
tuning file. **Non-Goals:** the broader cross-module R4 surface (the orchestrator side is already
done); deriving harmonic-change strength from chroma (the energy proxy stands).

## Decisions

**D1 — Soft target + flex; ceiling = target + flex.** `INSTR_TARGET_SECTION_S = 25`,
`INSTR_SECTION_FLEX_S = 10`. Each cut's window is `[prev + 15, prev + 35]` (clamped to keep the
tail ≥ `min_piece`). The loop stops while a remainder is ≤ the ceiling (35), so a 30–35s stretch
with no better break is left whole rather than force-cut.

**D2 — Rank by "is this a REAL break", then nearest the target.** A seam counts as real when its
energy `|Δrms|` ≥ `SEAM_MIN_STRENGTH_FRAC` (12%) of the song's full RMS span — relative, so it
adapts to the mix. Among real breaks, pick the one NEAREST the 25s target (ties → stronger), so we
pace ~25s rather than always jumping to the single biggest spike. The relative bar is load-bearing:
without it, a steady-volume harmonic seam closer to the target would beat the actual break.

**D3 — Graceful fallbacks.** No real break but weak/harmonic seams present → nearest-to-target seam
(preserves the harmonic-only behavior). No seam at all → beat nearest the target (not the ceiling
edge). A tiny sub-`MIN_SECTION` tail still folds into its predecessor.

**D4 — Core-side tuning file.** The audio-structure dials move to `xlights_core/audio/tuning.py`.
R4 centralized the orchestrator's dials in `pipeline/tuning.py`, but `xlights-core` is the lower
package (orchestrator depends on it), so it gets its own sibling. Constant names are unchanged and
still importable from `structure` (re-exported), so nothing downstream breaks.

## Risks / Trade-offs

- [A 33–35s piece can be left whole] → intended: the ceiling is 35, and a clean stretch shouldn't
  be chopped just to hit 25. Accepted.
- [The 12% bar and the nearest-target rule are heuristics] → both are single dials in `tuning.py`,
  easy to retune once validated on real audio; the synthetic Canon-shaped test pins the key
  behavior (a break at ~28s beats a 25s harmonic).

## Migration Plan

Additive; better cut points only. Already-split cached analyses won't re-cut (they fit). Branch
`claude/festive-pascal-t372cv`, PR (user merges). Real-audio verification (Canon) pending an
environment with the `[audio]` extra.

## Open Questions

- Final values for the target (25), flex (10), and the 12% real-break bar — confirm against real
  songs.
- Whether to feed true tonal-change strength (chroma distance) for harmonic-only breaks — deferred.
