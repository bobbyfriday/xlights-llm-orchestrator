## MODIFIED Requirements

### Requirement: A human-readable song description is produced
The system SHALL produce a deterministic, human-readable analysis digest (`analysis_digest.md`) covering the song's duration, tempo and meter, its sections with timing and normalized per-section energy, instrumentation over time (dominant stems per section, detected entrances), rhythm/accents, harmony (key, chord density), and the timed and repeated lyric lines — derived purely from the cached analysis, with no model call. Interpretation of mood, narrative, and structure labels happens in the Claude Code conversation over this digest.

#### Scenario: Digest covers the song
- **WHEN** analysis completes
- **THEN** a readable digest is available that describes each section's time, energy, instruments, and lyrics, not just raw numbers

#### Scenario: Digest is deterministic
- **WHEN** the digest is regenerated from the same cached analysis
- **THEN** it is byte-identical

## REMOVED Requirements

### Requirement: Interpret a song analysis into a MusicBrief
**Reason**: Interpretation is a conversation; the agreed labels and themes are written into the creative brief.
**Migration**: Delete `music_brief.py`; `build_timing_tracks` and `video-plan` read sections from the brief.

### Requirement: Analysts run in parallel
**Reason**: The analyst panel is removed.
**Migration**: Delete `agents/panel.py`.

### Requirement: Synthesize analyst outputs into one brief
**Reason**: The synthesizer is removed.
**Migration**: Delete `agents/synthesizer.py`.

### Requirement: The show planner consumes the MusicBrief
**Reason**: There is no planner agent; Claude reads the digest.
**Migration**: None.

### Requirement: Configurable panel size
**Reason**: The panel is removed.
**Migration**: None.

### Requirement: Interpretation is cache-resumable
**Reason**: There is no interpretation artifact to cache; the digest is cheap and deterministic.
**Migration**: Old `song_description.json` caches are ignored.

### Requirement: Extensible for additional analysts
**Reason**: The panel is removed.
**Migration**: New perspectives are added as digest content or skill guidance.

### Requirement: Human review of the description before proceeding
**Reason**: The description is discussed in conversation; there is no gate to pass.
**Migration**: None.
