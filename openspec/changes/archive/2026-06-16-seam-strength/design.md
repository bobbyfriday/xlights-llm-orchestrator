## Context

The cutter searched the [min_piece, max_section] window for seams, preferring harmonic-change points. But `analysis.harmonic_changes` carries TIMES only (no strength), so the code weighted them all `1.0` and `max((w, t))` broke ties by latest `t`. With harmonic changes dense (Canon: ~every 0.5s), that always selected the last one before the cap — equivalent to maxing the section length. The energy curve, meanwhile, pinpoints the real break (drop-out → re-entry).

## Goals / Non-Goals

**Goals:** cuts land on the audible structural break (energy change), not the cap; keep harmonic seams as candidates but rank by strength; don't regress the no-energy / synthetic cases. **Non-Goals:** changing the cap value or the windowing; deriving harmonic-change strength from chroma (we use energy as the proxy).

## Decisions

**D1 — Strength = energy |Δrms|.** Build energy deltas from `energy_arc`. Each harmonic-change time scores by the max `|Δrms|` within `SEAM_ENERGY_NEAR_S` (0.75s, ~one arc step) of it; energy-delta points are candidates with their own `|Δrms|`. Per snapped beat-time, keep the max. So a chord-change-AND-energy-jump scores highest, a dense run of chord changes at steady volume no longer ties.

**D2 — Pick strongest, tie-break EARLIEST.** `max(inside, key=(strength, -time))`. Earliest tie-break removes the cap-drift: equal-strength seams resolve toward the start of the window, not the 32s edge.

**D3 — Keep the candidates even at strength 0.** A harmonic seam with no energy data (synthetic tests, or a flat passage) is still a candidate and still beats pure time-spacing — only when a window has NO candidate at all do we fall back to a beat near the cap. (Real songs always have an energy_arc, so the strength ranking drives every real cut.)

## Risks / Trade-offs

- [A key change at steady volume has strength 0 and may be missed] → rare (key changes usually carry a dynamic shift); old code handled it no better (picked latest). Accepted.
- [Energy-delta noise picks a spurious peak] → the arc is ~0.5s-smoothed RMS; the dominant peak in a 20s window is the structural break, not noise (validated on Canon).

## Migration Plan

Additive; better cut points only. Already-split cached analyses won't re-cut (they fit), so a song re-benefits on a fresh analysis (or a manual re-cap). Branch `change/seam-strength`, PR (user merges).

## Open Questions

- Whether to also feed true tonal-change strength (chroma distance) when the VAMP plugin exposes it — would sharpen harmonic-only breaks; deferred (energy proxy covers the observed cases).
