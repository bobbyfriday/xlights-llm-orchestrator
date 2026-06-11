## ADDED Requirements

### Requirement: Multi-color effects receive enough colors
Effects that render multiple palette colors SHALL receive at least 3 colors, expanded deterministically from the section palette when the brief is thin.

#### Scenario: Plasma with a 2-color brief
- **WHEN** a multi-color effect is placed in a section whose brief has 2 colors
- **THEN** its palette is expanded to 3+ colors derived from the section's

### Requirement: Concurrent effects vary within the section palette
Effects in the same section SHALL NOT all carry an identical palette; assignments vary (rotation) within the section's color family.

#### Scenario: Two washes in one section
- **WHEN** two effects are placed in the same section
- **THEN** their palettes differ in color order/subset while staying in the section's palette

### Requirement: The Director's color names resolve
The Director SHALL be guided to the known color vocabulary, and common show colors SHALL be present in it, so chosen names are not silently dropped.

#### Scenario: Copper
- **WHEN** the brief names a common show color like Copper
- **THEN** it resolves to a hex rather than being dropped
