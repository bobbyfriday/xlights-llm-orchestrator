## ADDED Requirements

### Requirement: Generate phonemes from aligned lyric words

The system SHALL derive, for each timed lyric word, a sequence of mouth-shape phonemes drawn from the
xLights set `{AI, E, FV, L, MBP, O, U, WQ, etc, rest}`. It SHALL obtain each word's pronunciation from a
grapheme-to-phoneme step — the CMU Pronouncing Dictionary when available, and a deterministic
letter-based fallback for out-of-vocabulary words — and map the resulting ARPABET phones to the
mouth-shape set through a fixed table owned in code. The derivation SHALL be deterministic and offline,
and SHALL degrade gracefully (to the fallback, then to `rest`) rather than fail when a pronunciation is
unavailable.

#### Scenario: A known word maps to mouth shapes

- **WHEN** a timed lyric word is in the pronunciation dictionary
- **THEN** its ARPABET pronunciation is mapped to a sequence of mouth-shape phonemes from the xLights set

#### Scenario: An out-of-vocabulary word still produces phonemes

- **WHEN** a word has no dictionary pronunciation
- **THEN** the deterministic fallback produces mouth-shape phonemes rather than failing, and the result
  is still drawn only from the xLights set

### Requirement: Drive singing-face props with a Faces effect synced to the vocals

When a song has timed lyrics, the system SHALL place an xLights `Faces` effect on each singing-face prop
in the layout, configured to read the generated phoneme timing track and lip-sync to the vocals. The
effect SHALL be placed deterministically (not by the language model) and SHALL be configured to read its
phonemes from the timing track (auto phoneme), use the prop's node face definition, rest during
non-vocal passages, and animate the eyes automatically. Because the `Faces` effect is asset-bound, the
system SHALL place it from explicit settings rather than from the mined preset library, and a placement
failure SHALL NOT abort the run. When a song has no timed lyrics, or a prop has no usable face
definition, no `Faces` effect SHALL be placed for it.

#### Scenario: A vocal song lights the singing faces

- **WHEN** the song has timed lyrics and the layout has a singing-face prop with a node face definition
- **THEN** a `Faces` effect is placed on that prop, reading the phoneme timing track, with the face
  resting during non-vocal passages

#### Scenario: An instrumental song places no faces

- **WHEN** the song has no timed lyrics
- **THEN** no `Faces` effect is placed and the rest of the show is unchanged

#### Scenario: A prop without a face definition is skipped

- **WHEN** a singing-face prop has no usable node face definition
- **THEN** that prop is skipped with a warning and no broken effect is placed
