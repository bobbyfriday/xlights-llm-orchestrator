## ADDED Requirements

### Requirement: Curated trigger effects from a hand-editable cookbook
The orchestrator SHALL place curated "trigger" effects — deterministic rules mapping musical or lyrical events to scaled effects — defined in a hand-editable markdown cookbook parsed best-effort (a missing or malformed entry is skipped, never fatal). Each trigger SHALL declare its detector, effect, render scope, rarity, section eligibility, and color/direction treatment. Triggers SHALL be applied as a deterministic layer over the existing fabric and SHALL respect the hard caps and layer budget.

#### Scenario: A cookbook trigger places its effect
- **WHEN** the cookbook defines a trigger whose detector finds events in the analysis
- **THEN** the pipeline places that trigger's effect at the detected times, scaled and colored per the cookbook, tagged with the section index

#### Scenario: Editing the cookbook changes the show without code
- **WHEN** a user edits the cookbook (tunes a threshold, changes an effect or color, enables/disables a trigger that reuses an existing detector)
- **THEN** the next run reflects the edit with no code change

#### Scenario: A malformed or unknown trigger is skipped
- **WHEN** a cookbook entry names an unknown detector or has invalid fields
- **THEN** that trigger is skipped with a log and the run proceeds

### Requirement: Triggers are used sparingly across the show
Trigger effects SHALL be bounded by two sparsity scales: section selection (a deterministic rotation so not every section features the same accent) and per-trigger within-section density. Periodic drum triggers SHALL key to the drum stem's onsets (not the beat grid); singular triggers (a big-moment shockwave) SHALL fire on the strongest event in their region only.

#### Scenario: Not every section gets the same accent
- **WHEN** several sections are eligible for the same periodic trigger
- **THEN** only a rotated subset feature it, so consecutive sections differ

#### Scenario: The big moment is singular
- **WHEN** the big-moment shockwave trigger runs over a region
- **THEN** it fires once on the strongest drum hit / energy jump there, rendered across the whole house

### Requirement: Trigger scale and variety come from render scope and per-event modulation
Small vs large SHALL be expressed as render scope — per-model (each prop, prop-scaled) vs whole-house (one radiating gesture) — not by shrinking a radius. Successive events of a periodic trigger SHALL vary deterministically: rotating target groups and alternating contrast-anchor color and out/in direction.

#### Scenario: Periodic drum shockwaves vary per hit
- **WHEN** the periodic drum-onset shockwave trigger fires across a section
- **THEN** successive onsets rotate across the rhythm groups and alternate color and out/in radius, each rendered per-model

### Requirement: Word-precise lyric timing for color words
The analysis SHALL persist per-word lyric timestamps (already computed during alignment) so lyric-driven triggers can place effects on the word, not only the line.

#### Scenario: A color word lights the yard
- **WHEN** a lyric line contains a color word and per-word timing is available
- **THEN** the color-word trigger colors the prominent props at that word's time
