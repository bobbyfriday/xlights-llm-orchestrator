## ADDED Requirements

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
