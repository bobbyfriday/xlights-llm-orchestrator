## 1. Implementation
- [x] 1.1 `audio/structure.py`: score seam candidates by energy `|Δrms|` (harmonic times scored by nearby energy; energy-delta points as candidates); pick strongest, tie-break earliest; `SEAM_ENERGY_NEAR_S` constant.

## 2. Tests
- [x] 2.1 A window with dense harmonic noise + one energy break cuts at the break, not the latest harmonic.
- [x] 2.2 Existing instrumental/lyric tests still pass (harmonic-only and energy-fallback cases hold).
- [x] 2.3 Full suite passes.

## 3. Verify + land
- [x] 3.1 Canon: first intro cut moves 31.9s → 29.1s (energy re-entry); later cuts to energy seams.
- [x] 3.2 Archive, commit, push, open PR (user merges).
