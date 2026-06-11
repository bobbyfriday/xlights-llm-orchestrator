## ADDED Requirements

### Requirement: Extract core musical features from an audio file
The system SHALL analyze an audio file and return a structured `SongAnalysis` containing tempo, a beat grid (including downbeats/bars), key/mode, a chord progression, structural sections, an energy arc over time, an onset track, and harmonic-change points.

#### Scenario: Analyze a song
- **WHEN** a caller analyzes a music file
- **THEN** the system returns a `SongAnalysis` populated with tempo, beat grid, key, chords, sections, energy arc, onsets, and harmonic-change points

#### Scenario: Plausible tempo and beats
- **WHEN** a song with a steady beat is analyzed
- **THEN** the reported tempo is within a sensible musical range and the beat grid is non-empty and ordered in time

#### Scenario: Sections detected
- **WHEN** a multi-part song is analyzed
- **THEN** at least one structural section with start/end times is returned

### Requirement: Measurements only, not interpretation
The system SHALL output objective measurements; it SHALL NOT label sections (verse/chorus), name themes, or assign moods — that interpretation is performed later by other components.

#### Scenario: No semantic labels
- **WHEN** sections are returned
- **THEN** they carry timing and algorithmic structure identifiers (e.g. segment "A"/"B") but no human/interpretive labels like "chorus", "verse", or a mood

### Requirement: Feature confidence where available
The system SHALL annotate a feature with a confidence where the underlying analysis provides one, and SHALL NOT fabricate confidence values where none is available.

#### Scenario: Confidence reported when provided
- **WHEN** an analysis step provides a confidence (e.g. key detection)
- **THEN** that confidence is included with the feature

#### Scenario: No fabricated confidence
- **WHEN** an analysis step provides no confidence
- **THEN** the feature is returned without a fabricated confidence value

### Requirement: Required analysis plugins
The system SHALL require its core analysis plugins (the QM VAMP set, NNLS Chroma / Chordino, and a structural segmenter). If a required plugin is unavailable, the system SHALL fail with a clear error naming the missing plugin(s) — it SHALL NOT silently skip the feature or fall back to a degraded analysis.

#### Scenario: Required plugin missing
- **WHEN** a required analysis plugin is not available
- **THEN** the system raises a clear error identifying the missing plugin(s), rather than returning a partial result

#### Scenario: All plugins present
- **WHEN** all required plugins are available
- **THEN** the analysis runs and produces the full core feature set

### Requirement: Cache analyses by audio content
The system SHALL cache analysis results keyed by the audio file's content, so repeating an analysis of the same audio reuses the cached result rather than recomputing.

#### Scenario: Cache hit on identical audio
- **WHEN** the same audio content is analyzed a second time
- **THEN** the system returns the cached `SongAnalysis` without recomputing

#### Scenario: Cache miss on changed audio
- **WHEN** different audio content is analyzed
- **THEN** the system computes a fresh analysis

### Requirement: Stable schema with room for later enrichment
The `SongAnalysis` schema SHALL include optional, currently-unpopulated fields for later enrichment (per-stem energies, mood/genre descriptors, track identification, timed lyrics) so that adding those extractors later does not change the established contract.

#### Scenario: Optional enrichment fields absent but valid
- **WHEN** a core analysis is produced without the enrichment extractors
- **THEN** the enrichment fields are absent/empty and the `SongAnalysis` is still valid

### Requirement: Expose analysis via MCP
The system SHALL expose analysis to MCP clients: a tool to analyze a song file and a tool to report the available analysis plugins.

#### Scenario: Analyze via tool
- **WHEN** an MCP client calls the analyze tool with a valid audio path
- **THEN** it receives the structured `SongAnalysis`

#### Scenario: List plugins
- **WHEN** an MCP client requests the available analysis plugins
- **THEN** the system reports which VAMP plugins were discovered
