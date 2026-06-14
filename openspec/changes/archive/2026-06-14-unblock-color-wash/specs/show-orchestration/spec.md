## ADDED Requirements

### Requirement: Color Wash is a placeable effect type
"Color Wash" SHALL be treated as a placeable effect type — included in the placeable set offered to the director and enumerated by the editable-brief schema — having been re-verified to place (`addEffect` `worked=true`) and render via the automation API. The reject-list mechanism SHALL remain for any effect type genuinely confirmed unplaceable.

#### Scenario: Color Wash is offered and accepted
- **WHEN** the placeable effect types are computed
- **THEN** "Color Wash" is included, so the director may choose it and the brief schema lists it as a valid effect type

#### Scenario: The reject mechanism still exists
- **WHEN** a future effect type is confirmed unplaceable and added to the reject list
- **THEN** it is filtered out of the placeable set exactly as before
