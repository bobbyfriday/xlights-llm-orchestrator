## 1. Grapheme→phoneme + viseme mapping

- [x] 1.1 Add `phonemes.py` (xlights-core `audio/` or `text/`): `arpabet_to_viseme` constant mapping the
  ~39 ARPABET phones → `{AI,E,FV,L,MBP,O,U,WQ,etc,rest}` (mirrors xLights/Papagayo; one tunable table).
- [x] 1.2 `word_to_visemes(word, *, lookup=None) -> list[str]`: CMUdict pronunciation (injectable
  `lookup`; default wraps the `cmudict` package when present) → visemes; deterministic letter-based
  fallback for OOV; unknown → `rest`. No network, no model.
- [x] 1.3 Add an optional `lyrics` extra (the `cmudict` data package); import lazily so the module works
  (via fallback) when the extra is absent.
- [x] 1.4 Hermetic tests: a known word maps to expected visemes via an injected dict; an OOV word uses
  the fallback (non-empty, only set members); the viseme table covers every ARPABET symbol it's given.

## 2. Phoneme timing track (multi-layer)

- [x] 2.1 In `pipeline/timing.py`, add `layers: list[list[TimingMark]] | None = None` to `TimingTrack`;
  `patch_xsq_timing_tracks` writes one `<EffectLayer>` per layer when `layers` is set, else the existing
  single `marks` layer (every current track byte-unchanged).
- [x] 2.2 Add `_phoneme_track(sa, end_ms)`: phrases = `sa.lyrics` lines; words = `lines[].words`;
  phonemes = `word_to_visemes` per word tiled evenly across `[word.start, word.end]`, with `rest` marks
  filling inter-word/inter-line gaps. Returns a 3-layer `TimingTrack` (name e.g. `"Faces"`), or `None`
  when there are no timed words.
- [x] 2.3 Wire `_phoneme_track` into `build_timing_tracks` (additive; only when timed lyrics exist).
- [x] 2.4 Hermetic tests: multi-layer patcher writes 3 `<EffectLayer>`s in order; single-layer tracks
  unchanged; `_phoneme_track` produces phrases/words/phonemes with `rest` gaps and ms timing; no lyrics
  → `None`.

## 3. Singing-face detection + Faces effect placement

- [x] 3.1 Resolve singing-face props + their node face-definition name from the layout (reuse the
  layout-semantics rgbeffects parser / `faceInfo`); expose `singing_face_props(layout) -> [(model, face_def)]`.
- [x] 3.2 Add `pipeline/faces.py`: `place_faces(sa, layout, song_end_ms) -> list[EffectInstruction]` —
  one `Faces` instruction per singing-face prop spanning the vocal span, `extra_settings` =
  `{E_CHOICE_Faces_Phoneme:"(Auto)", E_CHOICE_Faces_TimingTrack:<track>, E_CHOICE_Faces_FaceDefinition:<def>,
  E_CHOICE_Faces_Eyes:"Auto", E_CHECKBOX_Faces_SuppressWhenNotSinging:"1"}`; `effect_type="Faces"`,
  marked asset-bound/`on_top` so the layer-budget clamp and wash guard skip it. Empty when no timed lyrics.
- [x] 3.3 Call `place_faces` in the generate path (only when `sa.lyrics` has timed words); tag the
  instructions and append to the show's instruction list.

## 4. Asset-bound emitter path

- [x] 4.1 In `effect_emitter`, add a branch for asset-bound effects (`effect_type == "Faces"`): assemble
  the settings string from `extra_settings` and call `client.add_effect(...)` directly — skip
  `place_preset`/the preset library and `render_style`. Catch placement errors like the rest of the
  emitter (a Faces failure never aborts the run).
- [x] 4.2 Confirm `clamp_layer_budget` and `_guard_wash_occlusion` leave Faces instructions untouched.
- [x] 4.3 Hermetic test: a Faces `EffectInstruction` round-trips through the emitter to a
  `client.add_effect` call with the expected settings (fake client), and a non-Faces effect still goes
  through `place_preset`.

## 5. Live verification

- [ ] 5.1 Run the pipeline on a vocal song (e.g. a Genius-lyric'd track) and confirm in xLights: the
  `Faces` track has phrases/words/phonemes; the three `GE Hanging Bulb Singing` props lip-sync; faces
  rest during instrumental passages.
- [ ] 5.2 Tune the viseme table / mouth color / eye-blink against the live render if needed.
- [ ] 5.3 Confirm an instrumental song places no Faces effect and is otherwise unchanged.

## 6. Land

- [x] 6.1 Document singing faces (README/usage): needs timed lyrics + a singing-face prop with a node
  face definition; the optional `lyrics` extra improves phoneme accuracy.
- [ ] 6.2 Open a PR per the project workflow; do not commit to `main` directly.
