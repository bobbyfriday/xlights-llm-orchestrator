## MODIFIED Requirements

### Requirement: Long-section cuts land on the strongest seam, not the latest
When subdividing a long section, each cut SHALL aim for a soft target length and flex within a
fixed ± tolerance to land on the strongest REAL structural break in that window — a "real" break
being a point where the energy shifts by at least a minimum fraction of the song's RMS span
(harmonic-change times scored by the coincident energy shift; energy-delta points scored directly).
Among real breaks the cut SHALL pick the one nearest the target (ties toward the stronger). When the
window holds only weak or harmonic-only seams, the seam nearest the target SHALL be used; when it
holds no seam at all, the cut SHALL fall back to a beat near the target. No section SHALL exceed the
ceiling (target + flex).

#### Scenario: A real energy break beats a run of weak harmonic changes
- **WHEN** a window contains many equally-weighted harmonic-change candidates plus one point where the energy clearly drops out / surges back
- **THEN** the cut is placed at the energy break, not at a harmonic change that merely sits closer to the target

#### Scenario: A real break a little past the target is reachable
- **WHEN** the nearest real break sits a few seconds beyond the soft target but within the flex tolerance
- **THEN** the cut reaches that break instead of being forced to an earlier, weaker point before a hard cap

#### Scenario: A flat window cuts at the target, not the ceiling
- **WHEN** a window has no real energy break (a steady-volume stretch) and no seam at all
- **THEN** the cut lands on a beat near the soft target, not drifted to the ceiling
