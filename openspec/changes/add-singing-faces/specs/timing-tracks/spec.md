## ADDED Requirements

### Requirement: Multi-layer timing tracks and a phoneme lyric track

The timing-track model and the offline `.xsq` patcher SHALL support timing tracks with more than one
layer, writing one `<EffectLayer>` per layer in the order given, while a single-layer track continues to
be written exactly as before. When a song has timed lyrics, the pipeline SHALL emit a phoneme lyric
timing track with three layers — phrases (lyric lines), words (word timings), and phonemes (mouth shapes
distributed across each word's span, with silence between words marked as `rest`) — in the format the
xLights Faces effect reads. This track SHALL be patched into the finished `.xsq` offline like the other
reference tracks and SHALL never block finalize.

#### Scenario: A multi-layer track writes a layer per layer

- **WHEN** a timing track is built with multiple layers
- **THEN** the patcher writes one `<EffectLayer>` per layer in order, and existing single-layer tracks
  are written unchanged

#### Scenario: A vocal song gets a phoneme lyric track

- **WHEN** the song has timed lyrics
- **THEN** a three-layer phrases/words/phonemes lyric timing track is patched into the `.xsq`, with
  inter-word silence marked as `rest`
