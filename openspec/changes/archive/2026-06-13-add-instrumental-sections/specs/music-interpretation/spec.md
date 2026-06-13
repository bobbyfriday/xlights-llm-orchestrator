## ADDED Requirements

### Requirement: Instrumental songs' long sections subdivide at musical seams
WHEN a song's analysis carries no timed lyric lines (the lyric-marker refiner's complement) and any audio segment exceeds the maximum section length (~32s), that segment SHALL be subdivided into pieces between the minimum (~12s) and maximum length, cut at beat-snapped candidate seams — harmonic-change points preferred, energy-delta peaks as fallback, the beat nearest the window limit as last resort — labeled by the parent segment id plus an ordinal (e.g. "A" → "A1","A2"). Segments already within the maximum SHALL pass through untouched, the refinement SHALL be idempotent, and timed-lyric songs SHALL be unaffected.

#### Scenario: Coarse instrumental segments become bounded sub-sections
- **WHEN** an instrumental song's audio segmentation yields 60–75s segments and the analysis carries harmonic-change points and a beat grid
- **THEN** each long segment is split at beat-snapped harmonic changes into pieces no longer than the maximum and (apart from unavoidable pre-existing slivers) no shorter than the minimum, labeled A1/A2/... under the parent, and downstream interpretation/design plans one section per piece

#### Scenario: Graceful degradation of cut candidates
- **WHEN** the analysis lacks harmonic changes, energy data, or beats
- **THEN** cuts fall back in order to energy-delta peaks, then pure time-based placement, and are left unsnapped only when no beat grid exists — never producing a piece over the maximum length

#### Scenario: Lyric songs and short instrumentals unchanged
- **WHEN** a song has timed lyric lines, or every audio segment already fits the maximum section length
- **THEN** the segments are untouched and the pipeline behaves exactly as before

#### Scenario: Sub-segments are one evolving part to the analysts
- **WHEN** the structure analyst receives numbered sub-segments (e.g. A1/A2)
- **THEN** it treats them as beat-snapped subdivisions of one musical part — related but evolving looks, boundaries kept, not re-derived
