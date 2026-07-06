## Context

The orchestrator's choreography stack targets `SEM_` semantic groups. The *Prop-grouping
assessment (2026-07)* confirmed the architecture is the right contract — choreographing against roles
and ensembles instead of raw models matches community practice and the hard xLights constraint that
groups load only at startup (a static, pre-built vocabulary is the only practical design; dynamic
per-section groups are impossible, and targeting individual models would lose group-canvas spatial
rendering and explode effect counts). Specifics that beat the alternatives: subtractive ensembles
(`SEM_ALL_LESS_FOCAL*`) kill bed-ghosting with zero blending arithmetic; empirical targetability
probing (`pipeline/groups.py`) beats parsing because targetability isn't derivable from the XML; one
source of truth for names (`pipeline/semantic_groups.py`) makes a typo an import error; flat groups
sidestep xLights' unpredictable group-of-group rendering.

**What exists — the realization half.**
`packages/xlights-core/src/xlights_core/knowledge/layout_semantics.py` implements everything
*downstream* of classification:
- `Prop` dataclass (lines 24–40) — already carries every spec §4/§6 field except `mirror_of` and
  submodels: `name, display_as, role="CUSTOM_PROP", res="POINT", nodes, x, y, band="MID",
  side="CENTER", center_dist, sweep_order, focal, confidence, wx, wy, groups`.
- `build_sem_groups(props) -> dict[str, list[str]]` (line 50) — the complete §5 group *plan*: role
  groups via `_ROLE_GROUP`, `_LTR` ordered groups for ARCH/MINI_TREE/CANE, band/side groups,
  ensembles including the subtractive `SEM_ALL_LESS_FOCAL`/`SEM_ALL_LESS_FOCAL_RHYTHM`. Pure,
  hermetic, tested (`tests/test_scene_cookbook.py:38-42`).
- `patch_sem_gridsize(rgb_path, size=SEM_GRID_SIZE)` (line 89, `SEM_GRID_SIZE=1200`) — the in-place
  XML patcher pattern this design extends: `ET.parse`, mutate only `modelGroup[@name^="SEM_"]`, write
  to `.tmp`, `os.replace`. Idempotent (`tests/test_led_readability.py:142-152`).
- `patch_view(rgb_path, view_name="SEM Master")` (line 142) and `patch_xsq_render_order(xsq_path)`
  (line 176) — the same atomic offline-patch pattern applied to views and sequence row order, driven
  by `canonical_order()` (line 135) and the `_order_tier` table (line 127).

Around it, the orchestrator package has the operational pieces:
- **Empirical targetability probe** — `pipeline/groups.py::targetable_groups()` (line 35) places a
  throwaway `On` effect per group on a disposable sequence, keeps the ones xLights accepts, and caches
  by a layout fingerprint of sorted group *and model* names (`_fingerprint`, line 28). This is the
  run-time source of `st.available_groups` (`pipeline/run.py:386`).
- **The name vocabulary** — `pipeline/semantic_groups.py` holds the constants the deterministic
  layers import: `METRIC_RING` (line 41), `BACKBEAT_GROUP_PREFERENCE` (line 46), `BED_PREFERENCE`
  (line 33), `RHYTHM_POOL`, `ACCENT_GROUPS`, `HERO_GROUP`, `MELODIC_STEMS`. Consumed by
  `pipeline/beats.py::select_rhythm_groups()`, which degrades gracefully via `if g in avail` filters —
  but the *order* is this layout's opinion baked in.
- **Director input** — `agents/director.py::render_input()` (line 23) passes the group list as a bare
  JSON array (`AVAILABLE GROUPS (choose targets only from these):` + `json.dumps(groups)`, line 29).
  No node counts, no geometry, no symmetry, no capability classes.
- **QA capability gating by name prefix** — `qa/rules.py` (line 46/53): `_LINEAR_PREFIXES =
  ("SEM_ARCHES", "SEM_OUTLINE", "SEM_CANES", "SEM_ICICLES", "SEM_PATH")`; `_is_linear(target)` returns
  `target.startswith(_LINEAR_PREFIXES)`. Works only because the `SEM_` naming convention encodes role;
  a Custom prop that is geometrically LINEAR but grouped elsewhere escapes rule #2, and a user's
  freely-named group is invisible to the gate.
- **Offline preview renderer** — `xlights_core/preview/`: `parse_models()` (`layout.py:113`) parses
  `DisplayAs`, `parm1-3`, `WorldPosX/Y/Z`, `Scale`/`Rotate`, `CustomModel` grids;
  `model_world_pixels()` (`layout.py:248`) gives per-pixel world coordinates; `PreviewRenderer`
  (`render.py:29`) renders `.fseq` frames to PNG/MP4. This is the machinery §7 validation needs.
- **Visual critic** — `agents/visual_critic.py` (multimodal, advisory findings) can optionally inspect
  validation renders.
- **CLI** — `cli.py::main()` (line 67) has an argparse subcommand pattern (`run`, `regen`,
  `edit-brief`) that `init-layout` slots into; entry point `xlo = "xlights_orchestrator.cli:main"`.

**What doesn't exist — the judgment half.**
There is **no classifier, no spatial deriver, no group writer, no manifest** in the package. A grep
for `layout_semantics.json` across `packages/` returns nothing; the only callers of `build_sem_groups`
are tests. Historical note: the archived change
`openspec/changes/archive/2026-06-10-add-layout-semantics/` designed a classifier + spatial derivation
+ rgbeffects writer + manifest, but only the group-plan and patch functions survived into
`layout_semantics.py`. The classification and group creation for the current layout were executed as a
one-time agent/manual step. The July assessment ("the classifier is prose, not code … group creation
is agent/manual today") is the authoritative statement of what is actually in the tree, and this
change designs against that reality. The archived change's *decisions* (DisplayAs map, tree threshold,
outlier handling, backup/atomic write, xLights-closed guard) remain valid prior art and are folded in.

**Architecture at a glance.**
```
xlo init-layout
  ├─ 1 ANALYZE   knowledge/layout_classify.py   (new, xlights-core)
  │              parse_props → classify → derive_spatial; LLM fallback: agents/layout_classifier.py
  ├─ 2 REVIEW    pipeline/init_layout.py         (new, orchestrator)
  │              terminal review queue for confidence < 0.8 (web UX deferred)
  ├─ 3 WRITE     knowledge/layout_semantics.py   (extended)
  │              write_sem_groups(): idempotent modelGroup create incl. §5.7 layout modes +
  │              GridSize + patch_view; timestamped backup; xLights-must-be-closed guard
  ├─ 4 MANIFEST  knowledge/layout_manifest.py    (new, xlights-core)
  │              LayoutManifest pydantic model; emit layout_semantics.json
  ├─ 5 VALIDATE  pipeline/layout_validate.py     (new, orchestrator)
  │              synthetic .fseq → PreviewRenderer role-color frames + sweep-centroid check
  └─ CONSUME     director.py (traits block) · qa/rules.py (gating) · semantic_groups.py (vocabulary)
```
Package split follows the existing convention: everything that reads/writes xLights artifacts and is
LLM-free lives in `xlights-core/knowledge`; the CLI flow, the LLM fallback agent, and manifest
*consumption* live in `xlights-orchestrator`.

## Goals / Non-Goals

**Goals:**
- Onboard an **arbitrary** xLights layout to the `SEM_` vocabulary with one guided command, closing
  all five assessment gaps (classifier, manifest, layout modes, derived vocabulary, validation).
- Run **fully deterministically with no LLM key** (steps 1–4); the LLM fallback is optional and only
  for the unresolved tail.
- **Converge** on the current hand-built layout: `--dry-run` produces an empty (or explained-only)
  membership diff, and a re-run is a byte-level no-op.
- Keep every consumer **backward-compatible**: absent a manifest, the Director prompt is byte-identical
  to today, QA falls back to the prefix table, and `DEFAULT_VOCAB` equals today's constants.
- Deterministic-first validation (pure geometry gates; vision advisory).

**Non-Goals:**
- Not fixing membership-overlap render-order load-bearing-ness (accepted tension; out of scope —
  `canonical_order`/`patch_view` stay the single ordering authority, and the manifest at least makes
  the overlap inspectable).
- Not generalizing the 2026-06-10 one-time deletion of the user's 47 `0[1-8]_` numbered groups;
  `init-layout` must never touch user groups (spec §5.6). A separate `--prune-groups` is an open
  question, not this change.
- Not multi-preview/multi-`layoutGroup` support at v1 (spec §8: default preview only).
- Not submodel *targeting* (that's F-F); the classifier only *discovers* submodel names for the seam.
- Not improving offline-render effect-appearance fidelity (that's I8/`RealRender`); validation judges
  only "which pixels lit, where," which the offline renderer is exact at by construction.

## Decisions

**1. A dedicated dependency-free `parse_props`, not reuse of `preview/parse_models`.**
`parse_models()` requires `networks.xml` controllers to resolve start channels (irrelevant to
classification) and drops models it can't channel-resolve. Propose a dedicated parser that also
captures what classification needs and `parse_models` ignores — `StringType`, `<subModel>` children
(preserved for F-F), and user group membership (reverse-indexed from `<modelGroups>`). Node counting
reuses the proven rules in `preview/layout.py:141-149`: Custom → `max(CustomModel grid)`; Cube →
`parm1*parm2*parm3`; everything else → `parm1*parm2`. `Prop` gains three defaulted, backward-compatible
fields: `mirror_of: str | None = None`, `string_type: str = ""`, `submodels: list[str] = []`.
*Alternative rejected:* extend `parse_models` to skip channel resolution — would entangle the two
consumers and their controller-dependency assumptions.

**2. The classifier is data-driven steps in a fixed order, each touching only unresolved props (spec §3).**
- Step 1 — DisplayAs direct map (a `DISPLAYAS_ROLE` dict): Arches→ARCH, Icicles→ICICLES, Candy
  Canes→CANE, Star→STAR, Spinner→SPINNER, Matrix/Horiz Matrix/Vert Matrix→MATRIX, Window Frame→WINDOW.
- Step 2 — tree pixel-count disambiguation: Tree 360 / Tree Flat / Tree 180 with ≥ `MEGA_TREE_NODES`
  (600) nodes → MEGA_TREE, else MINI_TREE; a *sole* tree that is also the layout's largest prop →
  MEGA_TREE regardless.
- Step 3 — name heuristics (case-insensitive substring, spec table verbatim): roof/gutter/eave/ridge/
  outline/peak/fascia/column/garage→OUTLINE; window/door→WINDOW; flood/wash/up light/uplight→FLOOD;
  face/sing/carol/mouth→SINGING_FACE; sign/tune→SIGN; drive/walk/path/fence/yard line→PATH; flake→
  SNOWFLAKE.
- Step 4 — group hints: an unresolved prop inherits the role its user group's name matches under the
  same heuristics (member of "All Outline" → OUTLINE).
- Confidence: step 1–2 → 1.0, step 3 → 0.9, step 4 → 0.85, unresolved → CUSTOM_PROP @ 0.5.
*Alternative rejected:* a single opaque LLM classification of the whole layout — the archived change's
decision to keep classification deterministic-first is preserved (the current layout's 33 Custom
models resolved via name/group heuristics + manual review, no LLM needed).

**3. Capability classes are derived from role + geometry (spec §2), replacing "names encode capability."**
`capability(role, nodes, string_type)`: MATRIX→2D_SURFACE; MEGA_TREE/SPINNER/STAR→2D_RADIAL;
OUTLINE/PATH→LINEAR_HIGH if nodes ≥ 100 else LINEAR_LOW; ARCH/CANE/ICICLES/SNOWFLAKE/WINDOW/MINI_TREE→
LINEAR_LOW; FLOOD/CUSTOM_PROP low-count→POINT; SINGING_FACE→SPECIAL; non-RGB StringType→POINT override
regardless of role (spec §8); very large dense Custom (node density + area)→MATRIX/2D_SURFACE (spec §8).
This unlocks QA rules the prefix hack can't express (texture on a matrix-dominated mixed group;
POINT-only groups rejecting anything but washes; SPECIAL faces excluded from general placement).

**4. Step-5 LLM fallback is optional, batched, and enum-constrained (orchestrator side).**
`agents/layout_classifier.py` with `PropRoleGuess`/`PropRoleGuesses` pydantic models; the `role` field
is a `Literal[...]` over the 16 canonical roles, so an invented role is a schema failure, not a silent
bad group. One *batched* call for the whole unresolved tail (compact records, one worker-tier request),
not one call per prop. A new `classifier` role goes into `models/config.yaml` routed to the worker tier
(same as `analyst`/`generator`). Per spec §3.5/§6, any guess with `confidence < 0.8` — and every prop
the LLM didn't return — goes to the **review queue**, never silently into a group. Fully optional:
`--no-llm` or no key → deterministic steps 1–4 with the tail defaulting to CUSTOM_PROP + review.
Keeps xlights-core LLM-free.

**5. Spatial derivation order matters; outliers are excluded before normalization (spec §4/§8).**
`derive_spatial(props, *, invert_x=False) -> SpatialSummary(width_units, focal_x, symmetric, excluded)`:
(1) outlier exclusion FIRST — models > 2× the display span outside the main bbox, or with zero nodes,
are excluded from the bbox and appended to review (the X = −907 parked model must not stretch
normalization); (2) normalize `x=(wx-min_x)/(max_x-min_x)`, `y` likewise, ground→top, `invert_x` flips
x; (3) bands GROUND/MID/ROOF at y cuts 0.33/0.66 (optionally adjusted up if OUTLINE models define a
roofline above 0.66); (4) sides LEFT x<0.45, CENTER 0.45–0.55, RIGHT >0.55; (5) sweep order within each
multi-instance role in {ARCH, MINI_TREE, CANE, WINDOW, SNOWFLAKE, SPINNER} by x, `sweep_order=1..N`
(exactly what `build_sem_groups` expects for `_LTR`); (6) mirror pairs: same role, |x₁+x₂−1| ≤ 0.05 and
|y₁−y₂| ≤ 0.05 → set `mirror_of` on BOTH props; (7) center distance from the focal center (MEGA_TREE if
present, else bbox center) into `center_dist`; (8) focal flags: MEGA_TREE, MATRIX, and any prop whose
scale-derived visual area exceeds ~15% of the display area.

**6. The `SEM_` group writer creates elements — the piece with no precedent — extending the patch pattern.**
`write_sem_groups(rgb_path, groups, *, modes=None, grid_size=SEM_GRID_SIZE, backup=True) -> WriteReport`
(1) timestamped backup `rgbeffects.<ts>.bak` unless `backup=False`; (2) remove every existing
`modelGroup` whose name matches `^SEM_` (regenerable, spec §6: "rerunning deletes and recreates all
SEM_ groups, touching nothing else"); (3) append one `<modelGroup>` per plan entry (name, models=
comma-joined members, LayoutGroup="Default", GridSize, + the §5.7 layout-mode attribute); (4) atomic
tmp + `os.replace`. NEVER touches non-SEM_ groups (spec §5.6). `WriteReport(created, replaced,
kept_user_groups, backup)`.

**7. The §5.7 layout-mode serialization is pinned by a round-trip spike, NOT guessed.**
`LAYOUT_MODE_ORDERED = "Horizontal Per Model"` (SEM_*_LTR — chases traverse member order),
`LAYOUT_MODE_ENSEMBLE = "Per Preview"` (SEM_ALL / SEM_BAND_* / ensembles — spatial map);
`layout_modes(groups)`: `_LTR` → ordered mode, everything else → ensemble mode. xLights stores the
group dialog's "Preview/Buffer Layout" choice as a `modelGroup` XML attribute, but the exact attribute
NAME and the serialized strings must be established by round-tripping (create one group in each mode in
the target build's UI, save, diff the XML — slice 3.1). This is a *different* setting from the
per-effect `B_CHOICE_BufferStyle` in `pipeline/render_style.py`; the group-level default is what an
effect gets when its buffer style is "Default" (the archived `add-metric-rhythm` design found the
`_LTR` groups "don't render a chase" precisely because their group mode was never set).
*The doc pins the behavioral requirement; the constant strings come from the confirmed round-trip.*

**8. An xLights-must-be-closed guard, inverting the pipeline's usual assumption.**
xLights rewrites `rgbeffects.xml` from memory on exit, silently clobbering offline edits. The guard is
a cheap connectivity probe: attempt `XLightsClient.get_version()` with a short timeout; if it answers,
refuse to write ("close xLights, then re-run"; in the guided flow, wait-and-poll with a countdown).
`init-layout` must NOT share `_run()`'s `async with XLightsClient()` (which assumes xLights running).

**9. The manifest is written to the show dir (canonical) plus a cache copy, and is version-tolerant.**
`knowledge/layout_manifest.py`: `PropRecord(id, role, res, nodes, pos, sweep_order, mirror_of, focal,
confidence, submodels)`, `GroupRecord(members, ordered, layout_mode)`, `LayoutManifest(version=1,
generated, display, props, groups, review)`. `emit_manifest(m, show_dir) -> Path` writes
`layout_semantics.json` (< 10 KB) to the show dir (spec §6: "the only layout representation downstream
LLM planners receive") plus a copy under the cache root so hermetic runs and the dashboard can read it
without the show folder mounted. `load_manifest(show_dir_or_path) -> LayoutManifest | None` is tolerant:
`None` if absent or version-mismatched (forward-compat guard).

**10. Manifest consumption is three independent, individually-landable integrations.**
(a) **Director traits/props block** — `render_layout_block(manifest, groups)` renders ~1 KB per
targetable `SEM_` group (role, member count, ~nodes, band, symmetry/order) plus one display line
("display ~18m wide, focal center x=0.50, symmetric"). `render_input(brief, groups, placeable_types,
manifest=None)` keeps the flat AVAILABLE GROUPS list unchanged (the authoritative constraint from the
live probe at `pipeline/run.py:414`) and appends the block only when a manifest exists — absent
manifest, byte-identical prompt, so cached briefs stay valid.
(b) **QA capability gating** — `_target_res(target, manifest)` returns the res classes of the target
(the prop's own class, or the union of member classes for a group); `_is_linear(target, manifest=None)`
returns `res <= {"LINEAR_HIGH","LINEAR_LOW"}` when a manifest is present, else the legacy prefix
fallback. `evaluate(instructions, plan)` grows an optional `manifest=None` keyword; existing tests pass
unchanged.
(c) **Choreography data** — mirror pairs and sweep orders feed true call-and-response (left prop ↔ its
recorded mirror) and center-out waves ordered by `center_dist`; the seam is that
`weave`/`pipeline/triggers.py` group rotation already take name lists, so the manifest only needs to
*order* those lists.
*Alternative weighed and deferred:* a browser review form (the `brief_editor.py` stdlib-`http.server`
`serve()` pattern) — deferred because the review payload is a short list of enum choices with no visual
assets yet (the validation render doesn't exist at review time); a numbered terminal prompt is strictly
simpler. Browser review wins only once each prop can be shown highlighted in a preview render (v2,
`--review-web` reserved).

**11. Derived choreography vocabulary — a pure function over the manifest, constants as fallback.**
`ChoreoVocabulary(metric_ring, backbeat_preference, bed_preference, peak_broad, accent_groups,
hero_group, bass_band_group)` (frozen); `DEFAULT_VOCAB` = today's constants; `derive_vocabulary(manifest)`:
`None` → `DEFAULT_VOCAB`. RING: rank the rhythm-family role groups present (ARCH, CANE, MINI_TREE,
SNOWFLAKE, SPINNER, WINDOW) by score = f(instance count, x-spread, node budget) — count (a walkable
family needs ≥2 members), spread (the walk should traverse the yard), node budget (readable at
distance); take the top 4. BACKBEAT: `SEM_SIDE_*` when ≥2 sides populated (spatial contrast beats family
contrast), else the point/accent families not consumed by the ring. BED: `SEM_BAND_GROUND` if the ground
band holds ≥~25% of props, else `SEM_ALL`; PEAK_BROAD is the reverse (broadest first, preserving today's
deliberate asymmetry). HERO: `SEM_FOCAL` if any focal prop, else the largest 2D_RADIAL/2D_SURFACE prop.
Consumers change minimally: `select_rhythm_groups(section, available_groups)` gains
`vocab: ChoreoVocabulary = DEFAULT_VOCAB`; `weave.py`'s `BED_PREFERENCE` lookup does the same;
`run.py` computes the vocabulary once per run from the loaded manifest. Every `if g in avail` guard
stays — the vocabulary proposes, the live probe disposes.
*Alternative rejected:* keeping the constants and relying only on the `if g in avail` filters — the
roadmap explicitly asked for a beat anchor chosen *by ranking*, not by accident of tuple order.

**12. Validation needs no xLights; the validator synthesizes the test frames' channel data directly.**
`pipeline/layout_validate.py`: `write_fseq_v2_uncompressed(path, frames, frame_ms=50)` (minimal
uncompressed FSEQ v2 writer the read side `preview/fseq.py::load_fseq` round-trips);
`role_color_frames(manifest, models)` (one frame per role present, that role's member channels at a
hue-distant color, rest dark — spec §7.1); `sweep_frames(group, models)` (K frames for an `_LTR` group,
member i lit alone in frame i — spec §7.3); `check_sweep(frames, renderer)` (DETERMINISTIC: per frame,
the lit-pixel world-x centroid — `renderer.world[ch]` weighted by channel value — must be strictly
increasing; backward → x axis inverted → CLI offers `--invert-x`); `role_color_sheet(renderer, frames,
labels)` (contact sheet PNG written next to the manifest — spec §7.2). Labor split: **deterministic
(always)** — the sweep-centroid check (pure geometry, in the pass/fail gate) plus cheap structural
checks (every SEM_ member exists; no SEM_ group empty; `SEM_ALL` excludes SINGING_FACE/SIGN; every
`_LTR` member order matches `sweep_order`); **vision (optional, LLM key)** — the role-color contact
sheet to the visual critic with spec §7.2's question ("does each colored region correspond to its
labeled role?") plus known failures (mega vs mini tree confusion, outline-as-PATH) — advisory, printed,
never auto-mutating; **human (always)** — the contact sheet on disk. Caveat: offline-render fidelity is
approximate for effect *appearance* (why `RealRender` exists), but for role-color/sweep — "which pixels
lit, where" — the offline renderer is exact by construction. One live render remains the ground-truth
gate at the end of the first real run, unchanged.

**13. The guided CLI flow, wired into the existing subcommand pattern.**
`xlo init-layout [--show-folder PATH] [--dry-run] [--yes] [--no-validate] [--no-llm] [--invert-x]
[--review-web]`: (1) Locate — `--show-folder`, else ask a running xLights via `get_show_folder()`
(remembered for the close guard), else prompt; (2) Analyze — `parse_props` → `classify` → LLM fallback
(skipped with `--no-llm`/no key) → `derive_spatial`; print the classification table; (3) Review — for
each prop with confidence < 0.8 and each excluded outlier, a numbered terminal prompt offering the role
enum, "accept as CUSTOM_PROP", or "exclude"; `--yes` accepts all suggestions unattended (they still land
in the manifest's `review` array so state is visible; spec §7.4 requires resolution before the manifest
is "final" — an unreviewed manifest is marked `review` non-empty and the CLI exits with a warning);
(4) Plan + diff — `build_sem_groups(props)` → diff against the file's current SEM_ groups; `--dry-run`
stops here; (5) Write — enforce the closed guard → `write_sem_groups` + `patch_view` → `emit_manifest`;
print the backup path; (6) Validate — §7 (skippable via `--no-validate`); on a sweep-test failure offer
to re-run with `--invert-x` automatically; (7) Finish — "Restart xLights to load the groups; the first
`xlo run` will re-probe targetability." CLI wiring: a new `sub.add_parser("init-layout", ...)` beside
`run`/`regen`/`edit-brief` dispatching to `pipeline/init_layout.py::run_init_layout(args)`. Unlike `run`,
it must not require an LLM key and must not require xLights running.

## Risks / Trade-offs

- **Misclassification poisons every downstream decision (gap #5's warning).** Wrong groups → wrong
  choreography for the layout's whole lifetime. → Confidence thresholds + mandatory review queue (spec
  §7.4); deterministic sweep/structural validation gates the command; role-color contact sheet for
  human/vision inspection; convergence test against the known-good real layout; overrides file for the
  irreducible judgment calls.
- **xLights open during write → file silently clobbered on xLights exit.** Groups vanish; user
  confusion. → Connectivity-probe guard refuses to write while the automation port answers; guided
  flow polls until closed; timestamped backup before every real write; post-restart verification
  instructions printed.
- **xLights file-format drift (attribute names/values change across versions).** Writer emits attributes
  a new xLights ignores or rejects. → Layout-mode strings pinned by a per-version round-trip fixture
  (slice 3.1), not guessed; writer touches only SEM_ elements and never rewrites unknown attributes
  elsewhere; version string logged into the manifest (`generated` block) for forensics.
- **Wrong §5.7 layout mode silently breaks every sweep on a group (gap #3).** Chases don't traverse;
  hard to attribute. → The sweep-centroid validation test exists precisely for this — it fails
  deterministically at init time instead of visually at show time.
- **ElementTree drops XML comments / reorders attributes.** Cosmetic diff noise in a user-owned file. →
  Already the accepted, shipped behavior of `patch_view`/`patch_sem_gridsize` on the same file; xLights
  itself rewrites the file; backups retained.
- **LLM fallback hallucinates roles or burns cost.** Bad tail classifications. → Enum-constrained
  `output_type` (invalid role = schema error); worker-tier routing; one batched call; <0.8 → review,
  never silent; fully optional (`--no-llm`).
- **Group rewrite invalidates the targetable-groups cache mid-season.** One slow re-probe run. → By
  design — `_fingerprint` keys on group+model names; CLI summary warns the next run re-probes.
- **Derived vocabulary changes shows on the *current* layout.** Regression on the one layout that
  matters today. → `DEFAULT_VOCAB` equals today's constants; golden pipeline snapshot asserts
  byte-stability; derivation must reproduce the constants from the real-layout manifest before it ships
  as default.
- **Membership overlap remains render-order load-bearing (accepted tension).** A future reordering
  silently changes occlusion. → Out of scope to fix; `canonical_order`/`patch_view` stay the single
  ordering authority, and the manifest records group membership so the overlap is at least inspectable.

## Migration Plan

The first user of `init-layout` is the current layout, which already has hand-created SEM_ groups the
whole pipeline depends on. **Requirement:** `xlo init-layout --dry-run` against it produces a plan whose
group membership matches the file **byte-for-byte or with explained diffs only** — misclassification
shows up as a membership diff, so the dry-run diff doubles as the classifier's acceptance test on real
data. Mechanics:
- `--dry-run` renders a three-way diff per group: *only-in-file / only-in-plan / member-order-changed*.
- **Convergence fixture:** a sanitized copy of the real `rgbeffects.xml` (names kept, personal metadata
  stripped) under `tests/fixtures/` with a golden manifest — same golden-snapshot discipline as
  `test_golden_pipeline.py`.
- Divergences during bring-up are resolved by *fixing the classifier or recording an explicit per-layout
  override*, never by weakening the diff. Overrides live in a small `layout_overrides.json` beside the
  manifest (`{"prop_name": {"role": ...}}`), applied after step 4, before the LLM step.
- A converged re-run is a **no-op write**: `write_sem_groups` compares the serialized SEM_ subtree before
  replacing and skips the file write (and the backup) when identical — same idempotency contract as
  `patch_sem_gridsize` returning 0.
- One accepted divergence to resolve at bring-up: the file may contain hand-set attributes on SEM_ groups
  the plan doesn't know about. Policy: the writer owns SEM_ groups *entirely* (spec §6 regenerability);
  anything worth keeping must become part of the plan (grid size, layout mode) — discovered extras are
  printed in the diff so nothing silently vanishes.

Docs migration: `docs/usage.md`'s "One-time layout setup (SEM_ groups)" section (lines 53–69) is
rewritten to describe `xlo init-layout` instead of the manual/agent procedure.

## Open Questions

1. **Layout-mode serialization** — the exact `modelGroup` attribute name/values for "Per Preview" vs
   "Horizontal Per Model" in the target xLights build. Resolved by the slice-3.1 round-trip spike before
   any writer code merges (deliberately not guessed here).
2. **Manifest home** — spec §6 says the show directory; the pipeline caches under `data/analyses/`.
   Proposal: show dir canonical, cache copy for hermetic consumers — confirm the copy doesn't create a
   staleness trap (mtime check on load?).
3. **`SEM_ALL_LESS_FOCAL*` vs the spec** — the subtractive ensembles exist in code but not in spec §5.5.
   Proposal: treat code as the spec's superset and amend the spec doc; the writer emits them (it already
   must, for convergence).
4. **Numbered-group removal** — the 2026-06-10 change deleted the user's 47 `0[1-8]_` groups as a
   one-time, explicitly-consented cleanup. `init-layout` must NOT generalize that (spec §5.6 forbids
   touching user groups). Is a separate `--prune-groups REGEX` opt-in worth having, or leave cleanup
   manual?
5. **Multiple previews / layoutGroups** — spec §8 says default preview only. Is a `--layout-group NAME`
   escape hatch needed at v1, or defer until a real second-preview user appears?
6. **Roofline-adjusted band cuts** — implement the §4.2 adjustment at v1 or ship fixed 0.33/0.66 cuts and
   revisit when a layout misbands? (Leaning: fixed cuts + a manifest field recording them, so the
   adjustment is a data change later.)
7. **Where does the Director block stop?** ~1 KB of traits is the roadmap's number; should
   `group_motifs`-style per-prop detail (colors that read well on sparse props) ever ride along, or is
   that the guides' job? (Leaning: traits only; guides own craft.)
8. **Review UX v2** — browser review with per-prop preview-render highlights once the validator exists
   (`--review-web`), reusing the `brief_editor.py` pattern. Worth scheduling with F-I (live progress UI)
   which extends the same pattern?

## Notes

- **Dependencies / sequencing:** F-E depends on nothing hard; roadmap sequencing puts it after
  F-A/F-B/F-C ("do it once the show quality is worth sharing"). I5 (degradation logging) pays off during
  its live-verify. F-E unblocks F-F (submodel targeting), sharing the tool with any layout,
  manifest-grounded Director designs, and capability-class QA. Complexity L — split into the seven
  landable slices captured in tasks.md.
- **Prior art (archived changes whose decisions are inherited):**
  `2026-06-10-add-layout-semantics` (DisplayAs map, tree threshold, outlier policy, backup + atomic
  write, xLights-closed constraint; the history of what survived into the package);
  `2026-06-11-add-render-order`; `2026-06-11-add-scene-cookbook` (subtractive ensembles);
  `2026-06-17-add-metric-rhythm-and-instrument-overlay` (the `_LTR` render-mode gap);
  `2026-06-09-add-targetable-group-filter`.
- **References:** roadmap `docs/roadmap-2026-07.md` (Horizon 3, "Prop-grouping assessment (2026-07)"
  and item F-E; sequencing table row 7); the spec `xlights-layout-semantics-spec.md` (§2
  roles/capabilities, §3 classification, §4 spatial, §5 groups incl. §5.6 what-not-to-do and §5.7 layout
  modes, §6 manifest, §7 validation, §8 edge cases); downstream `f-f-submodel-targeting.html` (consumes
  the classifier's submodel discovery and the writer). Grounding docs: `docs/usage.md` "One-time layout
  setup (SEM_ groups)", `docs/craft-roadmap.md`.
