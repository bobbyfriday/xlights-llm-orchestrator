## ADDED Requirements

### Requirement: Catalog hard caps are enforced
Strobe and Shimmer durations SHALL be clamped to the catalog's hard caps (Strobe ≤ ~1s, Shimmer ≤ ~2 bars) regardless of what generation produced.

#### Scenario: Over-long strobe
- **WHEN** generation produces a 10-second Strobe
- **THEN** the placed effect is clamped to the cap

### Requirement: Placement-rule violations gate the loop
Texture-on-linear-prop, energy-band-mismatch, and overlapping-feature violations SHALL be detected as objective findings so the refine loop regenerates the offending sections.

#### Scenario: Texture on a linear prop
- **WHEN** a texture effect targets an arch/outline group
- **THEN** an objective finding names the section and the violation

#### Scenario: Energy mismatch
- **WHEN** an effect's energy band is far from its section's energy
- **THEN** an objective finding is raised

#### Scenario: Two features at once
- **WHEN** two high-attention effects overlap in time
- **THEN** an objective finding is raised
