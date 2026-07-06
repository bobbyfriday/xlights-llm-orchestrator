## Context

This change designs the two **shared placement primitives** the July-2026 roadmap's narrative and
layout-generalization features build on. Both start from a correct-but-limiting current design.

**F-B — the exclusion, in three layers (current state).**

- **Layer 1 — mining.** `knowledge/constants.py:9` defines
  `ASSET_BOUND_TYPES = frozenset({"Faces", "Pictures", "Video", "Shader", "DMX"})` — "effect types
  whose settings reference external resources not guaranteed to exist in a target sequence. Excluded
  from mining." `knowledge/xsq_extractor.py::extract_file` (lines 73–89) skips them at the source, plus
  a subtler filter: any effect whose settings carry an *active timing-track value curve* is skipped too
  (`_has_active_timing_track_curve`, lines 51–56, built on `settings.classify_value_curve` /
  `constants.is_timing_track_curve_type`). The committed catalog's `presets/looks.json` meta records
  the cost: `"skipped": {"asset_type": 453, "timing_track_vc": 197}` across the 17-file corpus. Nuance
  the roadmap wording papers over: **`Text` is not in `ASSET_BOUND_TYPES`** — it simply never survived
  mining (community Text is typically lyric text bound to timing tracks, caught by the second filter,
  or absent from this corpus's top-level files). The committed catalog's 37 `looks_by_type` keys
  include neither `Text` nor `Faces`. Either way the practical effect is identical: no `Look`, no
  placement.
- **Layer 2 — agent vocabulary.** `agents/catalog.py::placeable_effect_types()` (line 15) is
  `get_library().list_effect_types()` minus `KNOWN_REJECTED_TYPES` — so the Director and Generator are
  never offered Text/Faces, QA's `ENERGY_BAND` has no entries for them, and `weave.canon_effect_type` /
  `beats._accent_look` (guarding on `candidate_look_ids(effect_type)` being non-empty) silently drop or
  fall back if an LLM hallucinates one. This defense-in-depth is good and stays: F-B does **not** add
  these types to the LLM's free-choice menu.
- **Layer 3 — placement.** Every placement goes through `editing.place_preset` (`editing.py:35–94`),
  whose first act is `look = lib.get_look(effect_type, look_id)` (raises `KeyError` for Text/Faces) then
  `settings = lib.assemble(look, knob_values)` (validates knobs per constraint). In
  `effect_emitter.apply_instructions`, `KeyError` is in `_SKIPPABLE` (line 16), so an unmined type is
  quietly recorded in `skipped`. There is no path by which an `EffectInstruction` can deliver a settings
  string that didn't come from a mined `Look`.

**F-B — seams reused (current state).** `place_preset`'s override mechanics (`editing.py:67–78`):
`extra_settings` entries override same-keyed pairs (first-occurrence-wins handled) and append the rest;
values may contain `|` (value curves) but never `,`, so comma-splitting is safe. Palettes are already
look-independent (`colors.palette_from_colors` builds `C_BUTTON_Palette1..N=,C_CHECKBOX_Palette1..N=`).
The wire format is trivial (`client.add_effect(target, effect, settings, palette, layer, start_ms,
end_ms)`, `client.py:223–244` — opaque settings). The parser round-trip exists
(`knowledge/settings.py::parse_settings`/`serialize_settings`, lines 13–30; `constants.classify_kind`,
key-prefix → slider/choice/checkbox/valuecurve/text). The scratch-sequence validator exists
(`editing.validate_preset`, lines 97–177). Buffer style stays orthogonal (`resolve_buffer_style` injects
`B_CHOICE_BufferStyle`, `effect_emitter.py:113–114`, regardless of provenance).

**F-F — current state.** There is **no submodel handling anywhere in the packages**, plus one guard that
actively blocks it. The spec preserves but doesn't use them:
`xlights-layout-semantics-spec.md` §1 lists "`<subModel>` children (named pixel subsets, preserve
these)"; §5.6 sketches the deliverable — "Do not flatten submodels. If `OUTLINE` models have submodels
(Roof_Left, Peak, Garage_Line), additionally create `SEM_OUTLINE_SEGMENTS` containing the submodels in
left-to-right order to enable section-by-section builds." (line 173). The 2026-06-10
`add-layout-semantics` change explicitly listed "submodel `SEM_OUTLINE_SEGMENTS`" as a non-goal.
`layout_semantics.py` has no submodel concept: the `Prop` dataclass (lines 23–40) carries no submodel
field; `build_sem_groups()` (line 50) plans groups of model names only (the F-E design adds
`Prop.submodels` as a forward seam). The preview parser skips them:
`preview/layout.py::parse_models()` (line 113) iterates `models_el.findall("model")` and never reads
`<subModel>` children. The write path rejects submodel targets today —
`editing.py::place_preset()` (lines 83–84): `if target not in await client.get_models(): raise
ValueError(...)`, and `client.get_models()` (`client.py:147`) returns model and group *names* only, so
even if xLights' `addEffect` accepted a submodel element, this client-side guard raises first. Every
effect flows through `place_preset` (`effect_emitter.py:62`), so this is a single choke point. The
targetability probe covers groups only (`pipeline/groups.py::targetable_groups()`, line 35, probing
`get_group_names()`) — but that is exactly the right tool to extend ("probing beats parsing"). A partial
workaround exists: the layering guide's *Sub-Buffer* row (line 98) fakes zones per-effect, unnamed and
unordered (§3.6 alternative).

**The honest conditionality.** `docs/craft-roadmap.md` line 11: "this user's `rgbeffects.xml` has **0
SubModels** → submodel work is DEFERRED"; item 9 (line 74) marks the change deferred for exactly that
reason. Nothing in F-F benefits the current layout; it activates only when F-E onboards a layout that
has submodels, or when this user adds them (the layering guide line 272 contemplates defining a scheme).

## Goals / Non-Goals

**Goals:**
- A second placement route (F-B) for the narrow set of asset-bound effects we actually want (Text now,
  Faces next): templates in code, external references bound to resources we own, syntactically
  validated, carried through the existing emitter — reusing every proven mechanism.
- Text/Faces never enter the LLM's free-choice menu; only deterministic passes author direct settings.
- Submodel targeting (F-F) captured now so the F-E classifier leaves the right seams: discovery,
  ordered/singleton grouping, and choreography hooks, all cheap-and-hermetic where possible and gated
  where hardware is required.
- Byte-identical output on layouts with 0 submodels — a permanent regression guard.
- Deterministic and code-owned wherever possible; probing beats parsing for anything not derivable from
  the XML.

**Non-Goals:**
- **F-B:** no Pictures/Video/Shader/DMX support (§3.6 explicit); no addition of Text/Faces to the mined
  catalog or to `placeable_effect_types()`; no changes to `run.py`, QA scoring, or any agent prompt; no
  synthesized *non-asset* strings (keep `DIRECT_TYPES` minimal — the catalog is the source of truth for
  anything minable).
- **F-F:** no new audio analysis for v1 (drum-kit mapping uses beat-grid structure, not per-drum
  separation; a kick/snare spectral split is a deferred analyzer follow-up); no default-on submodel
  behavior before the phase-3 hardware gate; Sub-Buffer zone-splitting stays a deferred escape hatch,
  not the primary mechanism; no Route-A dependence (Route B is the critical path).

## Decisions

**F-B / 1. Principle: templates in code, references we own.**
A "direct effect" is an effect whose settings string is built by a code-owned template — a curated,
hand-verified analogue of a mined `Look` — where every external reference points at a resource the
pipeline itself creates or verifies. **Text:** no external file at all when using OS font rendering; the
only "asset" is the glyph content (a plain settings value) — fully self-contained, the easiest case and
why F-C is the first consumer. **Faces:** two external references — the target model's *face definition*
(lives in the user's `rgbeffects.xml`; must be detected, never invented) and a *phoneme timing track*
(which F-D's pipeline itself writes, so the name is ours) — placeable only when both exist, gated.
**Pictures/Video/Shader/DMX:** explicitly OUT (§3.6). *Alternative rejected:* "stop excluding them from
mining" — the mined guarantee cannot extend to out-of-string references; a mined Text look whose value
curve reads "Timing Track: Verse 1" silently renders nothing in our sequence.

**F-B / 2. New module `knowledge/direct_settings.py` with `DIRECT_TYPES = {"Text","Faces"}`.**
Owns per-type templates and builders. `build_text_settings(text, *, movement="none", font_size=12,
bold=True, speed=10, center=True) -> str` (movement validated against `_TEXT_DIRS`; font_size clamped
to matrix height upstream). `build_faces_settings(*, timing_track, face_definition, eyes="Auto",
outline=True) -> str` — **requires** both reference arguments, performs no defaulting (a dangling
reference renders a blank prop). Text keys emitted (self-describing `E_*` scheme, all understood by
`classify_kind`): `E_TEXTCTRL_Text` (text — the one mandatory key), `E_FONTPICKER_Text_Font` (other —
legacy wx font descriptor at default), `E_CHOICE_Text_Font` ("Use OS Fonts"), `E_CHOICE_Text_Dir`
(none/left/right/up/down + vector variants), `E_TEXTCTRL_Text_Speed`, `E_CHOICE_Text_Effect` ("normal";
vert/rotate out of scope v1), `E_CHOICE_Text_Count` ("none"; countdown out of scope v1),
`E_CHECKBOX_TextToCenter`, `E_SLIDER_Text_XStart`/`E_SLIDER_Text_YStart` (default 0). Faces keys:
`E_CHOICE_Faces_TimingTrack`, the face-definition choice key observed in the probe
(`E_CHOICE_Faces_FaceDefinition` in current builds), phoneme source mode, eyes, outline.

**F-B / 3. Verification protocol: a corpus of one.**
Key names drift across xLights versions and must not be trusted from memory. Author one Text effect
(one static, one scrolling) by hand in the *pinned* xLights version, save, read the settings string out
of the `.xsq`'s `EffectDB` via `parse_settings` (a five-line script) — the observed string becomes the
frozen template committed as a fixture; the builder only varies the documented knobs. This is exactly
how the mined catalog earns "valid by construction," applied to a corpus of one hand-authored probe.
The `DROP_KEYS` mechanism (`editing.py:22`) is the precedent for stripping stale/version-gated keys.
Same protocol for Faces (semantics per the F-D design doc).

**F-B / 4. Carrying it: `EffectInstruction.direct_settings: str = ""` (schema addition).**
Add one defaulted field to `EffectInstruction` (`show_plan.py:63–80`); when non-empty the emitter
bypasses the preset library entirely, and `look_id=""` is allowed. Defaulted → cached instruction lists
(`instructions` stage cache, golden fixture) validate unchanged. The generator LLM is **not** told about
the field (not in any prompt). QA treats a direct instruction like any other (real target/effect_type/
span); `rules.ENERGY_BAND` simply has no entry for Text/Faces, which means "unconstrained" by
construction (`qa/rules.py:15` comment). *Alternative rejected:* a magic `look_id="direct:…"` sentinel —
saves a field but hides a load-bearing behavior switch inside a string convention, and `look_id` is
threaded through logging, review bundles, and skip reasons where the full settings string would be
noise.

**F-B / 5. Placement: `editing.place_direct` + emitter branch, sharing helpers.**
`place_direct(client, target, effect_type, settings, *, palette_colors=None, extra_settings=None,
layer=0, start_ms, end_ms) -> str` — a sibling of `place_preset` that skips assembly but keeps every
guard: validates the settings string syntactically (`parse_settings` round-trip, known key kinds),
merges `extra_settings` with the same first-occurrence-wins override, resolves the palette via
`palette_from_colors`, then `add_effect`; raises `PresetPlacementError` on `worked=false`, `ValueError`
on bad timing/target. The extra-settings merge loop and the timing/target guards are **extracted** from
`place_preset` into private helpers (`_merge_extra_settings(settings, extra)`,
`_check_timing_and_target(...)`) both functions call — no behavior change to the preset path, provable
by the existing `tests/test_editing.py` and the golden test. `effect_emitter.apply_instructions`
branches per instruction (around line 116): `if ins.direct_settings: await place_direct(... extra_settings=extra
...)` (still carries `B_CHOICE_BufferStyle`) `else: await place_preset(...)` (exactly today's call). Layer
accounting (`_free_layer`/`_top_layer`/occupancy) and `_SKIPPABLE` handling are identical for both
branches — a failed direct placement degrades to a logged skip, same best-effort posture as the rest of
the emitter.

**F-B / 6. Validation: three rings.**
(1) *Syntactic (hermetic, every build):* `serialize_settings(parse_settings(s)) == s`; every key
classifies to a known kind via `classify_kind` (no `"other"` except the audited font-picker key); no
active timing-track value curves unless the builder deliberately bound one — reuse
`_has_active_timing_track_curve`'s logic, **inverted** for Faces (the track reference is *required* and
its name must equal the track the run writes). (2) *Reference (hermetic for Text, gated for Faces):*
Text needs none; Faces needs `face_definitions(rgb_path, model) -> list[str]` (proposed helper in
`knowledge/layout_semantics.py` or a new `knowledge/faces.py` — parses `rgbeffects.xml` `faceInfo`
elements) to return the referenced definition, and the timing-track name must be one the pipeline
schedules for writing. (3) *Live (opt-in, `-m live`):* `validate_direct(client, effect_type, settings)`
mirrors `validate_preset`'s scratch-sequence protocol (clean slate → place → `render_all` → discard),
used once per template per xLights upgrade, not per run.

**F-B / 7. Explicitly out of scope: Pictures, Video, Shader (and DMX).**
Pictures/Video embed *file paths* — a real feature needs asset acquisition, show-folder copying, path
rewriting (the catalog doc warns "imports break paths; fix via Bulk Edit Path"), resolution gating
(<~50 px canvases turn detailed imagery "to mush"), and content curation — a full asset-management
subsystem with no LLM-pipeline leverage until we have assets worth showing. Shader references `.fs`
files (same asset problem), heavy render cost, per-GPU behavior differences the offline preview renderer
cannot reproduce — validation story doesn't exist. DMX is device-bound by definition; this layout drives
pixels. The design keeps the door open: each future type is one more builder in `direct_settings.py`
plus its reference ring — no new plumbing — but `DIRECT_TYPES` is the allowlist and adding to it
requires a new OpenSpec change.

**F-F / 8. Discovery during F-E classification (verifiable today).**
Submodel discovery extends the F-E classifier's `parse_props()`, not a new pass. New `SubModel`
dataclass (new dataclass in `layout_semantics.py`; parsed by `knowledge/layout_classify.py`): `name`
(e.g. "Ring 1", "Roof_Left"), `parent` (owning model), `node_ranges` (raw range spec, e.g.
"1-50,101-150"), `nodes` (count expanded from the ranges), `kind` (RING | ZONE | HALF | SEGMENT | ARM |
TOPPER | "" unknown), `order_hint` (trailing integer in the name — "Ring 3" → 3). XML shape: submodels
are child elements of `<model>` carrying a `name` and a node-subset definition (typically a
`type="ranges"` spec whose `line0..lineN` attributes hold comma-separated node ranges referencing the
*parent's* node indices, or a sub-buffer rectangle). Since this repo has 0 examples, the exact attribute
grammar is pinned like F-E pins group layout modes: **define one of each kind in the target xLights
build, save, and commit the diff as a fixture** before the parser merges; the parser round-trip-preserves
anything it doesn't understand (spec §1 says *preserve*; the F-E writer never touches non-`SEM_`
elements). Segment semantics follow the F-E name-heuristic pattern:
`SUBMODEL_KIND = [(("ring",),"RING"), (("zone","band","tier"),"ZONE"),
(("half","left","right"),"HALF"), (("roof","peak","garage","gutter","eave","ridge"),"SEGMENT"),
(("arm","blade","spoke"),"ARM"), (("top","topper","star"),"TOPPER")]`. Roles are **inherited** — a
submodel of an OUTLINE model is an outline segment; a RING of a MEGA_TREE is a tree zone; submodels never
get independent taxonomy roles, they refine their parent. Spatial derivation orders segments
left-to-right (SEGMENT/HALF, by mean x of their node subset once parent pixel geometry is known via
`model_world_pixels()`) or bottom-to-top (RING/ZONE, by mean y or `order_hint`). The manifest's
`PropRecord.submodels` (already stubbed as `submodels: list[str] = []` in the F-E schema) upgrades to a
list of records `{"name","kind","nodes","order"}` — a few hundred bytes, within the §6 10 KB budget.

**F-F / 9. Targeting mechanics — Route B first (the central investigation).**
Two candidate routes. **Route A — direct element target:** `client.add_effect(target="Tree/Ring 1", ...)`
— whether xLights' `addEffect` resolves submodel child elements (and under what name syntax) is
**unverified**; `place_preset`'s layout guard (`editing.py:83`) must learn submodel names (a tolerant
check — manifest lookup or a widened name set) plus whatever name syntax the API wants; new live probe
logic, unknown failure modes (`XLightsTargetMissing`? silent `worked=false`?). **Route B (recommended)
— groups with submodel members:** xLights model groups may contain submodels
(`models="Tree/Ring 1,Tree/Ring 2"` in the `modelGroup` element — the group dialog's "show submodels"
affordance); the group is then an ordinary top-level element with **no client changes** — its name
appears in `get_group_names()`, flows through `targetable_groups()`, `place_preset`, the emitter, QA,
and render-order untouched; the *existing* `pipeline/groups.py::_probe` (line 75) answers targetability
per layout, cached by fingerprint. Expressiveness is equivalent to Route A via *singleton* groups (one
submodel per group) where independence is needed and ordered multi-member groups where traversal is
needed. **Decision: Route B first** — reuses every proven mechanism (probe, write lock, emitter layer
allocation, `canonical_order`), needs zero client changes, and its one unknown ("does xLights accept
`addEffect` on a group whose members are submodels?") is answered by the probe in one disposable-sequence
pass on real hardware. Route A stays a recorded investigation (one live experiment: try `Model/Submodel`
and the bare submodel name; log status codes) because if it works it saves group proliferation for
one-off accents — not on the critical path.

**F-F / 10. `SEM_` group extensions (planning verifiable today).**
`build_sem_groups()` grows a companion `build_submodel_groups(props) -> dict[str, list[str]]` emitting
`Parent/SubModel` groups, kept separate so submodel-less layouts are byte-identical to today:
`SEM_OUTLINE_SEGMENTS` (OUTLINE submodels of kind SEGMENT, left-to-right — spec §5.6, ordered layout
mode = ordered traversal), `SEM_TREE_ZONES` (MEGA_TREE submodels of kind RING/ZONE, bottom-to-top),
`SEM_TREE_ZONE_<i>` (singleton per zone, i=1..N bottom-up — the drum-kit targets: distinct simultaneous
effects), `SEM_TREE_TOPPER` (TOPPER submodels — the cymbal), `SEM_WINDOW_CELLS` (WINDOW submodels —
independent rhythm cells). Design points: **ordering is the value** — ordered groups follow the `_LTR`
doctrine (member order = traversal order, group layout mode = the ordered mode F-E pins in its
slice-3.1 spike) so a chase draws the house left-to-right and a riser climbs the tree, direction
reversal via effect parameters (spec §5.2: no `_RTL` variants). **Singletons make the drum kit** —
placing kick/snare/cymbal *simultaneously* needs three independent targets; per-zone singletons deliver
that through Route B; cost is a handful of extra probe-verified groups, all excluded from ensemble beds.
**Ensemble hygiene** — submodel groups never join `SEM_ALL` or band/side ensembles (their parents are
already there; double membership double-renders); they slot into `canonical_order`'s `accent`/`rhythm`
tiers (`layout_semantics.py:113-124`) so zone accents win overlaps against the parent's bed.
**Manifest** — each group lands in `groups` with `ordered`/`layout_mode`, the §6 `GroupRecord` shape from
F-E, so downstream needs no new schema.

**F-F / 11. Choreography hooks (design today, verify on hardware), all `if zones`-guarded.**
**Drum-kit mapping** (`pipeline/beats.py`): extend `RhythmRoles` (line 252) with optional
`zones: list[str]` (bottom-up singleton zone groups) and `topper: str | None`. In
`place_beat_accents()` (line 296), when zones exist and the section's `follow_stem` is drums: downbeats
→ bottom zone, backbeat positions (`_backbeat_positions`, line 287) → mid zone, sparkle layer's
strongest-hit selection retargets from `ACCENT_GROUPS` to the topper. First cut needs *no new audio
analysis* — it maps beat-grid structure. A true kick/snare split (spectral band classification of
drum-stem onsets) is a separate optional analyzer follow-up, kept out of v1. **Vertical build runs**
(`pipeline/weave.py`): the weave's directional sweeps (lines 356–363 force sweep cells onto the group
buffer so motion traverses the group) work unchanged on `SEM_TREE_ZONES` — a chase-family cell with an
"up" direction on an ordered bottom-to-top group *is* the riser; the only new logic is the direction
vocabulary for zone groups mapping up/down instead of left/right. **Outline draw:** an intro-scene
recipe (scene cookbook candidate) placing a single slow chase on `SEM_OUTLINE_SEGMENTS` — pure data
once the group exists. **Director awareness:** the F-E layout block gains one line per submodel-bearing
prop ("MegaTree: 1600 nodes, 4 zones bottom-to-top + topper — zone-mapped drum accents available"), and
`pulse_groups` can name zone groups; no schema change.

**F-F / 12. Offline rendering & QA (verifiable today).**
A submodel is just a channel subset of its parent, so the offline `PreviewRenderer` validates without
hardware: parse node ranges → parent node indices → absolute channels (`start_channel + 3*node`, as
`render.py:43` computes) → synthesize frames lighting one zone/segment at a time → run the F-E
sweep-centroid check vertically for `SEM_TREE_ZONES` (centroid y strictly increasing) and horizontally
for `SEM_OUTLINE_SEGMENTS`. The F-E validator generalizes with one parameter (which axis). Coverage QA
needs nothing: submodel-group effects light parent channels, which `make_lit_sampler`
(`pipeline/visual.py:105`) already counts.

**F-F / 13. Minimal-first phased plan (see tasks.md).**
Phases 0–2 are buildable and hermetic today (fixture/parser; plan/manifest; writer + offline
validation, behind an `--submodels` flag on `xlo init-layout`). Phase 3 is a **hardware-blocked live
gate** (group load after restart, probe targetability, the Route-A experiment logged either way, one
placed chase + one riser watched) — the `--submodels` flag flips to default-on only if load + probe +
watch pass. Phase 4 is choreography (each hook lands separately, `if zones`-guarded). Phase 5 is optional
follow-ups (kick/snare spectral split, Route-A direct targeting if phase-3 passed, Sub-Buffer escape
hatch, vendor-naming import mappings).

## Risks / Trade-offs

**F-B:**
- [Setting keys drift across xLights versions; a template goes stale and renders defaults silently] →
  Templates frozen from a probe against the pinned version; `validate_direct` re-run on every xLights
  upgrade; `DROP_KEYS`-style strip list for removed keys; xLights logs `ApplySetting: Unable to find` —
  check the log in live verify.
- [Comma/equals in user-visible text corrupts the CSV `KEY=VALUE` settings string] → Builder sanitizes
  glyph text (documented substitution); property test pins it; ring-1 round-trip catches any escape
  bug.
- [The LLM starts emitting Text/Faces once it sees them in shows / review bundles] → Types never enter
  `placeable_effect_types()`; guard test asserts `DIRECT_TYPES ∩ placeable_effect_types() == ∅`;
  existing look-guards drop hallucinated types as today.
- [Direct path drifts from preset-path behavior (palette handling, override precedence)] → Shared
  extracted helpers, not copies; parity tests assert both paths produce identical merged strings for
  identical `extra_settings`.
- [A dangling Faces reference (missing face definition / track) renders a dark prop] → Ring-2 validation
  is mandatory for Faces — the builder takes verified references only; the F-D pass gates on detection,
  never invents.
- [Scope creep toward Pictures/Video asset management] → §3.6 explicit; `DIRECT_TYPES` is the allowlist
  and adding to it requires a new OpenSpec change.
- [Emitter branch introduces a regression in the hot preset path] → Branch is a two-line dispatch;
  golden test + `test_editing.py` + emitter tests must stay green with zero fixture changes.

**F-F:**
- [No submodel-bearing layout exists to verify against (the defining condition) → design drifts, dead
  code ships] → Phases 0–2 only, behind a flag, exercised purely by fixtures; phase 3 is an explicit
  gate before anything defaults on; the 0-submodel no-op is a permanent regression test.
- [xLights rejects submodel members in groups, or renders them unpredictably (echoes the group-of-group
  caution in spec §5.6) → Route B collapses] → The empirical probe answers it cheaply per layout before
  any show depends on it; fallback is Route A if the phase-3 experiment passed, else Sub-Buffer for the
  narrow cases; nothing downstream assumes success (all hooks `if zones`-guarded).
- [Submodel XML grammar mis-parsed (ranges vs sub-buffer vs future types) → wrong channels lit,
  corrupted preserve-round-trip] → Fixture authored by real xLights, not hand-written; unknown types
  preserved verbatim and excluded from planning (listed in the manifest `review`); offline channel-subset
  validation catches range math errors deterministically.
- [Group proliferation (N singleton zones × props) → probe time, sequencer clutter, prompt bloat] →
  Emit singletons only for kinds with a consumer (tree zones, topper); cap zones folded into planning
  (merge >6 rings into 3–4 zones); Director block summarizes ("4 zones") instead of listing groups.
- [Double-rendering: zone effect + parent-model effect overlap → muddy blends, occluded beds] → Same
  overlap doctrine as today: render order via `canonical_order` tiers decides winners; zone accents ride
  the accent tier; QA rule #4 merging already treats same-window gestures as one event.
- [Vendor naming diversity defeats the kind heuristics → segments unclassified → no ordered groups] →
  Same escape as F-E: low-confidence kinds → review queue + per-layout overrides file; geometry-based
  ordering works even when names don't.

## Migration Plan

Both features are strictly additive. **F-B:** `direct_settings` is defaulted `""`, so pre-change cached
instruction JSON and the golden fixture load and compare unchanged; nothing emits direct instructions
until F-C/F-D land, so the golden must not move. The `place_preset` refactor is behavior-preserving
(shared helpers, not copies) and proven by the untouched `tests/test_editing.py` + golden. **F-F:**
gated behind the `xlo init-layout --submodels` flag; a layout with 0 submodels produces zero new groups
(asserted forever), and `select_rhythm_groups` without zones is byte-identical to today (golden pipeline
snapshot unchanged). The flag defaults on only after the phase-3 hardware gate passes. No schema breakage
in either feature (`PropRecord.submodels` was already stubbed by F-E; `GroupRecord` shape reused).

## Open Questions

**F-B:**
- Should the direct path also serve *synthesized non-asset* strings someday (e.g. an effect type mined
  with too few looks)? Recommend no — the catalog is the source of truth for anything minable; keep
  `DIRECT_TYPES` minimal.
- Comma handling in glyph text: substitute (e.g. "," → " ·") or reject? Recommend substitute-with-log —
  a lyric fragment should never fail a run. Needs the probe to confirm whether xLights itself escapes
  commas in `E_TEXTCTRL_Text` when saving (if it does, mirror its escape exactly).
- Does `addEffect` accept multi-line text (newlines in a query/body value) for stacked static text?
  Probe during step 1; v1 can restrict to single-line.
- Where does the Faces reference-detection helper live — `knowledge/layout_semantics.py` (already parses
  `rgbeffects.xml`) or a new `knowledge/faces.py`? Leaning `layout_semantics.py` for cohesion; F-D
  decides.
- Should skipped direct placements surface in the roadmap-I5 degradation summary with a dedicated
  reason? Cheap once I5 lands; flag it there.

**F-F:**
- Member name syntax — the exact `models=` string for a submodel member (`Parent/Sub` is the expected
  convention; pinned by the phase-0 fixture, like F-E's layout-mode strings).
- Does `getModels` ever list submodels? If a future xLights exposes them, `place_preset`'s guard passes
  for free and Route A becomes testable without client changes — worth re-checking per version bump.
- Zone granularity policy — merge many rings into 3–4 zones (readable at distance, fewer groups) vs
  faithful per-ring groups? Leaning merge, with the ring→zone map recorded in the manifest.
- Kick/snare separation — is beat-position mapping (downbeat/backbeat) good enough for the drum-kit
  illusion, or does the spectral split of drum-stem onsets earn its analyzer complexity? Decide after
  watching phase-4 output on hardware.
- Vendor submodel import — adopting vendor-compatible naming (sequencing guide lines 223, 263) so
  purchased HD props classify cleanly: a heuristic-table growth path or an import-mapping file?
- Should this user add submodels? The layering guide (line 272) argues yes for the mega tree/spinners;
  if so, F-F's phase 3 unblocks on the current display and the "conditional" label falls away — a cheap
  way to de-risk the whole item.

## Notes

**Dependency / unblock map (from the roadmap docs):** F-B depends on nothing and unblocks F-C (Matrix
narrative Text) and F-D (Lyric-driven Faces) — "Build it once, unblock both features." F-F depends on
F-E (`xlo init-layout` — submodel discovery rides its classifier and writer) *and* a layout that
actually has submodels; it unblocks tree-zone/ring drum-kit mapping, vertical build runs, outline
section-by-section builds, window rhythm cells, and vendor HD-prop effect compatibility.

**Key source-doc references (kept for traceability):** Roadmap `docs/roadmap-2026-07.md` Horizon 2 (F-B,
F-C, F-D) and Horizon 3 (F-F, lines 260–261, prop-grouping assessment); June scorecard row "F1/F2
blocked on an asset-bound placement path"; `docs/roadmap-2026-06.md` §F1/F2 and F4;
`docs/craft-roadmap.md` items 7 (`lyric-driven-effects`), 8 (`matrix-narrative-text`), 9 (submodels) and
grounding line 11 ("0 SubModels → DEFERRED"). Spec `xlights-layout-semantics-spec.md` §1 (preserve
`<subModel>`), §5.6 (`SEM_OUTLINE_SEGMENTS`), §5.2 (ordered-group doctrine), §5.7 (group render modes),
§6 (manifest shapes), §7 (validation). Guides: `xlights-effects-catalog.md` §8 (Media & Content
Effects); `xlights-sequencing-guide.md` lines 179, 198, 223, 263, 289;
`xlights-layering-rendering-guide.md` lines 98 (Sub-Buffer), 144, 272. Related OpenSpec archives:
`2026-06-08-add-effect-presets` (the catalog), `2026-06-12-add-settings-hygiene` (`DROP_KEYS`),
`2026-06-10-add-render-style` (buffer-style injection), `2026-06-14-unblock-color-wash`
(`KNOWN_REJECTED_TYPES`), `2026-06-10-add-layout-semantics` (submodel segments as an explicit non-goal —
the deferral this change ends). Companion design docs: F-C Matrix narrative Text, F-D Lyric-driven Faces,
F-E `xlo init-layout` (classifier seams, group writer, manifest schema, validation machinery F-F
extends).
