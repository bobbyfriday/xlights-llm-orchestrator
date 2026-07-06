## MODIFIED Requirements

### Requirement: Critique rendered frames into scoped findings
The system SHALL critique the rendered show into scoped findings using a tiered strategy that spends the cheapest sufficient resource first: free deterministic rendered-pixel metrics on every iteration, a cheap contact-sheet critique on a worker-tier model for only the sections that changed or were flagged, and the full still-plus-clip critique on the pro-tier model only as a rare escalation.

Each tier SHALL, given the show's creative intent, return scoped findings (naming the affected section/area and a concrete issue/fix). The cheap contact-sheet tier SHALL tile several beat-aligned frames of a section into one downscaled montage and omit the sequencing/layering guides from its prompt while retaining the per-section musical context. The pro-tier escalation SHALL fire only on tier disagreement, repeated churn of a section, or a once-per-run whole-show final gate, and that final gate SHALL run on the real xLights render when a media-attached export is possible.

#### Scenario: Visual findings
- **WHEN** rendered frames and the show intent are given to the visual critic
- **THEN** it returns findings that identify visual problems (e.g. dark/empty areas, poor coverage, monotony) scoped to where they occur

#### Scenario: Frames sampled across the show
- **WHEN** frames are selected for critique
- **THEN** they represent multiple sections of the show (not a single moment)

#### Scenario: Only changed or flagged sections are critiqued
- **WHEN** an iteration follows a section-scoped regeneration
- **THEN** the contact-sheet critique is run only on sections whose instructions changed since their last critique or that the deterministic metrics flagged, and unchanged, unflagged sections are not re-critiqued

#### Scenario: Pro-tier critique is a rare escalation
- **WHEN** the deterministic metrics and the cheap critique agree and no section is churning
- **THEN** the pro-tier still-plus-clip critique is not invoked for that iteration, and it is invoked at most once per run as a whole-show final gate on the real render when exportable

## ADDED Requirements

### Requirement: Deterministic rendered-pixel metrics from the compiled render data
The system SHALL compute deterministic per-section, per-group metrics directly from the compiled render data and the node-to-group mapping, with no LLM and no running xLights, covering coverage (lit fraction over the section), motion (frame-to-frame change), music-sync (brightness change correlated to the beat grid), palette adherence and distinctness, and section-signature similarity for repeated material.

These metrics SHALL read channel values (not the projected preview image), so the metric layer requires only file paths and never a live client; when the render data or group mapping is unavailable or unreadable the metrics SHALL be neutral (produce nothing) rather than fail or gate blind.

#### Scenario: Metrics computed from channel data
- **WHEN** the compiled render data and the node-to-group mapping are available
- **THEN** the system produces per-section coverage, motion, sync, color, and section-signature metrics without invoking an LLM or contacting xLights

#### Scenario: Group attribution on motion and coverage
- **WHEN** a section is static or dark during a high-energy moment
- **THEN** the metric names the specific group(s) responsible

#### Scenario: Missing render data is neutral
- **WHEN** the compiled render data cannot be read or the group mapping is empty
- **THEN** the metrics produce no findings and no subscores, leaving the evaluation unchanged
