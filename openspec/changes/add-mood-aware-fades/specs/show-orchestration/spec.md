## ADDED Requirements

### Requirement: Section phrasing is directable as legato or staccato

The show plan SHALL let the Director direct each section's phrasing — the soft-versus-crisp
character of its woven cells — through an optional `phrasing` field on the section plan whose
value is `legato`, `staccato`, or empty. `legato` SHALL mean evolving, softly-faded cells suited
to calm or introspective sections; `staccato` SHALL mean crisp on/off cells suited to energetic
sections. The field SHALL be optional and back-compatible: a section (or a cached plan) that omits
it SHALL remain valid.

#### Scenario: Director directs legato phrasing

- **WHEN** the Director sets a section's `phrasing` to `legato`
- **THEN** the section plan carries that value and the weaver realizes that section's cells with
  soft fades rather than crisp on/off edges

#### Scenario: Phrasing is optional and back-compatible

- **WHEN** a section plan (or a previously cached plan) omits `phrasing`
- **THEN** the plan is still valid and generation proceeds, resolving phrasing from the section's
  intensity rather than failing

### Requirement: The weaver realizes legato phrasing as a curated soft-edge transition

The cell weaver SHALL resolve each section's effective phrasing — the directed `phrasing` value
when present, otherwise derived from the section's intensity (low intensity SHALL resolve to
legato, energetic intensity SHALL resolve to staccato) — and SHALL realize legato cells with a
soft-edge transition primitive selected in code from the cell's effect family: a linear fade-in /
fade-out (scaled to the cell's duration and bounded by a cap) for line and chase effects, or a
dissolve in/out transition for textural fill and wash effects. The selection and all numeric
values SHALL be owned by code, not the Director. Staccato cells SHALL carry no synthesized
soft-edge keys, so energetic sections render exactly as they do today. A cell recipe that already
names an explicit transition SHALL keep that transition (the phrasing-derived primitive applies
only when the recipe names none). Legato realization SHALL NOT increase a section's cell count
beyond its existing intensity-scaled budget.

#### Scenario: Low-intensity line effect softens with a fade

- **WHEN** a low-intensity section with no directed phrasing weaves a line or chase effect
- **THEN** its cells carry synthesized fade-in/fade-out settings (in xLights' fade units) sized
  from each cell's length and clamped to the cap, so the section reads as evolving rather than
  flashing

#### Scenario: Legato textural effect softens with a dissolve

- **WHEN** a legato section weaves a textural fill or wash effect
- **THEN** its cells carry a dissolve in/out transition (with code-set adjust) rather than a flat
  opacity fade

#### Scenario: Energetic section stays crisp

- **WHEN** a section resolves to staccato (directed, or energetic by intensity) is woven
- **THEN** its cells carry no synthesized soft-edge keys and the placements match the pre-change
  crisp behavior

#### Scenario: Directed phrasing overrides the intensity default

- **WHEN** a section's intensity would imply staccato but the Director directs `legato` (or vice
  versa)
- **THEN** the weaver uses the directed phrasing, not the intensity-derived default

#### Scenario: An explicit recipe transition is preserved

- **WHEN** a legato cell recipe already names its own transition
- **THEN** the weaver keeps the recipe's transition and does not overwrite it with the
  phrasing-derived primitive
