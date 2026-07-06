# Add narrative props: matrix Text and lyric-driven singing Faces

## Why

The matrix's real job is narrative — the effects catalog and scene cookbook both name it: "the
matrix is the storyteller" (`xlights-scene-cookbook.md` SC-08, citing Vol 3 §6). Today the pipeline
generates zero narrative content. The matrix (a real model in this layout — `tests/fixtures/getModels.json`
lists `"Matrix"` alongside Arches / Mega Tree / House Outline) is treated as just another focal canvas:
it gets washes, weave cells, the hero onset layer, and peak composite stacks via `SEM_FOCAL`, but never
a single word — even though the brief already curates the song's featured lyric lines with timestamps
and reasons (`MusicBrief.featured_lyric_moments`, `music_brief.py:65`) and knows the song's identity.
This is the best payoff-to-effort ratio on the board (roadmap Horizon 2: "Highest visible payoff per
unit work"): the lyric timing track exists, the brief already has curated moments, the Text effect is
stock and asset-free, and the asset-bound placement path (F-B) provides the route.

Singing faces are the community's signature vocal-song move: a character prop whose mouth shapes follow
the vocal line ("Faces: Phoneme-driven mouth rendering for singing face models … Vocal lip-sync",
`xlights-effects-catalog.md` §8). The pipeline already does the hard audio work — fetched lyric text is
force-aligned against the separated vocal stem with word-level timestamps (`lyrics_align.py`), driving
lyric color triggers and the "Lyrics" reference timing track. What's missing is three specific things:
(1) phoneme-level timing (one level finer than the words we have) to drive the Faces effect's mouth
shapes; (2) a placement route — Faces is in `ASSET_BOUND_TYPES` (`constants.py:9`), excluded from the
mined catalog because its settings reference a face definition and a timing track (F-B builds the route);
and (3) hardware — a prop with a face definition to sing on, which the current layout does not have. The
phoneme extractor, the multi-layer timing-track writer, the Faces builder, and the gating logic are all
buildable and hermetic-testable now; the placement pass no-ops on this layout until a face prop appears,
and the phoneme track is independently useful (it makes the saved `.xsq` hand-editable for faces).

## What Changes

**F-C matrix narrative Text:**
- Add a new deterministic pass `pipeline/matrix_text.py::place_matrix_text(st, matrix)` that emits xLights
  Text effects on the matrix **model** (never a group) driven by existing brief fields — a title card in
  the intro, up to `MAX_TEXT_MOMENTS = 4` featured lyric phrases snapped to their aligned line spans, and
  an optional config-gated outro sign-off.
- Add `find_matrix(model_names)` (name contains "matrix", case-insensitive) and plumb `State.model_names`
  via a best-effort `client.get_model_names()` fetch beside `targetable_groups` in `run_pipeline`.
- Ground content by construction: only strings present in `featured_lyric_moments`/`identity` may appear;
  featured moments with no fuzzy match to an aligned lyric line are dropped, never shown at a guessed time.
- Emit Text with `on_top=True`, `T_CHOICE_LayerMethod: "Max"` blend, the section palette's lightest color,
  static-or-scroll-once sizing, and dim concurrent matrix-targeted non-text instructions to ~40% during
  each text span. Exclude text from the peak section.
- Tag each Text instruction with its owning `section_index` and a marker key (`X_MatrixText=1`) so the
  refine-loop/`xlo regen` splice path re-runs the pass idempotently (replace, not stack).
- Add advisory QA when text moments exceed the cap; add named dials `MAX_TEXT_MOMENTS`/`TEXT_SPACING_MS`
  in `pipeline/tuning.py`.

**F-D lyric-driven singing Faces:**
- Add `xlights_core/audio/phonemes.py`: `word_phonemes(word)` (CMUdict via `pronouncing`/`g2p-en`,
  deterministic `['etc']` fallback for OOV) and `phoneme_marks(lines)` mapping ARPAbet → the 10 Papagayo
  mouth shapes (`AI, E, etc, FV, L, MBP, O, rest, U, WQ`) via a committed `_ARPA_TO_PAPAGAYO` table,
  distributing phonemes across each word's aligned span (vowels ~2× consonant weight) and inserting `rest`
  in inter-word gaps > `REST_GAP_MS`.
- Extend `pipeline/timing.py`: `TimingTrack` gains multi-layer support so `patch_xsq_timing_tracks` emits
  one `<EffectLayer>` per layer (single-layer tracks unchanged, back-compat by default); add a
  `_phoneme_track` builder producing a 3-layer "Lyric Phonemes" track (phrases / words / phonemes) —
  the Papagayo import shape — appended to `build_timing_tracks`, inheriting idempotent replace + atomic
  write.
- Add `pipeline/faces.py::place_faces(st, face_models)` (with F-B's `build_faces_settings`): one Faces
  instruction per singing-face model per merged sung region (aligned line spans merged with ≤2 s gaps),
  bound to the "Lyric Phonemes" track and the model's real face definition, `on_top=True`; gently dim
  concurrent `SEM_ALL`-bed instructions during sung regions.
- Add `face_definitions(rgb_path)` parsing `faceInfo` from `rgbeffects.xml` (in `knowledge/layout_semantics.py`)
  to detect a singing-face prop and its definition — no definition → no Faces, ever.
- Gate the pass on all of: vocal song (aligned word spans), a singing-face model with a face definition,
  and the phoneme track scheduled at finalize. Instrumental songs and this face-less fixture layout no-op
  with a degradation-log line. Tag instructions with `section_index` for splice-safe regen.

## Capabilities

### New Capabilities
- `matrix-text`: place stock xLights Text effects on the matrix model driven by lyric/identity brief
  fields — title card, featured lyric phrases, optional outro — as sparse narrative punctuation.
- `singing-faces`: extract phoneme timing from aligned lyrics, write a Papagayo-shaped 3-layer timing
  track, and place phoneme-driven Faces effects on singing-face props over sung regions (gated on
  hardware + a face definition).

### Modified Capabilities
- `timing-tracks`: the lyric-related timing track requirement gains multi-layer (phrases/words/phonemes)
  support so a Papagayo-style "Lyric Phonemes" track can be written for vocal songs.

## Impact

- New files: `packages/xlights-orchestrator/src/xlights_orchestrator/pipeline/matrix_text.py`,
  `packages/xlights-orchestrator/src/xlights_orchestrator/pipeline/faces.py`,
  `packages/xlights-core/src/xlights_core/audio/phonemes.py`.
- Modified: `pipeline/generate.py` (wire both passes into `generate_instructions` after the section loop),
  `pipeline/run.py` (model-name fetch + `place_faces` wiring), `pipeline/timing.py` (multi-layer
  `TimingTrack` + `_phoneme_track`), `pipeline/finalize.py` (already the offline-patch seam),
  `pipeline/tuning.py` (text dials), `xlights_core/knowledge/layout_semantics.py` (`face_definitions`),
  `qa/variety.py`-style advisory, `docs/usage.md`.
- New dep: `pronouncing` (or `g2p-en`) added to `xlights-core` (optional `lyrics` extra), heavy import
  deferred inside functions.
- Hard dependency on `add-asset-bound-placement` (F-B): `build_text_settings`, `build_faces_settings`,
  `direct_settings` field, the emitter's asset-bound branch, and the frozen Text/Faces templates.
- Tests: new `tests/test_matrix_text.py`, `tests/test_phonemes.py`, `tests/test_faces.py`, multi-layer
  timing-track round-trip tests; hermetic-first, negative-space (instrumental / no-matrix / no-face) as
  first-class cases; golden expected unchanged on the instrumental fixture.
- Risk profile: additive and gated. F-D ships dark on the current face-less layout (no rendered
  deliverable until a face prop with a definition arrives); F-C is fully active given a vocal song with
  a matrix.
