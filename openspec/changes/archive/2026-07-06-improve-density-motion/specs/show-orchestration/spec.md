## MODIFIED Requirements

### Requirement: Cell density is bounded and scales with intensity
The number of woven cells per section SHALL be bounded by a measurement-tuned budget that scales with section intensity and length, with even downsampling when recipes exceed it, so quiet sections weave sparsely and peaks approach community density without unbounded placement counts. The budget dials (`cell_budget`, `BUDGET_BASE`, `BUDGET_SCALE`) SHALL be set against a committed re-measurement of the density/motion gap and cite it, rather than by judgment, and the peak density target SHALL be expressed in prop-row-equivalent terms (raw group-row density × per-group expansion) so a group-row architecture is not tuned to a per-prop-row goalpost.

#### Scenario: Quiet vs peak density
- **WHEN** two equal-length sections weave the same recipes at intensity 0.2 and 1.0
- **THEN** the quiet section expands materially fewer cells than the peak section, and both stay within their budgets

#### Scenario: Budget dials cite the measurement
- **WHEN** a cell-budget dial (`BUDGET_BASE`/`BUDGET_SCALE`) is changed
- **THEN** its value is justified by, and its comment cites, the committed 2026-07 re-measurement of the fabric gap (not a judgment call), and the peak target is stated as a prop-row-equivalent density band (~2× community typical)

### Requirement: Motion-effect share is surfaced to QA as an advisory
The placement-rules QA SHALL surface, per energetic section, an advisory finding when the share of continuous-motion effects among that section's placements falls below a measurement-derived threshold (`MOTION_SHARE_MIN`), visible to the Judge but never gating the objective score. The threshold SHALL be evaluated only on energetic sections (intensity ≥ `MOTION_SHARE_INTENSITY`), SHALL exempt deliberately quiet/`rest`/`gesture` sections, and its value and comment SHALL cite the committed re-measurement rather than being set by judgment. The advisory floor SHALL be raised to the re-measured target only after the generator clears it, so the Judge is not spammed before the fabric can satisfy it.

#### Scenario: Static section flagged
- **WHEN** an intensity ≥ 0.5 section's placements are predominantly static/punctuation effects
- **THEN** the QA report contains an advisory motion-share finding scoped to that section, and the objective score is unchanged by it

#### Scenario: The floor cites the measurement
- **WHEN** `MOTION_SHARE_MIN` is changed
- **THEN** its new value is the re-measured energetic-section target and its comment cites the 2026-07 re-measurement, and the raise lands only after the generated shows already clear it

#### Scenario: A deliberately quiet section is not flagged
- **WHEN** a low-intensity or rest/gesture section is predominantly static by design
- **THEN** no motion-share advisory is emitted for it (the intensity gate and treatment exemption keep deliberate stillness from reading as a fabric regression)
