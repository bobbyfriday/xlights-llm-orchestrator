## MODIFIED Requirements

### Requirement: Chord and lyric tracks when data exists
Chord and lyric timing tracks SHALL be added when that data is available, and omitted otherwise; for vocal songs the lyric data SHALL additionally be written as a Papagayo-style multi-layer "Lyric Phonemes" track (phrases, words, and phonemes) alongside the existing line-granular Lyrics track.
The multi-layer track is expressed by extending `TimingTrack` with optional per-layer marks so `patch_xsq_timing_tracks` emits one `<EffectLayer>` per layer; single-layer tracks are unchanged (back-compat by default). Its three layers are the aligned phrases (reusing the existing lyric-track marks), the per-word spans, and the phoneme marks derived from those word spans. The track inherits the idempotent same-named replace and atomic write of the existing patcher, and its name ("Lyric Phonemes") is distinctive to avoid colliding with a user's own tracks.

#### Scenario: Instrumental song
- **WHEN** there are no timed lyrics
- **THEN** no lyric track is added (and a chord track is added only if chords were analyzed), and no "Lyric Phonemes" track is added

#### Scenario: Vocal song gets a three-layer phoneme track
- **WHEN** a vocal song with aligned per-word lyric spans is finalized
- **THEN** the `.xsq` contains a "Lyric Phonemes" timing track with three `<EffectLayer>`s — phrases, words, and phonemes — whose marks round-trip the XML parser

#### Scenario: Re-finalize is idempotent
- **WHEN** the timing tracks are patched again for the same sequence
- **THEN** the existing same-named "Lyric Phonemes" track is replaced rather than duplicated, and the write is atomic
