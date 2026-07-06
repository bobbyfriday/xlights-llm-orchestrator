Seven landable slices, each independently valuable. Slices 1–2 and 6a–c are pure/hermetic; 3–5 touch
files or live xLights. Sequencing rationale: 1→2 gives the convergence proof before anything writes;
3's spike is the highest-uncertainty item so it front-runs the writer; 6a–c are independent of 3–5 (the
manifest can be emitted for the already-onboarded layout from slice 2) and can land in parallel; 7 is
deferred because the current layout resolves fully via steps 1–4.

## 1. Slice 1 — Classifier + spatial (xlights-core, pure)

- [ ] 1.1 Add `Prop` fields `mirror_of: str | None = None`, `string_type: str = ""`,
  `submodels: list[str] = field(default_factory=list)` to `knowledge/layout_semantics.py` (defaulted,
  backward-compatible). Test: existing `build_sem_groups` tests still pass.
- [ ] 1.2 New `knowledge/layout_classify.py::parse_props(rgb_path, *, layout_group="Default") ->
  list[Prop]` — dependency-free parser, one Prop per `<model>` in the given preview (spec §8: default
  preview only). Populate `name`, `display_as`, `nodes` (Custom → `max(CustomModel grid)`; Cube →
  `parm1*parm2*parm3`; else `parm1*parm2`, mirroring `preview/layout.py:141-149`), `wx/wy`
  (WorldPosX/Y), `groups` (reverse-indexed from `<modelGroups>`), `string_type`, `submodels`. Roles/
  spatial left at defaults.
- [ ] 1.3 `DISPLAYAS_ROLE` map + step 1; `MEGA_TREE_NODES=600` + `_tree_role` step 2 (sole-largest tree
  → MEGA_TREE); `NAME_HEURISTICS` table + step 3; group-hints step 4. `classify(props) -> ClassifyResult`
  runs steps 1–4 in order, each touching only unresolved props; sets role + confidence (1.0/1.0/0.9/0.85,
  unresolved → CUSTOM_PROP @ 0.5); returns resolved props + the unresolved tail.
- [ ] 1.4 `capability(role, nodes, string_type) -> str` per the design matrix (2D_SURFACE/2D_RADIAL/
  LINEAR_HIGH/LINEAR_LOW/POINT/SPECIAL; non-RGB StringType → POINT override; dense-Custom → MATRIX).
- [ ] 1.5 `derive_spatial(props, *, invert_x=False) -> SpatialSummary(width_units, focal_x, symmetric,
  excluded)`: outlier exclusion first, normalize, bands (0.33/0.66), sides (0.45/0.55), sweep order,
  mirror pairs (both directions), center_dist, focal flags (per design decision 5).
- [ ] 1.6 Fixture `tests/fixtures/layout_basic.xml` (mega Tree 360 1600 nodes, 6 mirrored arches, 4
  canes, outline Single Lines "Roof Left"/"Gutter R", a Window Frame, a Custom "Snowflake 1").
  Table-driven classifier tests: every DisplayAs mapping; tree threshold at 599/600/601; each
  name-heuristic family; group-hint inheritance; unresolved → CUSTOM_PROP @ 0.5 → review; capability
  matrix incl. the LINEAR_HIGH/LOW node cut and the StringType override.
- [ ] 1.7 Fixture `tests/fixtures/layout_tricky.xml` (sole 400-node tree → MEGA_TREE; parked model at
  X = −900 → outlier/review/excluded; dense whole-house Custom mesh → MATRIX by density; non-RGB
  StringType → POINT override; model in a non-Default LayoutGroup → excluded per §8; a group named "All
  Outline" hinting an unnamed Custom). Spatial tests: normalization with/without outliers; band cuts;
  side cuts at 0.449/0.451; sweep order; mirror tolerance edges (0.049/0.051); center_dist with/without
  a mega tree; `invert_x` flips sweep order and mirror pairs consistently.

## 2. Slice 2 — Manifest emit + convergence (xlights-core, pure)

- [ ] 2.1 New `knowledge/layout_manifest.py`: `PropRecord`, `PropPos`, `GroupRecord`, `DisplayBlock`,
  `LayoutManifest(version=1, generated, display, props, groups, review)` pydantic models per design
  decision 9.
- [ ] 2.2 `emit_manifest(m, show_dir) -> Path` writes `layout_semantics.json` (< 10 KB) to the show dir
  plus a copy under the cache root. `load_manifest(show_dir_or_path) -> LayoutManifest | None` tolerant:
  `None` on absence and on version-mismatch.
- [ ] 2.3 Dry-run diff engine `plan_diff(file_groups, plan_groups)` → three-way per-group diff
  (only-in-file / only-in-plan / member-order-changed).
- [ ] 2.4 Fixture `tests/fixtures/layout_real.xml` — sanitized copy of the user's actual layout (81
  models, personal metadata stripped) + its golden manifest. Convergence acceptance test: classify +
  derive + `build_sem_groups` on `layout_real.xml` diffs empty (or explained-only) against the file's
  current SEM_ groups.
- [ ] 2.5 Manifest tests: schema round-trip; <0.8 confidence → `review`; < 10 KB on the real fixture;
  `load_manifest` returns `None` on absence and on version-mismatch (forward-compat guard).

## 3. Slice 3 — The SEM_ group writer (xlights-core + live-verified)

- [ ] 3.1 **Round-trip spike:** create one group in each §5.7 mode in the target xLights UI, save, diff
  the XML; pin `LAYOUT_MODE_ORDERED`/`LAYOUT_MODE_ENSEMBLE` strings and the attribute name; commit the
  artifact as `tests/fixtures/layout_modes_roundtrip.xml`. (Resolves Open Question 1 before any writer
  code merges.)
- [ ] 3.2 `layout_modes(groups) -> dict[str, str]` (spec §5.7: `_LTR` → ordered, else ensemble) in
  `knowledge/layout_semantics.py`.
- [ ] 3.3 `write_sem_groups(rgb_path, groups, *, modes=None, grid_size=SEM_GRID_SIZE, backup=True) ->
  WriteReport` per design decision 6: timestamped backup; remove `^SEM_` groups; append one `<modelGroup>`
  per plan entry (name, models, LayoutGroup="Default", GridSize, layout-mode attr); atomic tmp +
  `os.replace`; NEVER touch non-SEM_ groups. `WriteReport(created, replaced, kept_user_groups, backup)`.
- [ ] 3.4 No-op detection: compare the serialized SEM_ subtree before replacing; skip the file write AND
  the backup when identical (same contract as `patch_sem_gridsize` returning 0).
- [ ] 3.5 xLights-must-be-closed guard: `XLightsClient.get_version()` short-timeout probe; refuse to
  write (or wait-and-poll) if the port answers.
- [ ] 3.6 Writer tests: write → re-parse → equal plan; re-run → no-op (mtime unchanged); user groups and
  views untouched; SEM_ fully replaced (a stale `SEM_OLD` disappears); GridSize + mode attributes
  present; output re-parses under `parse_models()`; backup created once per real write; assert
  byte-compatible attributes against `layout_modes_roundtrip.xml`.
- [ ] 3.7 Live-verify (once, `-m live`): run the writer on the real layout expecting a no-op.

## 4. Slice 4 — The guided CLI flow (orchestrator)

- [ ] 4.1 `pipeline/init_layout.py::run_init_layout(args)` implementing the seven-step flow (locate →
  analyze → review → plan+diff → write → validate → finish) per design decision 13.
- [ ] 4.2 `cli.py`: `sub.add_parser("init-layout", ...)` beside `run`/`regen`/`edit-brief` with flags
  `--show-folder --dry-run --yes --no-validate --no-llm --invert-x --review-web`; must not require an
  LLM key and must not require xLights running.
- [ ] 4.3 Terminal review queue: numbered prompt per prop with confidence < 0.8 and each excluded
  outlier, offering the role enum, "accept as CUSTOM_PROP", or "exclude"; `--yes` accepts all (still
  recorded in the manifest `review` array; unreviewed manifest → CLI warning exit).
- [ ] 4.4 `layout_overrides.json` support: `{"prop_name": {"role": ...}}` applied after step 4, before
  the LLM step.
- [ ] 4.5 `--dry-run` prints the three-way diff and the would-be manifest and stops before the write.
- [ ] 4.6 Rewrite `docs/usage.md` "One-time layout setup (SEM_ groups)" (lines 53–69) around the command.
- [ ] 4.7 CLI tests: argument wiring, review-queue answer parsing, `--dry-run` on the convergence fixture
  printing an empty diff, driven through `main(argv)` with a stubbed flow.

## 5. Slice 5 — Automated §7 validation (orchestrator, offline)

- [ ] 5.1 `pipeline/layout_validate.py::write_fseq_v2_uncompressed(path, frames, frame_ms=50)` — minimal
  uncompressed FSEQ v2 writer the read side `preview/fseq.py::load_fseq` round-trips.
- [ ] 5.2 `role_color_frames(manifest, models)` (one frame per role, member channels at a hue-distant
  color, rest dark — spec §7.1); `sweep_frames(group, models)` (K frames, member i lit alone in frame i
  — spec §7.3); `ROLE_COLORS` table.
- [ ] 5.3 `check_sweep(frames, renderer)` — deterministic: per frame the lit-pixel world-x centroid
  (`renderer.world[ch]` weighted by channel value) must be strictly increasing; backward → recommend
  `--invert-x`. Plus structural checks: every SEM_ member exists; no SEM_ group empty; `SEM_ALL`
  excludes SINGING_FACE/SIGN; every `_LTR` member order matches `sweep_order`.
- [ ] 5.4 `role_color_sheet(renderer, frames, labels) -> Path` — contact sheet PNG next to the manifest.
- [ ] 5.5 CLI `--invert-x` loop: on a sweep-test failure offer to re-run with `--invert-x` automatically.
- [ ] 5.6 Optional visual-critic pass: send the contact sheet to `agents/visual_critic.py` with spec
  §7.2's question and the known-failure hints; findings advisory/printed, never auto-mutating.
- [ ] 5.7 Validation tests: `write_fseq_v2_uncompressed` → `load_fseq` round-trip; sweep centroid passes
  on `layout_basic`, fails (and recommends invert) on the same layout with x negated; role frames light
  exactly the member channels; the contact sheet renders (skip if `[preview]` extras absent, mirroring
  `test_preview.py`).

## 6. Slice 6 — Consume the manifest (three independent integrations)

### 6a. Director traits/props block
- [ ] 6a.1 `agents/director.py::render_layout_block(manifest, groups) -> str` (~1 KB: role, member count,
  ~nodes, band, symmetry/order per group + one display line).
- [ ] 6a.2 `render_input(brief, groups, placeable_types, manifest=None)`: keep the flat AVAILABLE GROUPS
  list unchanged; append the block only when a manifest exists.
- [ ] 6a.3 Wire in `run.py` behind `load_manifest()`; absent manifest → byte-identical prompt.
- [ ] 6a.4 Tests: `render_input` without manifest byte-identical to today (snapshot); with manifest
  contains the expected group lines and stays under a size budget.

### 6b. QA capability gating
- [ ] 6b.1 `qa/rules.py::_target_res(target, manifest)` — res classes of a target (prop class, or union
  of member classes for a group); cached per manifest.
- [ ] 6b.2 `_is_linear(target, manifest=None)` returns `res <= {"LINEAR_HIGH","LINEAR_LOW"}` when a
  manifest is present, else the prefix fallback; `evaluate(instructions, plan)` grows optional
  `manifest=None`.
- [ ] 6b.3 Tests: manifest-gated `_is_linear` flags a texture on a linear-membered group with a non-SEM
  name, and un-flags a matrix-dominated group the prefix rule would wrongly pass; existing QA tests
  unmodified and green.

### 6c. Derived choreography vocabulary
- [ ] 6c.1 `pipeline/semantic_groups.py`: `ChoreoVocabulary` (frozen), `DEFAULT_VOCAB` = today's
  constants, `derive_vocabulary(manifest) -> ChoreoVocabulary` per design decision 11 (RING rank,
  BACKBEAT, BED/PEAK_BROAD, HERO).
- [ ] 6c.2 Thread `vocab: ChoreoVocabulary = DEFAULT_VOCAB` through `beats.py::select_rhythm_groups` and
  `place_beat_accents`, and the `weave.py` bed-selection lookup; `run.py` computes the vocabulary once
  per run from the loaded manifest. Every `if g in avail` guard stays.
- [ ] 6c.3 Tests: `derive_vocabulary(None) == DEFAULT_VOCAB`; an arch-less synthetic manifest ranks
  canes/minis into the ring; the golden pipeline snapshot is unchanged on the real-layout manifest
  (derivation reproduces today's constants before shipping as default).

## 7. Slice 7 — LLM fallback (orchestrator, last)

- [ ] 7.1 `agents/layout_classifier.py`: `PropRoleGuess` (role `Literal[...]` over the 16 canonical
  roles, `confidence`, `rationale`), `PropRoleGuesses`, `layout_classifier_agent()`, `render_input`
  (spec §3.5 compact record per prop).
- [ ] 7.2 Add a `classifier` role to `models/config.yaml` routed to the worker tier.
- [ ] 7.3 One batched call for the whole unresolved tail; any guess with confidence < 0.8 (and every
  prop not returned) → review queue; `--no-llm` bypass; no key → deterministic path.
- [ ] 7.4 Tests: enum-constrained output rejects an invented role; a batched fixture resolves several
  props; low-confidence guesses route to review; `--no-llm` produces the deterministic tail.

## 8. Cross-cutting close-out

- [ ] 8.1 Acceptance sweep: `xlo init-layout --dry-run` on the real layout prints an empty/explained
  diff; a fresh fixture show folder produces SEM_ groups + GridSize + §5.7 modes + "SEM Master" view +
  valid `layout_semantics.json` < 10 KB with xLights closed, atomically, with a backup; re-run is a
  byte-level no-op.
- [ ] 8.2 Live-verify once (`-m live`): write groups with xLights closed, start xLights, confirm
  `get_group_names()` contains the SEM_ set, run `targetable_groups`, place one effect per `_LTR` group,
  export a preview; one human watch of perceptual sweep direction.
