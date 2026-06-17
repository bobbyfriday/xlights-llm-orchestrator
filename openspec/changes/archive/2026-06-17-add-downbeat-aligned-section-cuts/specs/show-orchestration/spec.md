## MODIFIED Requirements

### Requirement: Long-section cuts land on the strongest seam, not the latest
When subdividing a long section, the cut within each window SHALL be chosen by structural-seam
STRENGTH — how much the energy changes at the seam (harmonic-change times scored by the coincident
energy shift; energy-delta points scored directly) — selecting the strongest seam and breaking ties
toward the earliest time, so cuts land on the real break rather than drifting to the length cap.

Cut placement SHALL additionally be DOWNBEAT-AWARE: candidate seams and the chosen cut SHALL snap to
the nearest downbeat (bar line) when one lies within a small tolerance of the seam, using the beat
grid's bar positions, so a section boundary lands on a bar line rather than a weak off-beat. A seam
whose bar line falls outside the current window (e.g. a loud seam near the cap whose downbeat is past
the cap) SHALL be excluded, so an earlier downbeat phrase boundary is preferred over a louder
off-beat seam near the cap. When the beat grid carries no bar positions, cut placement SHALL fall
back to beat-snapped behavior unchanged. Snapping SHALL never produce a piece shorter than the
minimum-piece floor nor a section longer than the cap.

#### Scenario: A real energy break beats a run of weak harmonic changes
- **WHEN** a window contains many equally-weighted harmonic-change candidates plus one point where the energy clearly drops out / surges back
- **THEN** the cut is placed at the energy break, not at the latest harmonic change near the cap

#### Scenario: A cut lands on the bar line, not a weak off-beat near the cap
- **WHEN** a window's strongest energy seam sits on a weak beat near the cap while an earlier downbeat carries a real phrase boundary (a coincident harmonic change)
- **THEN** the off-beat seam's bar line falls past the cap and is excluded, and the cut lands on the earlier downbeat

#### Scenario: Chosen cut snaps to the nearest downbeat within tolerance
- **WHEN** the selected cut time sits within the snap tolerance of a downbeat that respects the minimum-piece floor and the cap
- **THEN** the cut is placed on that downbeat

#### Scenario: No bar positions falls back to beat snapping
- **WHEN** the beat grid carries no bar-position information
- **THEN** cuts are chosen and beat-snapped exactly as before, with no downbeat adjustment

#### Scenario: No seam data falls back to spacing
- **WHEN** a window has no harmonic or energy candidate at all
- **THEN** the cut falls back to an even beat-snapped spacing near the cap, snapped to a downbeat when one is within tolerance
