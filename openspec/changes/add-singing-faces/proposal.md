## Why

The layout has singing-face props ready to lip-sync — `GE Hanging Bulb Singing-2/3/4` each carry a full
xLights `faceInfo` definition (a node-based "Bulb" def + an image "Matrix" def) with the complete
phoneme mouth set (`Mouth-AI/E/FV/L/MBP/O/U/WQ/etc/rest`) and eyes-open/closed. The pipeline already
has everything upstream: Whisper word-level lyric timing (`sa.lyrics.lines[].words`), the vocals stem,
and the offline `.xsq` timing-track patcher. But nothing drives the faces: `SINGING_FACE` props are
classified and then **excluded** from all choreography, and no Faces effect is ever placed. The faces
sit dark while the rest of the show runs. We want them to sing — fully automatically, no manual step.

## What Changes

- **Grapheme→phoneme + viseme mapping (new, deterministic).** Add a `phonemes` extractor: each aligned
  lyric word → ARPABET pronunciation (CMU Pronouncing Dictionary, with a deterministic letter-based
  fallback for out-of-vocabulary words) → the 10 xLights mouth shapes
  (`AI E FV L MBP O U WQ etc rest`) via a curated ARPABET→viseme table mirroring xLights/Papagayo.
- **Phoneme timing track (multi-layer).** Build a three-layer timing track from `sa.lyrics`
  — **phrases** (lines) / **words** (word timing) / **phonemes** (visemes distributed across each word's
  span; inter-word gaps are `rest`). Extend the timing-track model + offline patcher to write
  multi-layer timing tracks (`<EffectLayer>` per layer), matching xLights' native phoneme-track XML.
- **Auto-place the Faces effect (asset-bound).** On each `SINGING_FACE` prop, place an xLights `Faces`
  effect spanning the song, reading the phoneme track: `E_CHOICE_Faces_Phoneme=(Auto)`,
  `E_CHOICE_Faces_TimingTrack=<track>`, `E_CHOICE_Faces_FaceDefinition=<the node def>`,
  `E_CHOICE_Faces_Eyes=Auto`, `E_CHECKBOX_Faces_SuppressWhenNotSinging=1` (the face rests during
  instrumental passages natively). `Faces` is **asset-bound** (excluded from the mined preset library),
  so add an emitter path that places it from explicit settings rather than a library Look.
- **No regression to the rest of the show:** faces are driven independently, exactly as the layout
  semantics already intend; non-vocal songs (no timed lyrics) place no Faces effect.

## Capabilities

### New Capabilities
- `singing-faces`: detect singing-face props and drive them with an automatically generated,
  phoneme-timed `Faces` effect synced to the vocals.

### Modified Capabilities
- `timing-tracks`: the timing-track model and offline `.xsq` patcher support **multi-layer** timing
  tracks, and the pipeline emits a phrases/words/phonemes lyric track when timed lyrics exist.

## Impact

- New `packages/xlights-core/src/xlights_core/audio/phonemes.py` (or `text/`): word→ARPABET→viseme,
  with the curated viseme table and OOV fallback. New optional dependency: the CMU dictionary (a small
  optional `lyrics` extra; degrades to the fallback when absent).
- `pipeline/timing.py`: a `layers` field on `TimingTrack`; `patch_xsq_timing_tracks` writes one
  `<EffectLayer>` per layer; a `_phoneme_track(...)` builder.
- `pipeline/generate.py` (or a new `pipeline/faces.py`): detect `SINGING_FACE` props (from layout
  semantics) and emit `Faces` `EffectInstruction`s; `effect_emitter` gains an asset-bound placement
  branch for `Faces` (settings-string → `client.add_effect`, no library Look).
- Tests: hermetic coverage of g2p/viseme/distribution, the multi-layer track + patcher XML, and Faces
  placement; live verification against the three `GE Hanging Bulb Singing` props. No CLI/schema change
  beyond the additive `Faces` effect path.
