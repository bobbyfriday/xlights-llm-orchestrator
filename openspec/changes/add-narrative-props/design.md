# Design — narrative props (matrix Text + singing Faces)

## Context

This change authors roadmap Horizon 2 items **F-C (Matrix narrative Text, complexity M)** and **F-D
(Lyric-driven Faces, complexity L)** together as the "matrix as storyteller" / vocal-narrative pair.
Both sit on top of **F-B asset-bound placement** (change `add-asset-bound-placement`): the direct-settings
route that builds settings strings for effect types absent from the mined catalog. F-B provides
`build_text_settings`, `build_faces_settings`, the `direct_settings` instruction field, the emitter's
asset-bound branch, the frozen Text/Faces settings templates, and the reference-verification "rings".
This change references that dependency; it does not re-specify it.

Confirmed in the current tree at authoring time: neither faces nor matrix-text is implemented here. There
is no `pipeline/faces.py`, no `pipeline/matrix_text.py`, no `xlights_core/audio/phonemes.py`; `ASSET_BOUND_TYPES`
still contains `"Faces"`; no spec has a faces/matrix/phoneme requirement. (A parallel unmerged branch commit
`a011229` "automatic singing-face lip-sync" implements F-D, but it is **not** an ancestor of this branch's
HEAD and its files are absent here — so F-D is authored as a NEW capability, not a modification of shipped
behavior.)

### F-C current state — the matrix, the collision surface, the content sources

**The matrix in the layout & group vocabulary.** The layout-semantics spec classifies matrices as role
`MATRIX` ("2D pixel surface capable of images/text", capability class `2D_SURFACE`: "Supports pictures,
text, video, shader-style effects" — `xlights-layout-semantics-spec.md` §2). Two code consequences:
- **No dedicated SEM_ group.** Spec §5: "Single-instance roles (`MEGA_TREE`, `MATRIX`, `STAR`, `SIGN`) do
  not need a group; the planner addresses the model directly." `layout_semantics._ROLE_GROUP` (line 43) has
  no MATRIX entry, and `pipeline/semantic_groups.py` has no matrix constant.
- **It is focal.** Spec §4 step 6 marks `MATRIX` props `focal: true`, so it lands in `SEM_FOCAL`
  (`build_sem_groups`, `layout_semantics.py:75`), and the render-order tiers treat any name containing
  "matrix" as the focal tier (`_ORDER_TIERS`, `layout_semantics.py:122`:
  `lambda n: n == "SEM_FOCAL" or "matrix" in n.lower()`) — rendered late, i.e. winning overlaps.

Targeting the model directly is legal end-to-end: `place_preset`'s only target check is membership in
`await client.get_models()` (`editing.py:83`), which includes plain models; the emitter passes any
`EffectInstruction.target` through. Caveat: `State.available_groups` comes from `targetable_groups()`
(`pipeline/groups.py`), which probes groups — the pass must resolve the matrix model name separately.

**The collision surface.** Because the matrix rides `SEM_FOCAL`, three existing layers can be live on it
at any moment (`generate.realize_section`): the **hero onset layer** (the melodic lead's onsets on
`HERO_GROUP = SEM_FOCAL`, `beats.place_beat_accents`, `semantic_groups.py:28`); the **peak composite
stack** (`curated_composite(_PEAK_COMPOSITES[...], [HERO_GROUP])` on peak sections, `generate.py:196–199`,
2 blended layers of Morph/Galaxy/etc.); and whatever **washes/weave cells** the Generator aims at
`SEM_FOCAL`. Any Text design that ignores this puts glyphs behind a kaleidoscope.

**Content sources that already exist.** `FeaturedLyricMoment{line, start_ms, end_ms, why}` list on the
brief (`music_brief.py:44–48, 65`); `MusicBrief.identity.title`/`.artist` (`music_brief.py:30–31`);
`LabeledSection.label` (the weakest source); `ShowPlan.key_moments` with a documented `"lyric"` kind
(`show_plan.py:22`) that the Director prompt already asks for (`director.py:38`) but that has no text
payload field and no downstream consumer beyond the white-flash filter (which matches only
climax/accent/drop/hit); word-level timing `{word,start,end}` persisted by `lyrics_align._match_lines`
(`lyrics_align.py:80–83`) and consumed by the `lyric_color` trigger (`triggers.py:155–166`); line-level
timing feeding the "Lyrics" reference timing track (`timing.py:123–127`).

**Text effect ground truth (guides).** Catalog §8 Text: "minimum ~10–12 px of height for legible
characters … Group canvases spanning mismatched props mangle glyphs; keep Text on a single matrix …
Best on: Matrix only (practically)." Catalog rule §9 #2: "Never place media effects (Text, Pictures,
Video) on canvases under ~50px of resolution." Cookbook Masked Texture Reveal (lines 170–182): Text with
"1 is Mask" over Bars/Plasma = "texture shows only inside glyphs … premium production value at near-zero
render cost", failure modes "text too small … busy effects behind small glyphs destroy legibility — bars
beat plasma for thin fonts." Text is absent from the mined catalog (`presets/looks.json` has no `Text`
key) → placement impossible today, the F-B dependency.

### F-D current state — word timing exists; faces excluded; no hardware

**Word-level timing is the ceiling today.** `lyrics_align.py`: Whisper (MLX, `mlx-community/whisper-small-mlx`)
transcribes the vocal stem with `word_timestamps=True` (`_transcribe`, 42–52); each lyric line is fuzzy-matched
into the transcript with a monotonic cursor (`_match_lines`, 55–87) and the matched per-word spans are
persisted (`lyrics_align.py:80–83`). Output: `SongAnalysis.lyrics = {lines:[{text,start,end,words:[...]}],
sections:[...], repeated:[...]}`. Alignment is fully graceful — any failure returns `None` and the run
proceeds (129–131). There is **no phoneme anywhere** (no g2p dep, no ARPAbet/Papagayo vocabulary).

**Timing tracks are authored offline at finalize.** `finalize.finalize_sequence` (21–40): after
`save_sequence` the run closes the sequence and patches the `.xsq` offline ("attaching media / reordering
via the live API crashes xLights"), including reference timing tracks via `build_timing_tracks` +
`patch_xsq_timing_tracks` (`pipeline/timing.py`). The patcher mirrors the corpus timing-track XML exactly,
is idempotent (same-named tracks removed before re-adding, `timing.py:167–169`) and atomic (temp +
`os.replace`). Today each track is a single `<EffectLayer>` of labeled marks (`timing.py:170–179`). The
existing "Lyrics" track (`_lyric_track`, 123–127) is line-granular. A Papagayo-style track is the same
`Element type="timing"` but with **three** `EffectLayer` children — phrases, words, phonemes — which the
current `TimingTrack(name, marks)` (one flat list) cannot express. That is the extension point.

**Faces is excluded from placement, by design.** `constants.py:9`:
`ASSET_BOUND_TYPES = frozenset({"Faces","Pictures","Video","Shader","DMX"})` — "settings reference external
resources not guaranteed to exist in a target sequence." For Faces those references are (a) the model's
face definition (the `faceInfo` mapping in `rgbeffects.xml` — which nodes/submodels form each mouth shape,
eyes, outline) and (b) a timing-track name to drive the phonemes. The extractor skips them at mining
(`xsq_extractor.py:78–80`), so there is no `Look`, and `place_preset`'s `get_look` would raise `KeyError`.
F-B's `build_faces_settings` + `place_direct` is the designed route; its builder deliberately requires
verified references (F-B §3.2/§3.5 ring 2).

**Hardware honesty: this layout has no singing faces.** Spec §2: role `SINGING_FACE` ("Singing faces /
talking props — Custom with face submodels"), class `SPECIAL`: "singing faces. Excluded from general
choreography; driven by dedicated face tracks only." §5: "SEM_ALL — every model except SINGING_FACE and
SIGN … Do not put SINGING_FACE models into any SEM_ group except where explicitly listed." Name heuristics
(§3): "face, sing, carol, mouth → SINGING_FACE." Code implements the quarantine only:
`layout_semantics._NON_ENSEMBLE = ("SINGING_FACE","SIGN")` (line 47) excludes the role from every ensemble
group, and `_ROLE_GROUP` (43) has no SEM_ group for it. The actual layout `tests/fixtures/getModels.json`
lists `Arches, Matrix, Mega Tree, House Outline` (+ two groups) — no face-named prop, and no `faceInfo`
handling anywhere. **Consequently every rendering deliverable of F-D is conditional on hardware.** Not
conditional: the phoneme extractor, the multi-layer timing-track writer, the Faces settings builder, and
the gating logic — all buildable and hermetic-testable now; the phoneme track is independently useful
(hand-editable `.xsq`, exactly what a human imports from Papagayo). Realistic landing: ship track + builder
+ gated pass; the pass no-ops on this layout until a face prop with a definition appears. (Technically a
Faces effect can render on a matrix/mega-tree with a face definition drawn for it — if a user ever defines
one on the Matrix, the same pass lights up unchanged.)

## Goals / Non-Goals

**Goals:**
- Emit sparse, grounded narrative Text on the matrix model (title card + ≤4 featured lyric phrases +
  optional outro), never behind the focal kaleidoscope, splice-safe under regen.
- Extract deterministic phoneme timing from already-aligned word spans and write a Papagayo-shaped 3-layer
  "Lyric Phonemes" timing track into every vocal `.xsq` (independent user value even without faces).
- Place phoneme-driven Faces on singing-face props over sung regions when hardware + a face definition
  exist; no-op cleanly and log otherwise.
- Everything except the two live-verify stages is hermetic (pure functions / fake clients), with
  negative-space cases (instrumental, no matrix, no face) as first-class tests.

**Non-Goals:**
- Full lyric captioning / section-label text ("VERSE 2") — excluded by doctrine (text is punctuation).
- Inventing captions or lyrics not present in the brief/analysis (grounding rule).
- The cookbook masked-texture "1 is Mask" premium recipe for Text — deferred to v2.
- Montreal Forced Aligner / acoustic phone alignment — deferred unless proven needed on real props.
- Full "singer owns focus" choreography for faces — v1 is a gentle brightness multiplier only.
- Building F-B (asset-bound placement) — a separate change and a hard dependency.

## Decisions

### D1 — F-C: deterministic pass over existing brief fields, not a new Director field
`place_matrix_text` runs inside `generate_instructions` after the per-section loop (beside
`place_triggers`/`key_moment_flashes`, `generate.py:256–258`). Content and times come from the brief; LLM
judgment is already spent there.
- **Alternative A (Director chooses via a new `SectionPlan`/`KeyMoment` field, e.g. `KeyMoment.text`).**
  For: matches "LLM chooses intent"; could phrase-pick creatively (a word, not a line). Against: schema +
  prompt churn + cached-brief invalidation for judgment already in the brief (the panel's lyric analyst
  curated `featured_lyric_moments` with timestamps and a `why`); duplicates a decision and adds a
  hallucination surface (text not in the song).
- **Chosen B (deterministic pass over existing brief fields).** Zero schema change; grounded by
  construction (only strings in `featured_lyric_moments`/`identity` can appear); testable as a pure
  function; consistent with the judgment-vs-realization split (same reasoning as improve-musicality
  decision 6: "no new Director round-trips … deterministic post-pass"). Cost: can't invent a clever
  caption; section labels would be literal — mitigated by simply not using them.
- **Forward-compatible escape hatch:** if a `KeyMoment` of kind `"lyric"` ever gains a `text` field (one
  defaulted string, cheap to add later), the pass prefers it over its own selection — Director-chosen
  captions without blocking on prompt work.

### D2 — F-C: resolve the matrix by name, target the model not the group
`find_matrix(model_names) -> str | None` picks a model whose name contains "matrix" (case-insensitive),
mirroring `_ORDER_TIERS`' focal test; `None` → the whole pass no-ops (layouts without a matrix skip F-C).
The pass needs model names, not group names: add a best-effort `st.model_names = await
client.get_model_names()` beside the `targetable_groups` call in `run_pipeline` (`run.py:386`), wrapped in
the usual `except Exception` posture, or pipe through `State`. **Never place Text on `SEM_FOCAL`** (a group
canvas spanning matrix + mega tree would mangle glyphs). Longer-term F-E's manifest (`has_matrix`/node-count)
replaces the heuristic; until then this matches the one already shipped in `canonical_order`.

### D3 — F-C: content doctrine — text is punctuation, in priority order with a cap
Do not caption the song (a matrix that talks all night is a chyron). Rules:
1. **Title card** — `identity.title` (+ artist if it fits) once, in the intro, static or slow scroll,
   ending ≥ 1 bar before the first downbeat-anchored section boundary. Skip if the intro is < 8 s or the
   title is empty.
2. **Featured lyric phrases** — each `FeaturedLyricMoment` whose span cross-checks against the aligned
   lines (`sa.lyrics["lines"]`): snap the Text span to the matched line's start/end on a fuzzy match; if the
   moment matches no aligned line, **drop it** (never guess a time). Cap: `MAX_TEXT_MOMENTS = 4` lyric
   phrases per show, ≥ `TEXT_SPACING_MS = 20_000` apart, ≤ one per section, **none inside the peak section**
   (the peak belongs to the composite payoff).
3. **Outro sign-off** (optional, config-gated) — a short "Merry Christmas"-class message only if the brief's
   `key_moments` contain a lyric-kind moment in the final section; v1 may ship without this.
**Non-sources:** section labels ("CHORUS"); full lyric captioning; anything not verbatim in the
brief/analysis (grounding rule, mirroring the Director prompt's "do NOT invent lyrics"). **Instrumental
behavior:** with no `featured_lyric_moments` and no aligned lines, only the title card survives — acceptable
and desirable (same signal as the instrumental flag, `director.py:24`).

### D4 — F-C: Text settings anatomy via F-B's builder
The pass emits `EffectInstruction`s with `direct_settings = build_text_settings(...)`. Choices keyed to
low-res-matrix readability: `E_TEXTCTRL_Text` = title/phrase (≤ ~24 chars or scrolled; comma/equals
sanitization per F-B); `E_CHOICE_Text_Dir` = `none` (static) for the title, `none` if it fits width else
`left` scroll for phrases (static beats scrolling; scroll only when forced); `E_TEXTCTRL_Text_Speed` sized
so one full traverse ≈ the phrase's aligned duration (scroll-once rule — text that loops twice reads as a
glitch); font/size = bold, ≥ 10–12 px glyph height but ≤ matrix height − 2 (probe dims once via
`client.get_model("Matrix")` `parm1/parm2`, cf. `tests/fixtures/live/getModel.Tree.json`, or hardcode for
this layout with a TODO for F-E's manifest); `palette_colors` = the section palette's **lightest** color
(reuse `beats._lightest_hex`) over a dim background (same logic as `feature_prop_contrast`); `render_style`
= `"Default"` (single-model buffer; never a group canvas).

### D5 — F-C: coexist with focal duties (on-top, Max blend, background dim, peak exclusion)
The matrix is likely `SEM_FOCAL`'s biggest member. Rules: **render order already favors us** (focal tier
renders late; placing Text on the model row keeps it visually above group rows resolved by
`patch_xsq_render_order` at finalize); **Text rides on top** — emit with `on_top=True` (`show_plan.py:78`,
the punch-through mechanism, top layer, exempt from `clamp_layer_budget`) so `_top_layer` places it above
overlapping layers, plus `T_CHOICE_LayerMethod: "Max"` in `extra_settings` so glyph pixels add over the
busy background instead of black-boxing it; **calm the background during text** — dim concurrent
matrix-targeted non-text instructions (multiply `C_SLIDER_Brightness` by ~0.4, floor via `brightness_setting`),
the catalog's Faces rule applied to glyphs, and **never dim other props, only the canvas behind the
letters**; **keep out of the peak** so Text never collides with the curated composite on `HERO_GROUP`; **QA**
— Text is not in `rules.FEATURES` nor `ENERGY_BAND` (objectively unconstrained) so add one advisory in
`qa/variety.py`-style if text moments exceed the cap. v2 option: the cookbook "1 is Mask" recipe — deferred
until the plain version verifies live.

### D6 — F-C & F-D: section-index tagging + marker-key idempotence for splice-safe regen
Each instruction carries the owning section's `section_index`, so `replace_section` (`refine.py:48–54`)
drops-and-recreates them when that section regenerates — meaning both passes must re-run after
refine-loop/`xlo regen` splices, exactly like improve-musicality's transitions pass (decision 5), and be
idempotent the same way. For Text: a marker key in `extra_settings` (`X_MatrixText=1` — stripped before
emit or tolerated as an unknown key xLights ignores; verify in the F-B probe) lets the pass replace its own
prior output instead of stacking. For Faces: the pass fully owns all Faces-type instructions (filter-and-
rebuild). Sequence the Text implementation after improve-musicality Phase 3 lands `place_transitions` and
copy its splice-hook pattern.

### D7 — F-D: phoneme extraction via G2P lookup + heuristic distribution (not a forced aligner)
- **Chosen A (G2P lookup + heuristic distribution).** CMUdict lookup (via `g2p-en` or `pronouncing`;
  g2p-en falls back to a trained model for OOV) → ARPAbet per word → map ARPAbet → Papagayo set →
  distribute across the word's already-aligned Whisper span. New deps: one small pure-Python package +
  bundled CMUdict (~4 MB). Accuracy: word boundaries exact (Whisper-aligned), intra-word phoneme boundaries
  approximate. Failure mode: slightly early/late mouth shapes within a word (tens of ms at yard distance).
  Fit: matches graceful-degradation posture; hermetic-testable (dict lookup deterministic).
- **Alternative B (Montreal Forced Aligner).** Acoustic model force-aligns audio + transcript to phone-level
  timestamps directly. Against: Kaldi-based, conda-distributed, model downloads, heavy native deps — hostile
  to the uv workspace and CI; whole-pipeline fragility; alignment failures on separated stems with bleed;
  overkill until someone can see the difference on a real prop.
- **Recommendation: A now, B never-unless-proven-needed.** Community practice calibrates this: hand
  sequencers use Papagayo/xLights' own "breakdown words" (dictionary lookup + even distribution) and it
  reads fine. The distribution heuristic beats uniform: weight vowel-class phonemes (AI/E/O/U/WQ) ~2×
  consonant classes (MBP/FV/L/etc) within the span (vowels carry sung duration); insert `rest` in inter-word
  gaps > ~120 ms. The committed, unit-tested `_ARPA_TO_PAPAGAYO` table (39 ARPAbet → 10 Papagayo) is
  judgment-free realization. Papagayo set: `AI, E, etc, FV, L, MBP, O, rest, U, WQ` (`rest` = closed mouth
  between words, `etc` = consonant catch-all).

### D8 — F-D: vocal-songs-only gating (three computable gates)
The pass runs only when all hold: (1) **vocal song** — `sa.lyrics["lines"]` non-empty with word spans (the
signal that flips the instrumental flag; cf. `director.render_input`'s
`instrumental = not brief.featured_lyric_moments and not brief.narrative_summary`, `director.py:24` — but
prefer the analysis-side signal: aligned words are what the track is built from); (2) **singing prop
present** — a model nameable as `SINGING_FACE` (spec §3 heuristics: face/sing/carol/mouth) **and** carrying
a face definition, detected by a new `face_definitions(rgb_path) -> dict[str, list[str]]` parsing `faceInfo`
in `rgbeffects.xml` (home: `knowledge/layout_semantics.py`, beside the other rgbeffects readers) — no
definition → no Faces, ever (references verified, never invented, F-B ring 2); (3) **track scheduled** — the
run will write the phoneme track at finalize (`timing_tracks=True`, save path known) since the placed effect
references it by name. Instrumental songs skip at gate 1 with one degradation-log line (roadmap I5 style);
this layout skips at gate 2 today.

### D9 — F-D: extend the finalize timing path for multi-layer tracks
`TimingTrack` gains `layers: list[list[TimingMark]] | None = None` (or a sibling `MultiLayerTimingTrack`) —
when present `patch_xsq_timing_tracks` emits one `<EffectLayer>` per layer instead of the single layer at
`timing.py:175`; existing single-layer tracks untouched (back-compat by default value). New builder
`_phoneme_track(sa, end_ms) -> TimingTrack | None`: name `"Lyric Phonemes"`, three layers — phrases (the
aligned lines, reusing `_lyric_track`'s marks), words (per-word spans), phonemes (`phonemes.phoneme_marks`)
— the exact Papagayo import shape. Appended to the candidate list in `build_timing_tracks` (`timing.py:134–141`),
inheriting idempotent replace + atomic write for free.

### D10 — F-D: the ordering wrinkle (live placement vs offline track) resolves by name-binding
Effects are placed live during generation, but timing tracks are patched offline after save
(`finalize.py` — live timing edits crash xLights). So the placed Faces effect references a track that does
not exist in the open sequence yet. Acceptable: the settings string binds by **name**; when the user opens
the saved `.xsq` the track (patched moments after save) resolves and the faces sing. Cost: **in-run renders
— visual critic, coverage sampler, RealRender — never see mouth movement**, only whatever the effect renders
trackless (typically rest/outline). Mitigations: (a) faces are `SPECIAL`-class and excluded from choreography
QA anyway — coverage/variety must ignore the face prop (already outside every SEM_ ensemble); (b) the
acceptance eyeball happens on the finalized file (live-verify checklist). Alternative — patch the Faces
*effect* itself offline at finalize after the track — is sketched in Open Questions; v1 keeps live placement
for emitter uniformity.

### D11 — F-D: placement pass shape and surrounding-dim
`pipeline/faces.py::place_faces(st, face_models: dict[str, str])`: one Faces instruction per singing-face
model per **sung region** (aligned line spans merged with ≤ 2 s gaps), not the whole song — faces close and
go dark in instrumental breaks. `direct_settings = build_faces_settings(timing_track=PHONEME_TRACK_NAME,
face_definition=face_models[model], ...)`; `on_top=True` (a face must never sit under a wash; ensembles
exclude it by construction, but an explicit Generator instruction could still target it). Companion catalog
rule — during sung regions dim surrounding props to ≤ 30%: v1 scopes this to a gentle brightness multiplier
on concurrent `SEM_ALL`-bed instructions only (full "singer owns focus" is a later refinement interacting
with improve-musicality's treatments). `face_models: dict` signature already permits multiple faces/duets.

## Risks / Trade-offs

**F-C:**
- Glyphs illegible at the matrix's real resolution → enforce the catalog floor (≥10–12 px glyph height) from
  probed matrix dims; live-verify eyeball is an explicit checklist item; if the matrix is under ~50 px the
  pass refuses (catalog rule #2) and logs a degradation.
- Text fights the focal choreography (kaleidoscope behind words) → peak exclusion; `on_top` + Max blend;
  background dim to ≤ ~40% during text spans; one-per-section cap.
- Wrong-time text (brief timestamps drift from the audio) → grounding rule: snap to the aligned lyric line or
  drop the moment; never trust brief times alone.
- Over-captioning creeps in (each future feature adds "just one more" text source) →
  `MAX_TEXT_MOMENTS`/`TEXT_SPACING_MS` as named dials in `pipeline/tuning.py`; advisory QA finding when
  exceeded; doctrine documented.
- Regen splices duplicate or orphan text moments → section-index tagging + marker-key idempotence, copied
  from (and tested like) the transitions pass.
- Layout has no matrix / a renamed matrix → `find_matrix` returns None → clean no-op + degradation log line;
  F-E's manifest later replaces the name heuristic.
- Comma/equals or non-ASCII in lyric text corrupts the settings CSV → F-B's sanitizer + property test;
  phrases failing sanitization are dropped, not mangled.

**F-D:**
- No hardware to verify on — the feature ships dark → stages 1–3 deliver standalone value (Papagayo-shaped
  track in every vocal `.xsq`); the pass is gated + logged, not assumed; stage 5 is an explicit conditional
  milestone; set expectations in the PR description.
- Faces effect placed before its timing track exists (live-render blindness) → by-name binding resolves at
  file open (D10); faces excluded from QA/critic expectations; finalized-file eyeball is the acceptance gate;
  fallback design (offline effect patch) sketched if live placement misbehaves.
- Whisper word timing drifts on melisma/held notes → mouths linger or snap early → vowel-weighted
  distribution absorbs most of it (the held phone is usually the vowel); alignment already discards weak
  matches (`min_ratio=0.55`, whole-run bail at <25% lines); if visible on hardware, revisit with MFA (D7 B).
- G2P dependency friction (model download in g2p-en's OOV path) → prefer dictionary-only lookup
  (`pronouncing`/raw CMUdict) with `etc` fallback for OOV — zero downloads; upgrade to g2p-en only if OOV
  rate proves high.
- Face prop accidentally receives choreography (washes over a singing face) → already structurally excluded
  from every SEM_ ensemble (`_NON_ENSEMBLE`); pass adds `on_top=True`; add a placement-rules advisory if any
  non-Faces instruction targets a SINGING_FACE model.
- Timing-track name collision with a user's own track → `patch_xsq_timing_tracks` replaces only same-named
  tracks we own; `PHONEME_TRACK_NAME` ("Lyric Phonemes") is distinctive; documented in usage.md.
- Papagayo label set drifts across xLights versions → labels frozen from the same pinned-version probe as the
  settings template; live template validation re-run on upgrades (F-B protocol).

## Migration Plan

- **Hard dependency:** land `add-asset-bound-placement` (F-B) first — `build_text_settings`,
  `build_faces_settings`, the `direct_settings` field, the emitter's asset-bound branch, and the frozen
  Text/Faces templates. Sequence the F-C Text pass after improve-musicality Phase 3 lands `place_transitions`
  and copy its splice-hook pattern.
- **Golden:** the fixture brief is instrumental-shaped and the fixture layout has no faces → expected golden
  impact is nil (F-D) or a title card only (F-C). Regenerate with `XLO_REGEN_GOLDEN=1` only if it changes and
  review the diff; for F-D any golden diff on the fixture is a bug, not a regeneration case.
- **New dependency:** add `pronouncing` (or `g2p-en`) to `xlights-core` (optional `lyrics` extra); heavy
  import deferred inside functions, mirroring `lyrics_align._transcribe`.
- **Back-compat:** the multi-layer `TimingTrack` defaults to single-layer behavior, so existing timing-track
  writers and archived tracks are untouched.
- **Docs:** note the text doctrine (punctuation, caps, non-sources) and the "Lyric Phonemes" track /
  faces gating in `docs/usage.md`; cross-link craft-roadmap items 7 (faces half) and 8 (matrix text) as
  closed.

## Open Questions

**F-C:**
- Matrix pixel dimensions: probe via `get_model` at run time vs a one-line layout constant until F-E's §6
  manifest exists? (Probe is ~free and self-maintaining; recommend probe with constant fallback.)
- Masked-texture recipe (Text "1 is Mask" over Bars — cookbook SC) as v1 or v2? Recommend v2: it doubles the
  layer choreography and the plain bright-on-dim version must be proven legible first.
- Outro sign-off content: config option (`xlo` flag / brief field) or omit in v1?
- Later Director hook: add `KeyMoment.text` so the LLM can hand-pick a word ("HALLELUJAH" not the whole
  line)? Cheap and back-compatible; decide after watching v1 output.
- Does the white `key_moment_flashes` flash on `SEM_ALL` visually stomp a concurrent text moment (the matrix
  is in SEM_ALL)? If live verify says yes, exclude flash overlap in selection.

**F-D:**
- Should the Faces effect also be patched offline at finalize (after the track) instead of placed live —
  trading live-render blindness for a second offline-patch pathway? v1 keeps live placement for emitter
  uniformity; revisit if the trackless in-run render looks wrong in review bundles.
- Dictionary choice: `pronouncing` (pure CMUdict, zero downloads, OOV → `etc`) vs `g2p-en` (neural OOV
  fallback, model download). Leaning `pronouncing` for CI hygiene — measure OOV rate on real lyric corpora
  first.
- Where does surrounding-dim live long-term — this pass, or improve-musicality's treatment system (a
  `feature`-like "vocal focus" treatment)? v1: local multiplier; revisit after F-A Phase 2.
- Should the phoneme track write even for layouts without faces (pure hand-editing value) — decouple stage 2
  from the feature flag entirely? Recommend yes (stage-2 default); confirm no xLights UI clutter objection.
- Multiple singing faces (duets): round-robin lines across props, or all props sing everything? Defer until
  hardware exists; the `face_models: dict` signature already permits both.

## Notes

- Dependencies / provenance references preserved from both docs: F-B asset-bound placement (builder, schema
  field, emitter branch, probe protocol, reference-verification rings); improve-musicality decision 5 (the
  splice-safe list-pass pattern this copies) and decision 6 (deterministic post-pass, no new Director
  round-trips); F-E's future layout manifest (`has_matrix`/node-count/pixel dims) that will replace the
  name heuristics; archive changes `2026-06-11-add-lyric-alignment`, `2026-06-14-add-melodic-triggers`,
  `2026-06-13-add-trigger-effects`, `2026-06-09-add-timing-tracks`, `2026-06-17-extend-downbeat-cuts-to-lyric-path`,
  `2026-06-08-add-effect-presets` (the mining exclusion's origin).
- Roadmap provenance: `docs/roadmap-2026-07.md` Horizon 2 F-C and F-D; June scorecard rows F1 (Matrix Text)
  and F2 (Faces); sequencing table row 6 ("F-B + F-C … closes the craft roadmap's biggest gap");
  `docs/roadmap-2026-06.md` §F2. Craft roadmap `docs/craft-roadmap.md` item 8 (`matrix-narrative-text`) and
  item 7 (`lyric-driven-effects` — "Needs phoneme-level timing … Instrumental songs skip entirely").
- Guides: `xlights-effects-catalog.md` §8 Text (+ §9 rule #2) and §8 Faces (anatomy + ≤30% dim rule);
  `xlights-scene-cookbook.md` masked-reveal and SC-08 ("the matrix is the storyteller");
  `xlights-layout-semantics-spec.md` §2 (MATRIX 2D_SURFACE, SINGING_FACE SPECIAL), §3 (name heuristics), §4
  step 6 (focal flag), §5 (single-instance roles addressed directly, ensemble exclusion).
