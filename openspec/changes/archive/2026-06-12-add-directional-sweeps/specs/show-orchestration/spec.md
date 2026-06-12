## ADDED Requirements

### Requirement: Beat cells support directional realization via effect settings
Beat-synchronized cells SHALL support direction — left/right sweeps, bounces, center-out/center-in gestures, and up/down runs — realized exclusively through the effects' own direction parameters (chase types, direction choices, reverse flags) using corpus-observed values, without altering the cells' target groups or render styles. Direction SHALL be directable by the generation LLM per cell recipe; WHEN a recipe names no direction, explicit recipes SHALL expand exactly as today while the deterministic fallback weave SHALL default to a bouncing sweep. An effect with no mapped direction parameter SHALL ignore the direction without failing.

#### Scenario: Chase direction comes from the effect's chase type
- **WHEN** a carrier recipe over the arches specifies left-to-right (or center-out)
- **THEN** its cells carry the effect's own direction setting (e.g. chase type Left-Right, or From Middle) in their settings, targets and render styles unchanged

#### Scenario: Static-direction effects bounce per bar
- **WHEN** a recipe with a static-direction effect (e.g. Fill or Wave) specifies bounce
- **THEN** cells within one bar share a single direction and the direction value reverses at each bar boundary, while effects with native bounce types (e.g. SingleStrand Dual Bounce) bounce within the effect itself

#### Scenario: Graceful degradation
- **WHEN** a recipe's effect has no mapped direction parameter, or the direction value is unknown
- **THEN** cells expand exactly as they do today

### Requirement: The beat-accent chase alternates direction per bar
The deterministic every-beat accent layer SHALL alternate its group-rotation order on each bar — forward through the spatial group order on even bars, backward on odd bars — with no LLM involvement.

#### Scenario: Accent chase bounces
- **WHEN** beat accents chase three rhythm groups across two consecutive bars
- **THEN** the first bar visits the groups in spatial order and the second bar visits them in reverse order
