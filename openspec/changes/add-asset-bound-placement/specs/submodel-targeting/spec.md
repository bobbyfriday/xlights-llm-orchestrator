## ADDED Requirements

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
