## ADDED Requirements

### Requirement: Effects can carry synthesized value curves
The system SHALL be able to synthesize a value curve for an effect parameter and attach it to a placed effect, so the parameter varies (ramps/swells/fades) over the effect's duration.

#### Scenario: Brightness ramp
- **WHEN** an effect is placed with a synthesized brightness ramp
- **THEN** the placed effect's settings include a valid value curve for brightness

### Requirement: Synthesized curves are valid and appended safely
A synthesized value curve SHALL be a valid xLights value-curve string (parseable by the existing parser) and SHALL be attachable to an effect even when the effect's preset has no such knob.

#### Scenario: Added to a look without that knob
- **WHEN** a value curve is attached to an effect whose preset does not define that parameter
- **THEN** placement still succeeds and the curve is present in the effect's settings
