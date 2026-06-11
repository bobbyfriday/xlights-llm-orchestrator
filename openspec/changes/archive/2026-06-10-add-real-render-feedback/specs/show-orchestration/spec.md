## ADDED Requirements

### Requirement: Visual judgments use the real render when available
When the open sequence has media attached, the refine loop SHALL export the real render and use it for the visual critique and the coverage metric.

#### Scenario: Media-attached sequence
- **WHEN** the loop evaluates and the open sequence has media
- **THEN** the coverage frames and critic clips come from the real export

### Requirement: Export is guarded and fail-safe
The export SHALL only be attempted on media-attached sequences, and any export failure SHALL fall back to the offline approximation (and then to neutral) without failing the run.

#### Scenario: No media / export failure
- **WHEN** the sequence has no media or the export fails
- **THEN** the offline renderer is used (or coverage stays neutral) and the run continues

### Requirement: Real-render timing is offset-corrected
Frames and clips taken from the export SHALL account for the export's lead-in offset so song-time maps to the right video-time.

#### Scenario: Lead-in
- **WHEN** the export is longer than the song
- **THEN** sampling at song-time t reads the frame at t + lead-in
