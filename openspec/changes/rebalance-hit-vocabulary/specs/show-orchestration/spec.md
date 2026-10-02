## ADDED Requirements

### Requirement: Beat accents differentiate effect by rhythmic role
The deterministic beat-accent layer SHALL use role-appropriate effect types rather than one effect for all sublayers: the sparkle layer (accent props) and the backbeat answer SHALL place radial Shockwave hits (using the curated radiating-Shockwave settings, ~600 ms, clipped to the beat grid), while the meter backbone and bass foundation retain the section's accent effect (default On). An explicit Director-chosen accent effect SHALL still govern the backbone.

#### Scenario: Sparkle hits are shaped
- **WHEN** beat accents are placed for a rhythmic section with drum onsets and an accent prop group available
- **THEN** the sparkle-layer instructions carry effect type Shockwave with the curated radiating settings, not the backbone's On

#### Scenario: The backbone honors the brief
- **WHEN** the Director set `accent_effect` to a placeable effect
- **THEN** the meter-backbone instructions use that effect (unchanged behavior), while sparkle/backbeat remain Shockwave

### Requirement: Strobe is reserved for peak sections
Outside the show's peak section(s), a Strobe instruction SHALL be substituted with a Shockwave carrying the curated radiating settings (the hit moment is preserved; only the vocabulary changes). Shimmer SHALL be limited to a per-section instance cap in addition to its existing duration cap. (Corpus grounding: community Strobe = 3 placements in 27,099 effects; ours previously 290 in 3 runs.)

#### Scenario: Off-peak Strobe is substituted
- **WHEN** a generator-designed section that is not a peak contains a Strobe instruction
- **THEN** the realized section carries a Shockwave in its place at the same time span and target

#### Scenario: Peak Strobe survives
- **WHEN** the peak section contains a Strobe instruction
- **THEN** it is placed unchanged (subject to the existing ≤1 s hard cap)

#### Scenario: Shimmer instance cap
- **WHEN** a section's realized instructions contain more Shimmer instances than the cap
- **THEN** only the earliest instances up to the cap remain
