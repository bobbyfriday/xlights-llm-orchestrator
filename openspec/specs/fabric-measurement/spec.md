# fabric-measurement Specification

## Purpose
TBD - created by archiving change improve-density-motion. Update Purpose after archive.
## Requirements
### Requirement: A show's effect fabric is measurable into comparable stats

The system SHALL compute a comparable set of effect-fabric statistics from a show, so a generated show and a hand-sequenced community show can be compared on the same axes. The statistics SHALL include effects per minute, share by effect family (motion / punctuation / bed / feature / other), share by effect type, median duration by type, the share of rows carrying a blend mode and a transition, the value-curve kinds used (brightness vs motion parameters), and the layer-depth histogram, produced identically whether the input is an instructions cache/hermetic fixture or a finalized `.xsq`.

#### Scenario: Stats from an instructions list

- **WHEN** the measurement is run over a list of effect-instruction dumps with a song duration
- **THEN** it returns the fabric statistics (effects/min, family/type shares, median durations, blend/transition/value-curve usage, layer-depth histogram) derived purely from those instructions

#### Scenario: Stats from a finalized .xsq

- **WHEN** the measurement is run over an `.xsq` file (a community show or our own finalized output)
- **THEN** it parses the sequence's effect elements and returns the same statistics shape as for an instructions list, so the two are directly comparable

#### Scenario: The comparison runs without the community corpus

- **WHEN** the original community `.xsq` corpus is not available on the machine
- **THEN** the measurement still produces the comparison using frozen community aggregates baked into the tool, without failing

### Requirement: Density is normalized to prop-row equivalents

The measurement SHALL report a prop-row-equivalent density in addition to the raw effects-per-minute, so a group-row architecture (one effect animating a whole SEM_ group) is compared fairly against per-prop-row community sequences. The tool SHALL derive a per-group expansion factor from the layout's model groups and multiply group-targeted rows by it.

#### Scenario: Group-targeted density is scaled up

- **WHEN** a section's effects target SEM_ groups whose mean member count is known
- **THEN** the report shows both the raw effects/min and a prop-row-equivalent effects/min equal to the raw group-row density times the mean group member count

#### Scenario: Expansion is unavailable

- **WHEN** the layout's model-group membership cannot be resolved
- **THEN** the prop-row-equivalent value is reported as absent (null) and the raw effects/min is still reported

### Requirement: Fabric stats are reported per section and energy-bucketed

The measurement SHALL report every statistic per song section, tagged with that section's intensity (and, when present, its treatment), so a single whole-show number never hides the intended quiet-vs-peak contrast. The per-section aggregation SHALL be reusable by the QA musicality metrics rather than re-derived.

#### Scenario: Per-section breakdown distinguishes quiet from peak

- **WHEN** a show with both quiet and peak sections is measured
- **THEN** the report lists each section's effects/min and motion share alongside its intensity, so the peak's density is not averaged away by the quiet sections

#### Scenario: Deliberately sparse sections are labeled, not penalized

- **WHEN** a section is a rest/gesture (deliberately still) section
- **THEN** it appears in the per-section report with its treatment, and the density targets are evaluated only on energetic (full/feature) sections so its sparseness is not counted as a gap

