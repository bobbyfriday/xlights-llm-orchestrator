## ADDED Requirements

### Requirement: Code-owned settings templates for asset-bound effect types
The system SHALL provide a code-owned settings-template module (`knowledge/direct_settings.py`) that builds settings strings from scratch for the asset-bound effect types it serves, defined by an allowlist `DIRECT_TYPES = {"Text", "Faces"}`, so effects whose settings reference resources outside the string can be placed without a mined preset look. Each builder SHALL bind every external reference only to a resource the caller proves exists (its own timing tracks, the layout's own face definitions) and SHALL NOT invent references. The module is the single authority for asset-bound placement; adding a new type to `DIRECT_TYPES` SHALL require a new change.

#### Scenario: Text settings are built from scratch
- **WHEN** `build_text_settings(text, ...)` is called with a glyph string and knob values
- **THEN** it returns a full settings string containing the frozen Text key set (including the mandatory `E_TEXTCTRL_Text`) with no external file reference, using OS font rendering

#### Scenario: Faces settings require verified references
- **WHEN** `build_faces_settings(*, timing_track, face_definition, ...)` is called
- **THEN** it requires both a timing-track name the run writes and a face definition verified present on the target model, performs no defaulting for them, and (until the F-D probe lands) the skeleton raises rather than emitting a dangling reference

#### Scenario: Only allowlisted types are served
- **WHEN** a caller requests a direct settings string for a type not in `DIRECT_TYPES` (e.g. Pictures, Video, Shader, DMX)
- **THEN** no builder exists for it and the system does not synthesize one

### Requirement: Direct settings are frozen from a hand-authored probe
The system SHALL freeze each type's template from a settings string captured out of a hand-authored probe `.xsq` in the pinned xLights version, committed as a fixture, so the string is valid by construction against a real show. The builder SHALL vary only the documented knobs (text, direction, speed, size); a test SHALL assert the builder's output differs from the frozen probe only in those deliberately variable keys.

#### Scenario: The builder varies only documented knobs
- **WHEN** `build_text_settings` is invoked with different text/direction/speed/size values
- **THEN** the resulting string differs from the frozen probe fixture only in those keys, and all other keys match the probe exactly (the "corpus of one" invariant)

#### Scenario: A stale template is caught on upgrade
- **WHEN** xLights is upgraded and a setting key has drifted or been removed
- **THEN** the live validation re-run flags it (via a rejected placement or an `ApplySetting: Unable to find` log) and a `DROP_KEYS`-style strip list removes stale keys

### Requirement: Direct settings are syntactically validated before placement
The system SHALL validate every synthesized settings string syntactically before it reaches xLights: it round-trips through the existing parser (`serialize_settings(parse_settings(s)) == s`), every key classifies to a known kind via `classify_kind` (no `"other"` except the audited font-picker key), and no active timing-track value curve is present unless the builder deliberately bound one. For Faces the timing-track reference is required and its name MUST equal the track the run writes.

#### Scenario: A malformed template fails the round-trip
- **WHEN** a builder produces a settings string that does not round-trip through `parse_settings`/`serialize_settings`
- **THEN** validation rejects it before any placement is attempted

#### Scenario: Glyph text with commas or equals is handled explicitly
- **WHEN** the glyph text contains a comma or equals sign (which would corrupt the CSV `KEY=VALUE` settings string)
- **THEN** the builder strips or substitutes it per a documented, tested decision so the settings string stays well-formed

#### Scenario: A Faces track reference must match a written track
- **WHEN** a Faces settings string is built for a run
- **THEN** its `E_CHOICE_Faces_TimingTrack` value equals a phoneme timing track the pipeline schedules for writing, else reference validation fails

### Requirement: Asset-bound types stay out of the LLM's free-choice menu
The system SHALL keep the asset-bound `DIRECT_TYPES` out of the LLM's placeable vocabulary — a test SHALL assert `DIRECT_TYPES ∩ placeable_effect_types() == ∅` — so the Director and Generator are never offered Text/Faces, and only deterministic passes populate a direct-settings payload. Existing look-based guards SHALL continue to drop any hallucinated asset-bound type.

#### Scenario: The menu never grows these types
- **WHEN** the placeable effect types are computed (even after the catalog is re-mined with different filters)
- **THEN** neither Text nor Faces appears in `placeable_effect_types()`, and the guard test fails if either does

#### Scenario: A hallucinated asset-bound type is dropped
- **WHEN** an LLM emits an effect of a `DIRECT_TYPES` type in a recipe
- **THEN** the existing `candidate_look_ids`-based guards drop or fall back for it exactly as today, since it never enters the direct path (only deterministic passes do)

### Requirement: Pictures, Video, Shader, and DMX are explicitly out of scope
The system SHALL NOT provide a direct placement path for Pictures, Video, Shader, or DMX effect types in this change; these types remain excluded because they need asset acquisition/path rewriting, `.fs` shader files, per-GPU render behavior, or device binding that this pixel-driving pipeline does not support. The design SHALL keep the door open (each future type is one more builder plus its reference ring) but SHALL require a new change to enable one.

#### Scenario: No builder exists for out-of-scope types
- **WHEN** a caller looks for a Pictures/Video/Shader/DMX direct builder
- **THEN** none exists and `DIRECT_TYPES` does not list it
