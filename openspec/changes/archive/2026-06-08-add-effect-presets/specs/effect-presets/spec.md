## ADDED Requirements

### Requirement: Mine presets only from the curated source corpus
The system SHALL build the preset library only from community-authored source sequences, and SHALL exclude sequences produced by prior automated tooling and redundant backup snapshots.

#### Scenario: Community sequences are mined
- **WHEN** the extractor runs over the source corpus
- **THEN** it includes only community-authored sequences (those not authored by the prior auto-sequencer) and ignores backup-snapshot copies

#### Scenario: Prior tool output is excluded
- **WHEN** a source sequence was authored by the prior auto-sequencer
- **THEN** it is excluded from mining and contributes nothing to the catalog

### Requirement: Two independent axes — looks and palettes
The system SHALL represent the library as two independent catalogs — looks (effect motion/shape) and palettes (color) — such that any look can be combined with any palette and both remain well-formed.

#### Scenario: Recolor by swapping palette
- **WHEN** a caller pairs a look with any palette from the catalog
- **THEN** the combination is a well-formed effect specification, with color determined solely by the palette

#### Scenario: Color lives only in palettes
- **WHEN** a look's settings are inspected
- **THEN** they contain no color definition; color is carried only by palette strings

### Requirement: Looks are parameterized into typed knobs
For each effect type, the system SHALL group mined settings by their structural signature (the set of keys present) and represent each group as a look comprising a frozen base (keys whose value is constant across the group) and a set of knobs (keys whose value varies). Each knob SHALL be typed from its key (slider, choice, checkbox, text, value-curve, or other), and SHALL record the values observed in the corpus and a default (the most frequently observed value).

#### Scenario: Frozen vs knob separation
- **WHEN** a look is built from a group of mined settings
- **THEN** keys constant across the group are frozen, and keys that vary are exposed as knobs

#### Scenario: Knob typing and observations
- **WHEN** a knob is exposed
- **THEN** it carries its control type, the values observed in the corpus (as a range for numeric sliders or an option set otherwise), and a default value

#### Scenario: Default-only assembly reproduces a real look
- **WHEN** a look is assembled with every knob left at its default
- **THEN** the result is a well-formed settings string for that effect type

### Requirement: Emitted values are constrained to what the corpus proved
The system SHALL assemble a settings string from a look plus chosen knob values, and SHALL constrain every value: a numeric slider value MUST lie within the range observed for that knob; a choice, checkbox, text, value-curve, or otherwise-typed value MUST be one of the values observed for that knob. The system SHALL NOT synthesize value-curve content.

#### Scenario: In-range slider value accepted
- **WHEN** a caller sets a slider knob to a value within its observed range
- **THEN** the value is accepted and included in the assembled settings

#### Scenario: Out-of-range or unobserved value rejected
- **WHEN** a caller sets a slider outside its observed range, or sets a categorical knob to a value never observed
- **THEN** the system rejects the value rather than emitting it

#### Scenario: Value-curves are not synthesized in this version
- **WHEN** a value-curve knob is set
- **THEN** the value must be one observed verbatim in the corpus; no new curve is generated in this version

### Requirement: Value curves are parsed, classified, and overridable
The system SHALL parse a value-curve knob value into its structured components (active flag, curve type, min/max, shape parameters, and any explicit point list) and SHALL classify it as parametric (a closed-form shape such as Ramp or Sine), custom (an explicit point list), or timing-track-dependent. The system SHALL keep value-curve knob values overridable by callers, so that later parametric synthesis and externally supplied (e.g. audio-derived) curves can be substituted without changing the catalog.

#### Scenario: Parsed into structured form
- **WHEN** a mined value-curve value is recorded
- **THEN** it is stored in structured form (active, type, min/max, parameters, point list) and tagged with its classification

#### Scenario: Override a value curve
- **WHEN** a caller assembles a look and supplies a replacement value for a value-curve knob
- **THEN** the system uses the supplied value in place of the observed one

### Requirement: Exclude timing-track-dependent value curves
The system SHALL treat value curves that reference a timing track (timing-track-fade curves) as asset-dependent, since the referenced track may not exist in a target sequence, and SHALL exclude or flag them as unusable rather than emit them blindly.

#### Scenario: Timing-track-fade curve is excluded
- **WHEN** a mined value curve is of a timing-track-fade type
- **THEN** it is excluded from the emittable catalog (or flagged unusable), not offered as a reusable value

### Requirement: Lossless extraction and assembly
The system SHALL parse and reassemble settings without data loss: any settings string from the corpus, decomposed into its keys and values and reassembled, SHALL be equivalent to the source (same keys and values).

#### Scenario: Round-trip a source string
- **WHEN** a corpus settings string is decomposed and then reassembled with its original values
- **THEN** the reassembled string carries the same keys and values as the source

#### Scenario: Default (empty) settings are handled
- **WHEN** a mined effect has empty/default settings (no keys)
- **THEN** it is represented as a valid look with no knobs, not an error

### Requirement: Deduplicate and tag palettes
The system SHALL deduplicate palettes by their set of colors and SHALL tag each with mechanical descriptors (such as warmth, color count, and whether it is monochrome).

#### Scenario: Palette dedup by color set
- **WHEN** multiple source palettes contain the same set of colors
- **THEN** the catalog exposes a single palette for them

#### Scenario: Mechanical tags present
- **WHEN** a palette is exposed
- **THEN** it carries mechanical tags (e.g. warm/cool, color count, monochrome)

### Requirement: Exclude asset-bound effect types
The system SHALL exclude effect types whose settings reference external resources not guaranteed to exist in a target sequence — specifically Faces, Pictures, Video, Shader, and DMX — from the mined catalog.

#### Scenario: Asset-bound type is omitted
- **WHEN** the extractor encounters a placed effect of an asset-bound type (Faces, Pictures, Video, Shader, DMX)
- **THEN** it is not added to the catalog

#### Scenario: Self-contained type is included
- **WHEN** the extractor encounters a self-contained generative effect type (e.g. SingleStrand, Spirals, Bars, On)
- **THEN** its looks are eligible for the catalog

### Requirement: Provenance metadata on looks
The system SHALL record provenance on each look, including the source xLights version(s) it was mined from, so that consumers can reason about version drift and compatibility.

#### Scenario: Look carries provenance
- **WHEN** a look is exposed
- **THEN** it includes the effect type and the source xLights version(s) it was mined from

### Requirement: Catalog lookup API
The system SHALL provide a lookup interface that lets a consumer enumerate the available effect types, retrieve the looks (with their knobs) for a given effect type optionally filtered, and retrieve palettes optionally filtered.

#### Scenario: List effect types
- **WHEN** a consumer requests the available effect types
- **THEN** the system returns the effect types present in the catalog (asset-bound types excluded)

#### Scenario: Get looks for a type
- **WHEN** a consumer requests looks for a given effect type
- **THEN** the system returns that type's looks, each with its knobs (type, observations, default)

#### Scenario: Get palettes
- **WHEN** a consumer requests palettes, optionally filtered by tag
- **THEN** the system returns matching palettes from the catalog
