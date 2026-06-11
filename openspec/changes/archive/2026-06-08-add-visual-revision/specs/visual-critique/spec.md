## ADDED Requirements

### Requirement: The visual critique is music-aware
The visual critique SHALL judge the rendered visuals against each section's musical context (its energy/intensity and role — e.g. quiet, build, drop, peak, transition — and neighboring sections), so that darkness, staticness, or low energy is assessed as appropriate or defective for that moment rather than by brightness alone.

#### Scenario: Intentional dark moment is not flagged
- **WHEN** a section renders dark during a quiet lull before a transition
- **THEN** the critique does not treat the darkness as a defect

#### Scenario: Inappropriate dark moment is flagged
- **WHEN** a section renders dark during a high-energy moment of the music
- **THEN** the critique flags it as a defect for that section

### Requirement: The critique assesses dynamics, variety, and music-sync
The visual critique SHALL assess whether the show is dynamic and varied (neither repetitive nor random) and whether the visual effects align with the music's energy and structure.

#### Scenario: Repetitive or random show is flagged
- **WHEN** the visuals are monotonously repetitive, or change without relation to the music
- **THEN** the critique reports a dynamics/variety problem

#### Scenario: Energy mismatch is flagged
- **WHEN** the visual energy does not match the music at a moment (e.g. static visuals under a high-energy passage)
- **THEN** the critique reports a music-sync problem scoped to that section
