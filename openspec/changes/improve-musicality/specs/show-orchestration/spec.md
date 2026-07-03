## ADDED Requirements

### Requirement: Repeated music visually rhymes and escalates

When the music brief's repetition map marks sections as occurrences of the same musical material
(e.g. the choruses), the generation pipeline SHALL realize those sections with a shared visual
identity: the same weave carrier effect, the same peak-composite choice, and the same palette
rotation, keyed to the repetition label rather than the section's position in the song. Sections
that do not recur SHALL keep position-keyed variety. Escalation across occurrences SHALL be
structural — later occurrences gain prop coverage and accent density, and the final occurrence gains
an additional layer — bounded by the existing layer and hard-cap budgets, in addition to the
existing intensity lift.

#### Scenario: Choruses share a carrier

- **WHEN** the repetition map lists sections 2, 5, and 8 under one label and sections are realized
- **THEN** all three receive the same weave carrier and palette rotation, while unrelated one-off
  sections may differ from each other as today

#### Scenario: The last chorus is the biggest

- **WHEN** the final occurrence of a recurring label is realized
- **THEN** it lights at least as many prop groups as the first occurrence, with denser accents
  and one additional layer when the layout has accent props, without exceeding the layer budget

### Requirement: Sections are realized with distinct treatments

Each planned section SHALL carry a treatment (full, pulse, feature, gesture, or rest) that controls
which realization layers are included — withholding layers, not merely dimming them. The treatment
is chosen by the Director and SHALL fall back to a deterministic energy-based mapping when absent,
so previously cached plans remain valid. A rest or gesture treatment produces a genuinely sparse or
near-dark section; the pipeline SHALL inject a minimal bed only when more than two consecutive
sections would otherwise have no base layer.

#### Scenario: A quiet verse is sparse, not dim

- **WHEN** a section with gesture treatment is realized
- **THEN** it contains a single carrier recipe on at most two groups, with no bed, weave fabric,
  accents, or composite layers

#### Scenario: Old cached plans still work

- **WHEN** a cached show plan without treatment fields is loaded
- **THEN** every section resolves a treatment from its intensity and the show's peak set, and
  generation proceeds without error

### Requirement: Section boundaries are composed transitions

The pipeline SHALL place boundary transitions derived from the song's energy arc, downbeat grid, and
the brief's transition cues: a build/riser ending at a boundary the energy rises into, a one-beat
gate (blackout) immediately before a detected drop that lands on a downbeat, and an optional sweep
handoff on lateral boundaries. Transition instructions SHALL belong to the outgoing section's index
so regenerating the incoming section preserves them, and the pass SHALL be idempotent so re-running
it after a section splice replaces rather than stacks transitions.

#### Scenario: The drop hits out of darkness

- **WHEN** the energy arc shows a large upward step at a section boundary landing on a downbeat
- **THEN** instructions in the final beat before the boundary are gated so the display goes dark for
  that beat and relights at the drop

#### Scenario: Regen keeps the riser

- **WHEN** the section after a riser is regenerated and the transition pass re-runs
- **THEN** exactly one riser remains at that boundary

### Requirement: The show has a color script and phrase-shaped dynamics

The realized show SHALL carry a deterministic show-level color script: one anchor color present in
every section's palette, a signature color pair shared verbatim by all occurrences of the chorus
label, and deliberate hue contrast at the bridge. Sustained beds and washes SHALL receive brightness
value curves shaped by the section's own energy arc (rising, falling, or flat) and swells at
phrase starts, while accents and features keep crisp levels.

#### Scenario: One palette thread runs through the show

- **WHEN** a plan's sections are post-processed by the color script
- **THEN** every section palette contains the anchor color, and all chorus-label sections share the
  same signature pair

#### Scenario: A building bed swells

- **WHEN** a bed spans at least two bars over a rising stretch of the energy arc
- **THEN** its brightness carries an upward value curve rather than a flat level
