## ADDED Requirements

### Requirement: Effects stop when the music stops at the song end

The system SHALL derive, deterministically from the song's energy envelope (`SongAnalysis.energy_arc`),
the song's last non-silent moment (`music_end`) — the latest point whose energy exceeds a silence floor
defined relative to the track's robust peak. No effect in the final span SHALL extend past `music_end`:
every realized effect whose end exceeds `music_end` SHALL be trimmed to `music_end`, and an effect left
with non-positive duration SHALL be dropped. When the track never falls below the silence floor,
`music_end` SHALL equal the audio duration and no effect SHALL be trimmed. `music_end` SHALL be clamped
so it cannot shorten the final section below the minimum section length.

#### Scenario: Trailing silence is not lit

- **WHEN** a song ends with a silent (or sub-floor) tail after its last audible moment
- **THEN** `music_end` is set to that last audible moment and the final span's effects end at
  `music_end`, so the lights are dark through the silent tail instead of holding to the file end

#### Scenario: A song with no silent tail is unchanged

- **WHEN** a song's energy never drops below the silence floor before the file ends
- **THEN** `music_end` equals the audio duration and no effect end time is trimmed

### Requirement: The song tail fades with the music's amplitude decline

The system SHALL derive a fade-onset time (`fade_start`) for the song's final amplitude decline from the
energy envelope, bounded by a minimum and maximum tail-fade window, such that a gradual fade-out yields a
fade spanning the real decline and an abrupt ending yields a short fade at `music_end`. Every realized
effect overlapping `[fade_start, music_end]` SHALL carry an opacity fade-out over that region so the
lights dim along with the music. The fade-out SHALL be emitted through the existing effect-level soft-edge
fade mechanism (the same `T_TEXTCTRL_Fadeout` / dissolve-out primitive used for legato cells), with the
fade length scaled to the effect's portion of the trailing region. An effect that already carries a
fade-out SHALL keep the longer of the two. This realization SHALL apply only to the song tail; sections
before `fade_start` SHALL be unaffected.

#### Scenario: A fade-out song dims with the music

- **WHEN** a song ends on a gradual amplitude fade-out
- **THEN** `fade_start` is placed at the onset of that decline and the final span's effects fade their
  opacity from `fade_start` to `music_end`, mirroring the music rather than hard-cutting

#### Scenario: An abrupt ending gets a short fade

- **WHEN** a song ends abruptly with no gradual decline
- **THEN** `fade_start` collapses to the minimum tail-fade window and the final span's effects fade out
  briefly at `music_end` rather than cutting at full brightness

#### Scenario: The fade reuses the existing fade mechanism

- **WHEN** the song-end fade is applied to a final-span effect
- **THEN** it is expressed as effect-level fade-out keys produced by the existing soft-edge fade path,
  not a newly invented primitive, and an effect that already has a longer fade-out keeps it
