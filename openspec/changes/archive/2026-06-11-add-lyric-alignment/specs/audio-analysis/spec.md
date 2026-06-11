## ADDED Requirements

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
