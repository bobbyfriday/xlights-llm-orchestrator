## ADDED Requirements

### Requirement: Long sections are subdivided regardless of lyrics
No song section SHALL exceed the long-section cap. A segment longer than the cap SHALL be subdivided at the music's own seams (harmonic-change points, then energy-delta peaks, then beat-snapped time), with pieces labeled from the parent (id + ordinal). This SHALL apply whether or not the song has timed lyrics, so a long instrumental span in a lyric song (e.g. a long intro before the first sung line) is broken up rather than left as one oversized section.

#### Scenario: A lyric song's long instrumental intro is split
- **WHEN** a song has lyrics but a long instrumental stretch with no lyric markers (longer than the cap)
- **THEN** that stretch is subdivided into sections no longer than the cap, cut at musical seams, labeled from the parent

#### Scenario: Sections within the cap are untouched
- **WHEN** all sections already fit within the cap
- **THEN** the segmentation is unchanged (no-op, idempotent)

#### Scenario: Instrumental songs are unaffected by the change
- **WHEN** a song has no lyrics
- **THEN** long sections are capped exactly as before
