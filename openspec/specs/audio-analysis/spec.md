# audio-analysis Specification

## Purpose
TBD - created by archiving change add-audio-analysis. Update Purpose after archive.
## Requirements
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

### Requirement: Separate the mix into instrument stems
The system SHALL, when stem separation is enabled and available, separate the song into instrument stems (vocals, drums, bass, other) and make them available for measurement and inspection.

#### Scenario: Stems produced
- **WHEN** stem separation is enabled and the dependency/model is available
- **THEN** the analysis yields the four instrument stems

#### Scenario: Stems are inspectable
- **WHEN** stems are produced
- **THEN** the separated stem audio is persisted so it can be listened to / inspected

### Requirement: Measure each stem
The system SHALL compute, per stem, an energy arc and onset times.

#### Scenario: Per-stem features
- **WHEN** stems are produced
- **THEN** each stem carries its own energy arc and onset list

### Requirement: Derive per-section instrument prevalence
The system SHALL aggregate per-stem energy over each analysis section to report, per section, each stem's share and the dominant instrument(s).

#### Scenario: Section instrumentation
- **WHEN** stems are produced and the analysis has sections
- **THEN** each section reports per-stem energy shares and its dominant instrument(s)

### Requirement: Stem analysis is optional and degrades gracefully
The system SHALL treat stem separation as optional: when it is disabled, or its dependency/model is unavailable, or it fails/times out, the analysis SHALL still complete with the existing (full-mix) measurements and simply omit stem data.

#### Scenario: Disabled or unavailable
- **WHEN** stem separation is disabled or its dependency is not installed
- **THEN** the analysis completes normally and reports no stem data

#### Scenario: Failure mid-separation
- **WHEN** stem separation is attempted but fails or times out
- **THEN** the failure is logged and the analysis still returns its full-mix measurements

### Requirement: Stem results are cached
The system SHALL cache the stems and derived stem features keyed by the song's content, so a re-run reuses them instead of re-separating.

#### Scenario: Cached re-run
- **WHEN** the same song is analyzed again with stems enabled
- **THEN** the cached stems/features are reused without re-running separation

### Requirement: Stem separation uses a 6-stem model by default
Stem separation SHALL, by default, separate the audio into six stems — vocals, drums, bass, other, guitar, and piano — so instrument prevalence distinguishes guitar and piano rather than collapsing them into a single "other" bucket.

#### Scenario: Default separation
- **WHEN** stem separation runs with no model override
- **THEN** it produces guitar and piano stems in addition to vocals/drums/bass/other

### Requirement: The separation model is configurable
The system SHALL allow the stem-separation model to be selected (e.g. to fall back to a 4-stem model), defaulting to the 6-stem model.

#### Scenario: Override to 4-stem
- **WHEN** the model is configured to a 4-stem model
- **THEN** separation produces the 4-stem set instead

### Requirement: Separated stems are saved as audio files
The system SHALL save each separated stem as an mp3 audio file so a person can listen to what drives each part of the song.

#### Scenario: Stems written
- **WHEN** separation succeeds and audio export is available
- **THEN** one mp3 per stem is written under the song's analysis output

### Requirement: Saving stems is best-effort
Saving stems SHALL NOT fail the analysis: if audio export is unavailable or errors, the analysis (energy, shares, features) SHALL still complete.

#### Scenario: Export unavailable
- **WHEN** mp3 export cannot run
- **THEN** no stem files are written and the analysis completes normally

### Requirement: Stem separation remains optional and graceful
Stem separation (including the 6-stem model) SHALL remain optional: if no separation backend is available it SHALL be skipped without failing the analysis.

#### Scenario: No backend
- **WHEN** no stem-separation backend is available
- **THEN** analysis continues without stems

### Requirement: Lyrics are timed against the vocal stem
When lyrics text is available, analysis SHALL align it against the separated vocal stem to produce line-level timings (and words where confident).

#### Scenario: Vocal song
- **WHEN** lyrics are fetched and a vocal stem exists
- **THEN** the analysis carries timed lyric lines

#### Scenario: Alignment unavailable
- **WHEN** the aligner or its dependencies are unavailable or fail
- **THEN** analysis completes without timed lyrics (graceful)

### Requirement: Lyric structure hints are extracted
Section markers in the lyrics (when present) and repeated-line clusters SHALL be surfaced as structure hints with times.

#### Scenario: No markers
- **WHEN** the lyrics have no section markers
- **THEN** repeated-line clusters still provide chorus hints

