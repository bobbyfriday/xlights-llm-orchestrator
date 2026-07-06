# Tasks — narrative props (matrix Text + singing Faces)

## 1. Shared dependency (F-B)

- [x] 1.1 Confirm `add-asset-bound-placement` (F-B) has landed: `build_text_settings`,
  `build_faces_settings`, the `direct_settings` instruction field, the emitter's asset-bound branch, and
  frozen Text + Faces settings templates (probe-verified key names).
  <!-- Confirmed on main (base aa505a9): direct_settings.build_text_settings, EffectInstruction.direct_settings,
       effect_emitter's place_direct branch, DIRECT_TYPES={Text,Faces} all present. -->
- [x] 1.2 Sequence F-C's Text pass after improve-musicality Phase 3 lands `place_transitions`; copy its
  splice-hook re-run pattern.
  <!-- improve-musicality's place_transitions is on a parallel unmerged branch (not in this base). Copied the
       equivalent splice-hook pattern: `place_matrix_narrative` (strip-and-replace, idempotent) re-runs in
       refine_loop after `replace_section`/clamp and before `finalize_effects`. -->

<!-- NOTE (scope): the F-D half (§6–§10 below) ALREADY SHIPPED as the separate `add-singing-faces` change
     (pipeline/faces.py, audio/phonemes.py, timing._phoneme_track on main) — those tasks are superseded there,
     NOT re-implemented here. The specs/singing-faces spec delta in this change is likewise superseded by
     add-singing-faces. This branch implements F-C (matrix narrative Text) only. -->


## 2. F-C matrix Text — matrix discovery

- [x] 2.1 Add `pipeline/matrix_text.py::find_matrix(model_names: list[str]) -> str | None` (name contains
  "matrix", case-insensitive, mirroring `_ORDER_TIERS`' focal test); `None` → the pass no-ops.
- [x] 2.2 Plumb `State.model_names` via a best-effort `st.model_names = await client.get_model_names()`
  beside the `targetable_groups` call in `run_pipeline`, wrapped in `except Exception`.
- [x] 2.3 Hermetic test: `find_matrix` against the fixtures' `getModels.json` model list resolves "Matrix";
  a face-less/matrix-less list returns None.

## 3. F-C matrix Text — selection engine

- [x] 3.1 Implement `select_text_moments(brief, sa, plan) -> list[TextMoment]` (pure): title-card rule
  (`identity.title` + artist if it fits, intro only, skip if intro < 8 s or title empty); featured-phrase
  cross-check against aligned lines (snap to matched line span; drop moments with no fuzzy match);
  caps/spacing/peak-exclusion (`MAX_TEXT_MOMENTS = 4`, `TEXT_SPACING_MS = 20_000`, ≤ one per section, none
  in the peak section); instrumental degradation (title card only).
- [x] 3.2 Add named dials `MAX_TEXT_MOMENTS` and `TEXT_SPACING_MS` to `pipeline/tuning.py`.
- [x] 3.3 Table-driven tests: vocal song with 6 candidate moments → 4 placed, spacing enforced; a moment
  with no aligned line → dropped; instrumental → title only; no matrix → `[]`.

## 4. F-C matrix Text — realization & wiring

- [x] 4.1 Implement `place_matrix_text(st, matrix) -> list[EffectInstruction]` building instructions with
  `direct_settings = build_text_settings(...)`, `on_top=True`, `T_CHOICE_LayerMethod: "Max"` blend, the
  section palette's lightest color (`beats._lightest_hex`), static-vs-scroll decision (`E_CHOICE_Text_Dir`
  = `none` if it fits width else `left`), scroll-once speed sized so one traverse ≈ the aligned
  duration, glyph size ≥ 10-12 px (F-B's `build_text_settings` folds font/size into the descriptor).
  <!-- F-B's build_text_settings uses E_SLIDER_Text_Speed and an Arial font descriptor (not
       E_TEXTCTRL_Text_Speed / render_style); used its actual API. Matrix height via a `_matrix_height`
       heuristic defaulting to the 50px readability floor, TODO(F-E) for the real manifest/probe. -->
- [x] 4.2 Dim concurrent matrix-targeted non-text instructions during each text span (multiply
  `C_SLIDER_Brightness` by ~0.4 via `brightness_setting`); never touch non-matrix props.
- [x] 4.3 Refuse and log a degradation if the matrix resolution is under ~50 px (catalog rule #2).
- [x] 4.4 Wire `place_matrix_text` into `generate_instructions` after the section loop (beside
  `place_triggers`/`key_moment_flashes`) and into the refine/regen splice path (`place_matrix_narrative`).
- [x] 4.5 Tag each Text instruction with the owning `section_index` and a marker key `X_MatrixText=1` in
  `extra_settings` (idempotence marker for strip-and-replace; xLights tolerates the unknown key).

## 5. F-C matrix Text — idempotence, QA, golden, live verify

- [x] 5.1 Idempotence + regen tests: re-running the pass after `replace_section` yields exactly the same
  text moments (no stacking); regenerating a section that owns a text moment recreates exactly one copy.
- [x] 5.2 Add a `qa/variety.py`-style advisory finding when text moments exceed the cap (Text is outside
  `rules.FEATURES`/`ENERGY_BAND`).
- [x] 5.3 Settings validation test: every emitted `direct_settings` round-trips
  `parse_settings`/`serialize_settings` and its `E_TEXTCTRL_Text` equals the sanitized source string.
- [x] 5.4 Golden: expected nil / title-card only (fixture has no lyrics); confirmed BYTE-IDENTICAL
  (the golden's `_FakeClient` has no `get_model_names` and its `get_show_folder` raises → no matrix →
  the pass no-ops). No regeneration needed.
- [ ] 5.5 Live verify (`-m live`): run a vocal reference song end-to-end; eyeball the review-bundle stills.
  <!-- SKIPPED: requires a running xLights instance + a vocal reference render (live hardware). Left
       unchecked per the rigor brief; the template itself is already live-validated by F-B. -->
- [x] 5.6 Docs: note the text doctrine (punctuation, caps, non-sources) in `docs/usage.md`; cross-link
  craft-roadmap item 8 as closed.

<!-- ============================================================================================
     F-D (§6–§11 below) — SUPERSEDED BY the separate `add-singing-faces` change (shipped on main:
     xlights_core/audio/phonemes.py, pipeline/faces.py, pipeline/timing._phoneme_track, the `lyrics`
     extra, tests/test_phonemes.py + tests/test_faces.py). NOT implemented on this branch — the boxes
     are intentionally left unchecked here because add-singing-faces owns them, not this change. The
     specs/singing-faces spec delta in THIS change is likewise superseded there.
     ============================================================================================ -->

## 6. F-D faces — phoneme extractor

- [ ] 6.1 Add `pronouncing` (or `g2p-en`) to `xlights-core` deps (optional `lyrics` extra); defer the heavy
  import inside functions, mirroring `lyrics_align._transcribe`.
- [ ] 6.2 Create `xlights_core/audio/phonemes.py`; commit the `_ARPA_TO_PAPAGAYO` table (39 ARPAbet phones
  → the 10 Papagayo mouth shapes `AI, E, etc, FV, L, MBP, O, rest, U, WQ`).
- [ ] 6.3 Implement `word_phonemes(word) -> list[str]` (CMUdict lookup, `['etc']` fallback for OOV;
  deterministic for in-dictionary words) and `phoneme_marks(lines) -> list[tuple[str,int,int]]` distributing
  each word's phonemes across its aligned `[start,end]` span with vowel-class ~2× consonant-class weighting
  and `rest` marks in inter-word gaps > `REST_GAP_MS` (~120 ms).
- [ ] 6.4 Hermetic tests (`tests/test_phonemes.py`): known words → exact label sequences; OOV token →
  `['etc']`; distribution sums to the word span; rest marks in gaps; deterministic across runs.

## 7. F-D faces — multi-layer timing track

- [ ] 7.1 Extend `TimingTrack` with `layers: list[list[TimingMark]] | None = None` (or a sibling
  `MultiLayerTimingTrack`); when present, `patch_xsq_timing_tracks` emits one `<EffectLayer>` per layer
  instead of the single layer at `timing.py:175`. Existing single-layer tracks untouched (back-compat).
- [ ] 7.2 Add `_phoneme_track(sa, end_ms) -> TimingTrack | None`: name `"Lyric Phonemes"`, three layers —
  phrases (aligned lines, reusing `_lyric_track`'s marks), words (per-word spans), phonemes
  (`phonemes.phoneme_marks`); append it to the candidate list in `build_timing_tracks` (`timing.py:134–141`).
- [ ] 7.3 Tests: XML round-trip (parse the patched `.xsq`, assert 3 `<EffectLayer>`s + phrase/word/phoneme
  labels); idempotent re-patch; no "Lyric Phonemes" track when there are no aligned lyrics.

## 8. F-D faces — builder & detection (with F-B)

- [ ] 8.1 Freeze the Faces settings template from a hand-authored probe on a scratch model with a throwaway
  face definition (F-B probe protocol); implement `build_faces_settings` requiring verified refs (timing
  track name + face definition, no defaults).
- [ ] 8.2 Implement `face_definitions(rgb_path) -> dict[str, list[str]]` parsing `faceInfo` elements in
  `rgbeffects.xml` (home: `knowledge/layout_semantics.py`).
- [ ] 8.3 Ring-1 round-trip + ring-2 reference tests with a fixture `rgbeffects.xml` containing a synthetic
  `faceInfo`.

## 9. F-D faces — placement pass

- [ ] 9.1 Create `pipeline/faces.py` with `PHONEME_TRACK_NAME = "Lyric Phonemes"` and
  `place_faces(st, face_models: dict[str, str]) -> list[EffectInstruction]`: one Faces instruction per
  singing-face model per merged sung region (aligned line spans merged with ≤ 2 s gaps), `direct_settings =
  build_faces_settings(timing_track=PHONEME_TRACK_NAME, face_definition=face_models[model], ...)`,
  `on_top=True`; tag each with the owning `section_index`.
- [ ] 9.2 Implement the three gates (§D8): vocal song (aligned word spans), singing-face model with a face
  definition, phoneme track scheduled; a single degradation-log line at each failed gate.
- [ ] 9.3 v1 surrounding-dim: a gentle brightness multiplier on concurrent `SEM_ALL`-bed instructions during
  sung regions (≤ ~30%); never dim the face prop.
- [ ] 9.4 Wire `place_faces` into `generate_instructions` (+ the splice re-run) and into `run.py`'s apply
  stage when timed lyrics exist; the pass fully owns Faces-type instructions (filter-and-rebuild → idempotent).
- [ ] 9.5 Ensure coverage/variety QA ignores the SINGING_FACE prop (it is outside every SEM_ ensemble);
  add a placement-rules advisory if any non-Faces instruction targets a SINGING_FACE model.

## 10. F-D faces — negative-space, schema guard, golden, live verify

- [ ] 10.1 Hermetic tests (`tests/test_faces.py`) with a fake layout that has a face model: instructions
  span sung regions only; instrumental → none; no definition → none; the real fixture layout → none.
- [ ] 10.2 Negative-space first-class tests: instrumental song → no track additions beyond today + no
  instructions; layout without faces → no-op; missing face definition → refused with a logged reason.
- [ ] 10.3 Schema-drift guard: a stored known-good `lyrics` payload (with `words`) validated in tests (per
  roadmap I6) since the extractor depends on that shape.
- [ ] 10.4 Golden: expected zero change (both gates fail on the fixture); assert the fixture layout produces
  zero Faces instructions and an unchanged golden — any diff is a bug, not a regeneration.
- [ ] 10.5 Live verify (`-m live`, hardware-conditional): on a layout with a real face prop (or a face
  definition drawn on the Matrix as a stand-in) run a vocal song end-to-end; open the finalized `.xsq`;
  confirm the phoneme track imported, the Faces effect bound to it, mouths track the vocal by eye, and the
  surrounding bed dims during sung regions; a `validate_direct`-style scratch placement of the frozen Faces
  template.
- [ ] 10.6 Docs: document the "Lyric Phonemes" track, faces gating, and the name-collision caveat in
  `docs/usage.md`; cross-link craft-roadmap item 7 (faces half) as closed.

## 11. Fixtures (shared)

- [x] 11.1 Extend a copy of the golden's `SongAnalysis` with `lyrics.lines` + a brief with
  `featured_lyric_moments`, so F-C selection tests run against realistic timing data.
  <!-- Done for F-C inline in tests/test_matrix_text.py (aligned `_lyrics(...)` lines + featured moments +
       a matrixed model list). The F-D phoneme/track fixtures shipped with add-singing-faces. -->

