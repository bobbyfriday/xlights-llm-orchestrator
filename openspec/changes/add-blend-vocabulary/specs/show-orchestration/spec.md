## ADDED Requirements

### Requirement: Texture cells over a base blend as brightness gates
When a texture-role weave cell is placed over a target that carries a base layer, its default blend mode SHALL be `Brightness` (the cell's luminance modulates the base below — the community's dominant blend, 36% of their blended rows), while carrier and accent cells retain the `Max` default. An explicit blend on a recipe SHALL always override the default.

#### Scenario: A texture cell defaults to Brightness
- **WHEN** a texture-role cell recipe with no explicit blend expands onto a target that has a bed
- **THEN** the cell instruction carries `T_CHOICE_LayerMethod: Brightness`

#### Scenario: Carriers keep Max
- **WHEN** a carrier-role cell with no explicit blend expands onto a based target
- **THEN** the cell instruction carries `T_CHOICE_LayerMethod: Max` (unchanged behavior)

#### Scenario: The LLM's blend wins
- **WHEN** a texture recipe explicitly sets `blend: "Max"`
- **THEN** the cell carries Max, not the Brightness default

### Requirement: A curated mask/reveal composite exists
The curated composite library SHALL include a `reveal` stack — a texture base under a `Shape` layer blended with the mask family (`1 is Mask`, or the corrected polarity if a live check shows the inverse) — and the peak-composite rotation SHALL include it. (Corpus grounding: Shape-over-Spirals is the #3 stacked pair in the community corpus, 1,189 occurrences.)

#### Scenario: The reveal composite expands with a mask blend
- **WHEN** the `reveal` composite is expanded on a group
- **THEN** it emits a texture base layer and an upper Shape layer whose `T_CHOICE_LayerMethod` is in the mask family

#### Scenario: Reveal participates in the peak rotation
- **WHEN** enough distinct peak identities occur across shows
- **THEN** the `reveal` stack is among the composites rotated onto the hero at peaks
