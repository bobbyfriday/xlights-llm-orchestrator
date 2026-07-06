## Why

The two remaining `craft-roadmap.md` narrative features — Matrix narrative Text (item 8) and
lyric-driven Faces (item 7) — have been blocked since June on the same wall: **every** effect the
pipeline can place must come out of the mined preset catalog, and Text/Faces (and Pictures/Video/
Shader) are not in it and structurally cannot be. The June scorecard row is blunt: "F1 Matrix Text /
F2 Faces — ❌ Open — still blocked on an asset-bound placement path." Separately, everything the
orchestrator places today lands on whole models or whole-model groups, so choreography resolution is
capped at the prop: the mega tree is one target, the roofline is one line, a window frame is
indivisible — the community craft of tree-zone drum kits, vertical build runs, and section-by-section
outline "draws" is foreclosed.

Neither block is an oversight; each is a consequence of a correct decision. The catalog is mined from
community `.xsq` so every settings string is **valid by construction** — that guarantee cannot extend
to effects whose settings reference things *outside the string* (image/video paths, face definitions,
timing-track names on someone else's disk). And there is deliberately no submodel handling anywhere in
the packages, plus one guard (`place_preset`'s layout check) that actively rejects submodel targets.

These two roadmap items are the shared **placement primitives** that the later narrative features
(matrix text, faces) and layout-generalization features (tree zones, outline draws) build on:

- **F-B (Horizon 2 enabler, M)** — an asset-bound placement path: a second placement route that
  constructs asset-bound settings strings *from scratch in code*, binds their external references to
  resources *we ourselves create*, validates via the existing settings parser, and carries them
  through the existing emitter seam. Build it once, unblock both F-C and F-D.
- **F-F (Horizon 3, L, conditional)** — submodel targeting: addressing submodels / parts of a prop
  (tree rings/zones, roofline segments, window cells). Conditional because this user's `rgbeffects.xml`
  has **0 SubModels** → the work is DEFERRED until F-E onboards a layout that has submodels (vendor HD
  props ship with them). Captured now so the F-E classifier leaves the right seams; a minimal-first
  plan where everything buildable without submodel hardware is cheap and everything else is parked
  behind an explicit verification gate.

## What Changes

**F-B asset-bound placement:**
- Add a code-owned settings-template module `knowledge/direct_settings.py` with
  `DIRECT_TYPES = {"Text", "Faces"}`, `build_text_settings(...)`, and a `build_faces_settings(...)`
  skeleton (raises until F-D lands its probe) — each returning a settings string built from scratch,
  round-trip-validated via `settings.parse_settings`, binding external references only to resources
  the caller proves exist.
- Freeze the Text template from a hand-authored probe `.xsq` committed as a fixture; the builder
  varies only the documented knobs (the "corpus of one" invariant).
- Add a defaulted `EffectInstruction.direct_settings: str = ""` (`show_plan.py`); when non-empty the
  emitter bypasses the preset library entirely. Cached instruction lists and the golden fixture load
  and compare unchanged.
- Add `editing.place_direct(...)` — a sibling of `place_preset` that skips assembly but keeps every
  guard (parse-round-trip validation, `extra_settings` first-occurrence-wins merge,
  `palette_from_colors`, timing/target checks, `PresetPlacementError` on `worked=false`). Extract the
  shared merge/guards from `place_preset` into private helpers (`_merge_extra_settings`,
  `_check_timing_and_target`) — no behavior change to the preset path.
- Branch `effect_emitter.apply_instructions` on `direct_settings` with identical layer accounting and
  skip-on-failure (`_SKIPPABLE`) behavior for both branches.
- Add a `validate_direct(client, effect_type, settings)` live check mirroring `validate_preset`'s
  scratch-sequence protocol (`-m live`), run once per template per xLights upgrade.
- Keep Text/Faces **out** of the LLM's free-choice menu: `DIRECT_TYPES ∩ placeable_effect_types() ==
  ∅` asserted by test; only deterministic passes populate `direct_settings`.
- Pictures/Video/Shader (and DMX) stay **explicitly OUT** — `DIRECT_TYPES` is the allowlist; adding to
  it requires a new OpenSpec change.

**F-F submodel targeting:**
- Extend the F-E classifier's `parse_props()` to parse each `<model>`'s `<subModel>` children into a
  new `SubModel` dataclass (name, parent, node_ranges, expanded node count, derived `kind` — RING /
  ZONE / HALF / SEGMENT / ARM / TOPPER — and `order_hint`), attached to the parent `Prop`; preserve
  unknown submodel types verbatim. Pin the XML grammar with an authored fixture
  (`tests/fixtures/layout_submodels.xml`), not from memory.
- Derive segment ordering: SEGMENT/HALF by mean world-x (left-to-right), RING/ZONE by mean world-y or
  `order_hint` (bottom-to-top). Roles are **inherited** from the parent (an OUTLINE submodel is an
  outline segment); submodels never get independent taxonomy roles.
- Add `build_submodel_groups(props)` emitting `SEM_OUTLINE_SEGMENTS` (LTR), `SEM_TREE_ZONES`
  (bottom-up), per-zone singletons `SEM_TREE_ZONE_<i>` (the drum-kit targets), `SEM_TREE_TOPPER`, and
  `SEM_WINDOW_CELLS` — members are `Parent/SubModel` references. Layouts with 0 submodels produce
  **zero** new groups (byte-identical to today, asserted forever).
- **Targeting Route B (recommended, decided):** submodel-membered model groups become ordinary
  top-level elements — zero client changes; the existing `pipeline/groups.py::_probe` answers
  targetability per layout. Route A (direct submodel-element target) stays a recorded live experiment,
  not on the critical path.
- Choreography hooks (`if zones`-guarded, submodel-less layouts untouched): drum-kit mapping in
  `pipeline/beats.py` (`RhythmRoles.zones/topper`, downbeat→bottom / backbeat→mid / sparkle→topper);
  vertical build runs via `pipeline/weave.py` sweeps on ordered zone groups (up/down direction);
  outline-draw intro recipe; a Director layout-block line per submodel-bearing prop.
- Offline validation: `PreviewRenderer` lights each zone/segment via its parent-channel subset and
  runs the F-E sweep-centroid check on the appropriate axis (vertical for zones, horizontal for
  segments).
- A minimal-first plan: phases 0–2 (fixture/parser, plan/manifest, writer/offline-validation) are
  buildable and hermetic today behind an `--submodels` flag on `xlo init-layout`; phase 3 (live
  hardware verification) is an explicit gate before anything defaults on; phase 4 (choreography) and 5
  (optional follow-ups) follow.

## Capabilities

### New Capabilities
- `asset-placement`: a second, code-owned placement route for asset-bound effect types (Text, Faces)
  whose settings reference resources outside the string — templates built from scratch, references
  bound only to resources the pipeline creates/verifies, syntactically validated, carried through the
  existing emitter without entering the LLM's free-choice menu.
- `submodel-targeting`: discovery, planning, ordered/singleton grouping, and choreography of prop
  submodels (tree zones/rings, outline segments, window cells), gated on a submodel-bearing layout and
  a live-verification pass; a no-op on layouts with zero submodels.

### Modified Capabilities
- `xlights-sequence-editing`: the preset-backed placement requirement gains a code-templated
  (non-catalog) direct-placement path and its scratch-sequence validation, alongside the existing
  preset path.
- `show-orchestration`: instruction placement branches on a direct-settings payload while keeping
  asset-bound types out of the placeable menu; the semantic-group and beat-accent requirements gain
  submodel-membered `SEM_` groups and zone-mapped drum-kit accents, no-op on submodel-less layouts.

## Impact

**F-B code paths:** new `packages/xlights-core/src/xlights_core/knowledge/direct_settings.py`; edits to
`xlights_core/editing.py` (`place_preset` refactor + `place_direct` + `validate_direct`),
`packages/xlights-orchestrator/src/xlights_orchestrator/effect_emitter.py` (`apply_instructions`
branch), `show_plan.py` (`EffectInstruction.direct_settings`); test-only assertion touching
`agents/catalog.py::placeable_effect_types`. Reuses `colors.palette_from_colors`,
`client.add_effect`, `knowledge/settings.py` parser, `knowledge/constants.py::classify_kind`,
`resolve_buffer_style`. Estimated blast radius: 2 new files, ~4 edited; no changes to `run.py`, QA
scoring, or any agent prompt. Risk: low — the emitter branch is a two-line dispatch; the golden,
`test_editing.py`, and emitter tests must stay green with zero fixture changes.

**F-F code paths:** `knowledge/layout_semantics.py` (`SubModel` dataclass, `build_submodel_groups`,
`canonical_order` tier placement), the F-E classifier `parse_props()`, `xlights_core/preview/layout.py`
+ `render.py` (channel-subset math), `pipeline/beats.py` (`RhythmRoles`, `place_beat_accents`,
`select_rhythm_groups`), `pipeline/weave.py` (zone-direction sweeps), `pipeline/groups.py` (the probe,
unchanged mechanism), the F-E manifest/writer, `xlo init-layout` (`--submodels` flag). New fixture
`tests/fixtures/layout_submodels.xml`. Risk: **conditional / deferred** — nothing benefits the current
0-submodel layout; phases 0–2 exercised purely by fixtures behind a flag; phase 3 is a hardware gate;
the 0-submodel no-op is a permanent regression test; the golden pipeline snapshot must be unchanged.
