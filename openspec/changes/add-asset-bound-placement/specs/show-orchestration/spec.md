## MODIFIED Requirements

### Requirement: Place effects without removing any
The system SHALL place generated effects additively — on prop groups, on distinct layers and/or non-overlapping time ranges — and SHALL NOT depend on removing or replacing existing effects (the automation API cannot remove effects). When an instruction carries a non-empty `direct_settings` payload (a code-templated asset-bound effect), the emitter SHALL place it via the direct path (`place_direct`) instead of the preset library, with identical layer accounting and identical skip-on-failure behavior to the preset branch, so a failed direct placement degrades to a logged skip rather than aborting the run.

#### Scenario: Additive placement
- **WHEN** multiple effects are placed
- **THEN** they are arranged so none requires deleting another (distinct layers and/or non-overlapping times)

#### Scenario: Skip effects xLights will not place
- **WHEN** an effect type or instruction is not accepted by xLights (reported as not placed)
- **THEN** the system skips it and continues, rather than aborting the run

#### Scenario: A direct-settings instruction bypasses the preset library
- **WHEN** an `EffectInstruction` has a non-empty `direct_settings` string (default `""`)
- **THEN** the emitter places it via `place_direct` with the same layer accounting and skip-on-failure handling as the preset branch, still carrying the injected `B_CHOICE_BufferStyle`, and never touches the preset library for that instruction

#### Scenario: Cached and golden fixtures are unperturbed
- **WHEN** a pre-change cached instruction list (no `direct_settings` key) or the golden fixture is loaded
- **THEN** every instruction defaults `direct_settings` to `""`, takes the preset branch exactly as today, and the golden comparison is unchanged (nothing emits direct instructions yet)

### Requirement: Semantic role/ensemble groups exist in the layout
The layout SHALL contain semantic groups (`SEM_*`) derived from each model's role, spatial band/side, sweep order, and ensemble membership, generated from `rgbeffects.xml`. When a model carries submodels, the layout SHALL ALSO contain submodel-membered groups whose members are `Parent/SubModel` references — `SEM_OUTLINE_SEGMENTS` (OUTLINE segments, left-to-right), `SEM_TREE_ZONES` (MEGA_TREE rings/zones, bottom-to-top), per-zone singletons `SEM_TREE_ZONE_<i>`, `SEM_TREE_TOPPER`, and `SEM_WINDOW_CELLS` — emitted only for kinds with a choreography contract; a layout with zero submodels SHALL produce zero such groups (byte-identical to today). Submodel groups SHALL NOT join `SEM_ALL` or the band/side ensembles (their parents already are), and SHALL slot into the `canonical_order` accent/rhythm tiers so zone accents win overlaps against the parent's bed.

#### Scenario: Role and ensemble groups
- **WHEN** the layout is processed
- **THEN** role groups (e.g. `SEM_ARCHES`), band/side groups, ordered `_LTR` groups, and ensemble groups (`SEM_ALL`, `SEM_FOCAL`, `SEM_ACCENTS`, `SEM_HOUSE`, `SEM_YARD`) are present

#### Scenario: Submodel-bearing layout gains ordered and singleton groups
- **WHEN** a layout has OUTLINE segments, MEGA_TREE rings/zones, a topper, and window cells
- **THEN** `SEM_OUTLINE_SEGMENTS` (ordered left-to-right), `SEM_TREE_ZONES` (ordered bottom-to-top), per-zone singleton `SEM_TREE_ZONE_<i>`, `SEM_TREE_TOPPER`, and `SEM_WINDOW_CELLS` groups are emitted with `Parent/SubModel` members, and the singletons are excluded from ensemble beds

#### Scenario: Zero-submodel layout is unchanged
- **WHEN** the current real layout (0 submodels) is processed
- **THEN** no submodel groups are emitted and the `SEM_*` output is byte-identical to today (the permanent conditionality guard)

### Requirement: An accent on about every beat, bounded
An accent SHALL be placed on approximately every beat of a section (not heavily downsampled), with an
upper bound so a long section cannot place an unbounded number of effects. The per-beat accents SHALL
form a METER BACKBONE: each beat of the bar lights a DISTINCT rhythm group drawn in a fixed order from
a metric ring of groups (e.g. in 4/4 the four beats light four different prop-family groups in turn),
so the bar's meter is visible as a walk across the props. The ring SHALL honor the section's real
beats-per-bar (the beat index modulo the ring length selects the group), and SHALL be seeded by the
brief's pulse groups when set, else derived from the layout's rhythm groups. Each accent is a discrete
pulse on a whole group (per-model render), not a within-group buffer chase. WHEN the section's follow
stem is drums and the layout provides submodel tree zones, the accent placement SHALL map beat-grid
structure onto those zones — downbeats to the bottom zone, backbeat positions to the mid zone, and the
strongest-hit sparkle layer to the topper — using only beat-grid structure (no new per-drum audio
analysis); WHEN no zones are provided the accent output SHALL be byte-identical to today.

#### Scenario: Normal section
- **WHEN** a section has ~32 beats
- **THEN** roughly that many accents are placed (not capped to a small fraction)

#### Scenario: Each beat lights a distinct group in order
- **WHEN** consecutive beats of a bar are accented and the metric ring has at least as many groups as beats per bar
- **THEN** beat 1 lights the first ring group, beat 2 the second, and so on, so the pulse walks across distinct prop-family groups rather than all groups firing together

#### Scenario: The ring honors the meter and wraps
- **WHEN** the section's beats-per-bar differs from the ring length (a non-4/4 meter, or fewer rhythm groups than beats)
- **THEN** the beat-to-group mapping uses the beat index modulo the ring length (it wraps), and never errors for a short ring

#### Scenario: Very long section
- **WHEN** a section has far more beats than the upper bound
- **THEN** the accents are bounded to the upper limit

#### Scenario: Drum section maps to tree zones
- **WHEN** a drums-prominent section is realized on a layout with `SEM_TREE_ZONES` singletons and a topper
- **THEN** downbeats fire the bottom zone, backbeat positions fire the mid zone, and the strongest-hit sparkle fires the topper — a zone-differentiated drum kit driven by beat-grid structure alone

#### Scenario: No zones, no change
- **WHEN** a section is realized on a layout with no submodel tree zones
- **THEN** `select_rhythm_groups` and the accent output are byte-identical to today (the golden pipeline snapshot is unchanged)

## ADDED Requirements

### Requirement: Instructions can carry a code-templated direct-settings payload
An `EffectInstruction` SHALL carry an optional `direct_settings: str` field (default `""`) holding a full settings string built by the code-owned direct builders; when non-empty the emitter places the effect via the direct path and the `look_id` MAY be empty. The field SHALL NOT be surfaced in any generator prompt — only deterministic passes populate it — and QA SHALL treat a direct-settings instruction like any other placement (a real target, effect type, and time span), with the energy-band rule simply having no entry for the asset-bound types (unconstrained by construction).

#### Scenario: Direct payload routes placement
- **WHEN** an instruction sets `direct_settings` to a validated builder string and leaves `look_id` empty
- **THEN** the emitter places it via the direct path and does not require a mined look

#### Scenario: The generator is never offered the field
- **WHEN** the generator LLM composes a section
- **THEN** `direct_settings` is absent from its prompt and schema, so the LLM cannot populate it; only deterministic passes do

#### Scenario: QA treats it as an ordinary placement
- **WHEN** QA evaluates a section containing a direct-settings instruction
- **THEN** it is scored on its real target/effect-type/span, and the energy-band rule leaves it unconstrained (no entry for the asset-bound type)

### Requirement: Submodels are discovered, ordered, and preserved during classification
The layout classifier SHALL parse each model's `<subModel>` children into `SubModel` records — name, parent model, raw node ranges, expanded node count, a derived kind (RING, ZONE, HALF, SEGMENT, ARM, TOPPER, or unknown), and an order hint — attached to the parent prop, deriving segment order left-to-right for SEGMENT/HALF kinds (by mean world-x) and bottom-to-top for RING/ZONE kinds (by mean world-y or the order hint). Roles SHALL be inherited from the parent (a submodel of an OUTLINE model is an outline segment; a RING of a MEGA_TREE is a tree zone) and submodels SHALL NOT receive independent taxonomy roles. Submodel types the parser does not understand SHALL be preserved verbatim and excluded from planning. The manifest SHALL carry the submodel records and submodel-group records within its size budget.

#### Scenario: Submodels parse with kind and order
- **WHEN** the classifier processes a model with named submodels (e.g. "Ring 1".."Ring 4", "Roof_Left", "Peak")
- **THEN** each becomes a `SubModel` record with the correct expanded node count, inherited kind, and derived order, attached to its parent prop

#### Scenario: Unknown submodel types are preserved
- **WHEN** a submodel uses a sub-buffer or otherwise unrecognized definition
- **THEN** it is preserved verbatim in the file, excluded from group planning, and surfaced in the manifest review rather than mis-parsed

#### Scenario: Zero submodels yields no records
- **WHEN** a model has no `<subModel>` children
- **THEN** its submodel list is empty and no submodel groups or records are produced

### Requirement: Submodel groups are targeted via probe-verified model groups
The pipeline SHALL target submodels through Route B — ordinary model groups whose members are submodels — so that no client change is needed and the existing empirical targetability probe answers whether xLights accepts effects on a submodel-membered group per layout, cached by fingerprint. Route A (a direct submodel-element target) SHALL remain a recorded live experiment, not on the critical path, and any submodel-targeting behavior SHALL be gated behind a live-verification pass before defaulting on. All submodel choreography hooks SHALL be guarded so layouts without submodels are unaffected.

#### Scenario: A submodel group is an ordinary target
- **WHEN** a `SEM_TREE_ZONES` group with `Parent/SubModel` members exists and is probed
- **THEN** it flows through `get_group_names`, `targetable_groups`, placement, the emitter, QA, and render order like any other group, with no client changes

#### Scenario: Targetability is decided by the probe
- **WHEN** the layout is onboarded and the submodel groups are probed on a disposable sequence
- **THEN** the probe records per layout whether xLights accepts effects on them, and nothing downstream assumes success (all hooks are guarded)

#### Scenario: Submodel behavior is gated on live verification
- **WHEN** the submodel path is built but not yet hardware-verified
- **THEN** it stays behind the `--submodels` flag and defaults on only after group-load, probe, and human-watch checks pass on real hardware
