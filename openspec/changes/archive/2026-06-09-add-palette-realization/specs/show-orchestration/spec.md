## ADDED Requirements

### Requirement: Generated effects use the creative brief's section palette
When a section's creative brief specifies a palette (its chosen colors), the generated effects for that section SHALL be colored with that palette.

#### Scenario: Section has a brief palette
- **WHEN** a section's plan specifies colors
- **THEN** that section's placed effects use a palette built from those colors

### Requirement: Fall back to a mined palette when no brief palette applies
When no brief palette is specified for a section, or its colors cannot be realized, generation SHALL fall back to a mined palette rather than failing.

#### Scenario: No usable brief palette
- **WHEN** a section has no specified colors (or none can be realized)
- **THEN** placement uses a mined palette and the effect still places
