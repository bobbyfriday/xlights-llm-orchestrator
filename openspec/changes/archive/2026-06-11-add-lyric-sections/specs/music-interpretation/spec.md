## ADDED Requirements

### Requirement: Song structure derives from timed lyric section markers when available
WHEN the fetched lyrics carry section markers (e.g. Verse/Pre-Chorus/Chorus) and alignment yields timed positions for at least two of them, the analysis SHALL rebuild its structural segments from those markers — boundaries snapped to the beat grid, sections below a minimum length merged, segments labeled by the markers — with an intro segment before the first marker and an outro segment after the last sung line. The audio segmentation SHALL remain the fallback when markers are absent and SHALL in-fill boundaries inside long instrumental spans between markers.

#### Scenario: Marker-rich song gets lyric-aligned sections
- **WHEN** a song's Genius lyrics contain Verse/Pre-Chorus/Chorus/Post-Chorus markers that align against the vocal stem
- **THEN** the analysis segments match the marker boundaries (beat-snapped), carry the marker labels, and downstream interpretation/design plans one section per lyric section instead of one per coarse audio segment

#### Scenario: Instrumental and marker-less songs unchanged
- **WHEN** a song has no lyrics, or its lyrics carry fewer than two timed markers
- **THEN** the audio segmentation is used unchanged and the pipeline behaves exactly as before

#### Scenario: Lyric-labeled segments are ground truth to the analysts
- **WHEN** the structure analyst receives segments carrying lyric-derived labels
- **THEN** the labeled sections keep those labels in the interpretation (judgment is spent on themes and energy, not boundary re-derivation)
