## ADDED Requirements

### Requirement: Build an effect palette from named or hex colors
The system SHALL build a valid effect palette from a list of named or hex colors, with the named colors resolved via a known color vocabulary and `#RRGGBB` accepted directly.

#### Scenario: Named + hex colors
- **WHEN** a list of colors like `["warm white", "deep blue", "#DC143C"]` is given
- **THEN** a valid palette is produced with those colors as its active entries

### Requirement: Color realization degrades gracefully
An unknown color name SHALL be skipped rather than producing an invalid palette, and an empty or fully-unmapped color list SHALL yield no palette (so callers fall back).

#### Scenario: Unknown color
- **WHEN** a color name is not recognized
- **THEN** it is skipped and the remaining recognized colors still form a valid palette

#### Scenario: Nothing usable
- **WHEN** the color list is empty or none of its names resolve
- **THEN** no palette is produced (a null result the caller can fall back from)
