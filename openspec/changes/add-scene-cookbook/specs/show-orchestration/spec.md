## ADDED Requirements

### Requirement: Sections compose from cookbook scenes
The Director SHALL choose a cookbook scene (or explicitly freeform) per section with an archetype-to-group casting, and the Generator SHALL realize the chosen scene's stack.

#### Scenario: Scene chosen
- **WHEN** a section's design names a scene
- **THEN** the brief records the scene and casting, and generation realizes its stack on the cast groups

#### Scenario: Freeform allowed
- **WHEN** no scene fits a section
- **THEN** the section may be freeform (empty scene id) and generation proceeds as before

### Requirement: Subtractive ensemble groups exist for scenes
The layout semantics SHALL include subtractive groups (all-less-hero, all-less-hero-rhythm) so beds never paint over features.

#### Scenario: Bed under a clean hero
- **WHEN** the layout is (re)generated
- **THEN** SEM_ALL_LESS_FOCAL and SEM_ALL_LESS_FOCAL_RHYTHM exist with the right members
