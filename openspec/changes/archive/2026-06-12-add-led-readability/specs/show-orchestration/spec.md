## ADDED Requirements

### Requirement: Directional cells render as visible cross-group motion
WHEN a cell recipe specifies a horizontal or radial direction on a chase-family effect, the cell SHALL render on a buffer spanning the full target group (so the motion travels across all of the group's props) and SHALL persist long enough to track (a minimum cell length of two beats), unless the recipe explicitly chooses a render style. Non-directional cells SHALL keep the per-model default.

#### Scenario: A left-to-right chase travels the whole arch line
- **WHEN** a carrier recipe over the arches specifies ltr on a chase effect with no explicit render style
- **THEN** its cells render on the group buffer with at least two-beat duration, so one chase head visibly travels across all the arches

#### Scenario: Explicit style and non-directional cells unchanged
- **WHEN** a recipe explicitly sets a render style, or has no direction
- **THEN** the cell uses exactly that style (or the per-model default), as today

### Requirement: Automated palettes guarantee LED-legible hue contrast
The palette realization SHALL enforce a hue-contrast floor: WHEN a section's resolvable colors cluster within a minimum hue spread, a contrasting anchor SHALL be injected deterministically; rhythm-carrying cells (carrier and accent roles, and the beat-accent layer) SHALL alternate between the two most hue-distant anchors beat-to-beat, while texture and bed placements keep the section's expanded color family.

#### Scenario: A warm-clustered palette gains a contrast anchor
- **WHEN** a section's palette resolves to near-identical warm hues (e.g. golds and warm whites)
- **THEN** a hue-distant anchor is injected and consecutive carrier cells alternate between two clearly different colors, while the section's washes keep the warm family

#### Scenario: An already-contrasting palette is untouched
- **WHEN** a section's palette already spans distant hues (e.g. deep blue and gold)
- **THEN** no color is injected and the two existing most-distant colors become the alternating anchors
