## ADDED Requirements

### Requirement: Long-section cuts land on the strongest seam, not the latest
When subdividing a long section, the cut within each window SHALL be chosen by structural-seam STRENGTH — how much the energy changes at the seam (harmonic-change times scored by the coincident energy shift; energy-delta points scored directly) — selecting the strongest seam and breaking ties toward the earliest time, so cuts land on the real break rather than drifting to the length cap.

#### Scenario: A real energy break beats a run of weak harmonic changes
- **WHEN** a window contains many equally-weighted harmonic-change candidates plus one point where the energy clearly drops out / surges back
- **THEN** the cut is placed at the energy break, not at the latest harmonic change near the cap

#### Scenario: No seam data falls back to spacing
- **WHEN** a window has no harmonic or energy candidate at all
- **THEN** the cut falls back to an even beat-snapped spacing near the cap, as before
