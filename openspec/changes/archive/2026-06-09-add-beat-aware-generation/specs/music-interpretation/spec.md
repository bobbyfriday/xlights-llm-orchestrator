## ADDED Requirements

### Requirement: Surface per-section rhythm for generation
The interpretation SHALL surface, per section, the beat times and the section's prominent instrument with its onset times, so generation can place rhythmically.

#### Scenario: Section rhythm available
- **WHEN** a section is interpreted and stems are available
- **THEN** its beat times, its prominent instrument, and that instrument's onset times within the section are available to generation

#### Scenario: No stems
- **WHEN** stem data is unavailable
- **THEN** the beat times are still surfaced and the prominent instrument degrades gracefully (rhythm can still follow the beats)
