## MODIFIED Requirements

### Requirement: A layout manifest is emitted
A `layout_semantics.json` manifest SHALL be written describing each prop's role, capability, position, and the groups, for the planner to consume. The manifest's schema, field inventory, size budget, and version-tolerance rules SHALL be governed by the `layout-onboarding` capability, which is the single canonical home for the manifest contract; this requirement retains the emission-and-consumption obligation and defers those details to it.

#### Scenario: Manifest written
- **WHEN** the generator runs
- **THEN** `layout_semantics.json` is written with per-prop role/res/pos and the group membership

#### Scenario: The manifest contract is owned by layout-onboarding
- **WHEN** the manifest's schema, fields, size budget, or version-tolerance behavior is specified or changed
- **THEN** the `layout-onboarding` capability's manifest requirement is the authority, and this capability consumes the manifest through its tolerant loader (absent or version-mismatched loads as nothing) rather than restating the contract

### Requirement: Placement-rule violations gate the loop
Texture-on-linear-prop, energy-band-mismatch, and overlapping-feature violations SHALL be detected as objective findings so the refine loop regenerates the offending sections. When a layout manifest is loaded, the linear/capability classification of a target SHALL derive from the manifest's capability classes (the prop's own class, or the union of member classes for a group) rather than from the name-prefix table; when no manifest is present, the name-prefix fallback SHALL apply so QA behavior is unchanged from today.

#### Scenario: Texture on a linear prop
- **WHEN** a texture effect targets an arch/outline group
- **THEN** an objective finding names the section and the violation

#### Scenario: Energy mismatch
- **WHEN** an effect's energy band is far from its section's energy
- **THEN** an objective finding is raised

#### Scenario: Two features at once
- **WHEN** two high-attention effects overlap in time
- **THEN** an objective finding is raised

#### Scenario: Capability gating is manifest-derived
- **WHEN** a manifest is loaded and a texture effect targets a group whose members are linear-capability props but whose name matches no linear prefix
- **THEN** the texture-on-linear violation is still detected from the manifest's capability classes (and a matrix-dominated group the prefix rule would wrongly flag is not flagged)

#### Scenario: No manifest falls back to prefixes
- **WHEN** QA evaluates with no manifest available
- **THEN** the name-prefix table gates exactly as before and existing findings are unchanged

### Requirement: Rhythm group selection is layout-derived
Generation SHALL select the groups each rhythm sublayer targets — the metric ring, the sparkle props,
the hero, the bass band, and the backbeat group — from the layout's classified groups by
role/capability/band rather than a single fixed list, and SHALL degrade gracefully so a missing
category disables only its own sublayer. The brief's pulse groups SHALL still seed and override the
metric ring.

The choreography vocabulary these sublayers draw from — the metric ring, backbeat preference, bed
preference, peak-broad order, accent groups, hero group, and bass band — SHALL be derived from the
layout manifest when one is loaded, ranking the rhythm families by instance count, spatial spread,
and node budget, and SHALL fall back to the hardcoded `DEFAULT_VOCAB` constants when no manifest is
loaded. Every derived choice SHALL still be filtered against the live targetable-group set (the
vocabulary proposes, the live probe disposes).

#### Scenario: Selection adapts to the available groups
- **WHEN** a layout provides rhythm-cell, accent, focal, and ground-band groups
- **THEN** each sublayer targets the appropriate classified groups, and a layout missing a category simply omits that sublayer

#### Scenario: The brief still steers the ring
- **WHEN** a section's brief sets pulse groups
- **THEN** those seed the metric ring instead of the layout default

#### Scenario: Safety gate — the current layout is byte-stable
- **WHEN** the manifest is absent, or the loaded manifest describes the current hardcoded layout
- **THEN** the vocabulary SHALL equal today's `DEFAULT_VOCAB` constants and the golden pipeline fixture output SHALL remain byte-identical (no manifest means `DEFAULT_VOCAB`; the derivation must reproduce today's constants from the real-layout manifest before shipping as the default)

#### Scenario: A different prop mix derives a different anchor
- **WHEN** a manifest describes a layout without arches but with canes and mini trees
- **THEN** the derived metric ring ranks the present rhythm families (canes, minis) into the ring by count/spread/node budget, so the beat anchor is chosen by ranking rather than by a hardcoded tuple order
