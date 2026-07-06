## 1. F-B — probe & freeze the templates

- [ ] 1.1 Hand-author one static and one scrolling Text effect in the **pinned** xLights version;
  extract both settings strings from the saved `.xsq`'s `EffectDB` via `parse_settings` (a five-line
  script); commit them as the frozen template + a fixture under `tests/fixtures/`.
- [x] 1.2 Reconcile the §3.2 Text key table against the observed probe strings; document any
  version-gated keys and add them to the `DROP_KEYS`-style strip list (`editing.py:22` is the
  precedent). Confirm whether xLights escapes commas in `E_TEXTCTRL_Text` on save, and whether
  `addEffect` accepts multi-line text (v1 may restrict to single-line).

## 2. F-B — `knowledge/direct_settings.py`

- [x] 2.1 Create `knowledge/direct_settings.py` with `DIRECT_TYPES = frozenset({"Text","Faces"})`.
- [x] 2.2 Implement `build_text_settings(text, *, movement="none", font_size=12, bold=True, speed=10,
  center=True) -> str` emitting the frozen Text key set; validate `movement` against `_TEXT_DIRS`;
  sanitize glyph text (documented comma/equals substitution). Its output SHALL pass ring-1 validation.
- [x] 2.3 Add a `build_faces_settings(*, timing_track, face_definition, eyes="Auto", outline=True) ->
  str` **skeleton that raises** until F-D lands its probe; it requires both reference arguments and
  performs no defaulting.
- [x] 2.4 Unit tests per builder: round-trip (`serialize_settings(parse_settings(s)) == s`), key-kind
  audit (every key classifies via `classify_kind`; no `"other"` except the audited font-picker key),
  clamped/invalid inputs (negative font size, unknown movement → `ValueError`).
- [ ] 2.5 Fixture-parity test: `build_text_settings` output differs from the frozen probe only in the
  deliberately variable keys (text, dir, speed, size) — the "corpus of one" invariant.
- [x] 2.6 Parser property tests: `parse_settings(build_text_settings(...))` yields unique keys, values
  contain no commas, and glyph text with commas/equals is rejected or escaped explicitly (pin the
  chosen decision).

## 3. F-B — refactor `editing.py` + `place_direct`

- [x] 3.1 Extract `_merge_extra_settings(settings, extra)` (first-occurrence-wins override + append)
  and `_check_timing_and_target(...)` from `place_preset`; `place_preset` calls them — behavior-
  preserving, `tests/test_editing.py` and the golden must pass untouched.
- [x] 3.2 Add `place_direct(client, target, effect_type, settings, *, palette_colors=None,
  extra_settings=None, layer=0, start_ms, end_ms) -> str`: validate the settings string
  syntactically, merge `extra_settings` via the shared helper, resolve palette via
  `palette_from_colors`, `add_effect`; raise `PresetPlacementError` on `worked=false`, `ValueError` on
  bad timing/target.
- [x] 3.3 Parity test: for identical `extra_settings`, `place_direct` and `place_preset` produce
  identical merged strings and identical palette handling.

## 4. F-B — schema + emitter branch

- [x] 4.1 Add `EffectInstruction.direct_settings: str = ""` (`show_plan.py:63–80`); `look_id=""` allowed
  when `direct_settings` is set; the field is NOT surfaced in any generator prompt.
- [x] 4.2 Branch `effect_emitter.apply_instructions` (around line 116): `if ins.direct_settings ->
  place_direct(... extra_settings=extra ...)` (still carrying `B_CHOICE_BufferStyle`) else the exact
  `place_preset` call today; identical layer accounting (`_free_layer`/`_top_layer`/occupancy) and
  `_SKIPPABLE` skip-on-failure for both branches.
- [x] 4.3 Back-compat tests: a pre-change cached `instructions` JSON (no `direct_settings` key) and the
  golden fixture load and compare unchanged — this change must NOT perturb the golden (nothing emits
  direct instructions yet).
- [x] 4.4 Emitter fake-client test (pattern of `tests/test_orchestrator.py` / `test_client.py` fakes):
  a direct instruction reaches `add_effect` with the exact settings string, correct layer accounting,
  and skip-on-failure parity.

## 5. F-B — guard rails, validation, docs

- [x] 5.1 Guard test: `DIRECT_TYPES ∩ placeable_effect_types() == ∅` so the LLM menu never grows these
  types silently if the catalog is re-mined with different filters. Add a placement-rules note that
  direct types bypass `candidate_look_ids`-based guards (`weave._valid_recipes`, `beats._accent_look`)
  by never entering recipes.
- [x] 5.2 Add `validate_direct(client, effect_type, settings)` (marked `live`) mirroring
  `validate_preset`'s scratch-sequence protocol (clean slate → place the frozen Text template on the
  Matrix model → `render_all` → assert `worked` → discard); wire into the live-verify checklist.
- [ ] 5.3 Docs: a short section in `docs/architecture/README.md` (or the knowledge package docstring)
  describing the two placement routes and the rule for choosing (mined look when one exists; direct
  only for `DIRECT_TYPES`, authored only by deterministic passes).
- [x] 5.4 Hermetic suite green (`pytest -m "not live"`); golden untouched.

## 6. F-F — phase 0: fixture + parser (hermetic today)

- [ ] 6.1 Author submodels in the target xLights build once (tree with rings + topper, outline with
  segments, window cells, plus a sub-buffer-type submodel for the preserve-unknown path); commit the
  saved XML as `tests/fixtures/layout_submodels.xml`.
- [ ] 6.2 Add the `SubModel` dataclass (`layout_semantics.py`); implement `<subModel>` parsing + node
  range expansion + kind/order heuristics (`SUBMODEL_KIND` table) in the F-E classifier
  (`layout_classify.py`/`parse_props()`), attaching records to the parent `Prop`. Preserve unknown
  submodel types verbatim.
- [ ] 6.3 Parser tests: fixture round-trip (names, ranges "1-50,101-150" → 100 nodes, kinds, order
  hints); unknown types preserved untouched; a model with zero submodels yields `[]`.
- [ ] 6.4 Ordering tests: ring order from `order_hint` vs mean-y geometry agree on the fixture; segment
  LTR order matches world-x; inverted-x flips it (shares F-E's `invert_x` tests).

## 7. F-F — phase 1: plan + manifest (hermetic today)

- [ ] 7.1 Implement `build_submodel_groups(props) -> dict[str, list[str]]` emitting
  `SEM_OUTLINE_SEGMENTS` (LTR), `SEM_TREE_ZONES` (bottom-up), per-zone singletons `SEM_TREE_ZONE_<i>`,
  `SEM_TREE_TOPPER`, `SEM_WINDOW_CELLS` with `Parent/SubModel` members; singletons excluded from
  ensemble beds; `canonical_order` `accent`/`rhythm` tier placement.
- [ ] 7.2 Manifest: submodel records `{"name","kind","nodes","order"}` on `PropRecord.submodels` and
  submodel-group records (`GroupRecord` shape with `ordered`/`layout_mode`); size budget holds
  (≤10 KB).
- [ ] 7.3 Group-plan tests: exact expected group set on the submodel fixture; **empty delta** on the
  real 0-submodel layout (the conditionality guard, asserted forever); singletons exclude ensemble
  membership; `canonical_order` tier placement; F-E dry-run diff includes the planned groups.

## 8. F-F — phase 2: writer + offline validation (hermetic + offline render today)

- [ ] 8.1 F-E's `write_sem_groups()` accepts `Parent/Sub` members unchanged (member strings are opaque
  to it); gate the whole submodel path behind an `--submodels` flag on `xlo init-layout` until phase 3
  clears.
- [ ] 8.2 Offline validation: parse node ranges → parent node indices → absolute channels
  (`start_channel + 3*node`, per `render.py:43`) → synthesize frames lighting one zone/segment at a
  time → generalize the F-E sweep-centroid check with an axis parameter (vertical y-increasing for
  `SEM_TREE_ZONES`, horizontal x for `SEM_OUTLINE_SEGMENTS`).
- [ ] 8.3 Offline-validation tests: synthesized zone frames pass the vertical centroid check; a
  deliberately misordered/shuffled group fails it.
- [ ] 8.4 `xlo init-layout --submodels --dry-run` shows the planned groups in the diff.

## 9. F-F — phase 3: live verification gate (hardware-blocked, `-m live`)

- [ ] 9.1 On real hardware: restart xLights, confirm submodel-membered `SEM_` groups load.
- [ ] 9.2 Run `targetable_groups()` — do the submodel groups probe targetable? Record the result.
- [ ] 9.3 Route-A experiment: try direct `addEffect` on `Model/Sub` and on the bare submodel name; log
  the status codes either way (xfail-tolerated), record in the change's design doc.
- [ ] 9.4 Place one chase on `SEM_OUTLINE_SEGMENTS` and one riser on `SEM_TREE_ZONES`, export, human
  watch (does the riser read as climbing; does the chase draw left-to-right). Flip the `--submodels`
  flag to default-on ONLY if group-load + probe + watch pass.

## 10. F-F — phase 4: choreography (logic today, perceptual on hardware), all `if zones`-guarded

- [ ] 10.1 Extend `RhythmRoles` (`beats.py:252`) with `zones: list[str]` and `topper: str | None`; in
  `place_beat_accents()` (line 296) map downbeats → bottom zone, backbeat positions
  (`_backbeat_positions`, line 287) → mid zone, sparkle strongest-hit selection → topper, when
  `follow_stem` is drums and zones exist.
- [ ] 10.2 Zone-direction weave sweeps (`weave.py:356–363`): direction vocabulary for zone groups maps
  up/down instead of left/right, so an ordered bottom-to-top group + "up" is the riser.
- [ ] 10.3 Outline-draw intro recipe (scene cookbook candidate): a single slow chase on
  `SEM_OUTLINE_SEGMENTS`. Director layout-block gains one line per submodel-bearing prop.
- [ ] 10.4 Choreography tests: `select_rhythm_groups` with zones maps downbeat/backbeat/sparkle to
  bottom/mid/topper; **without** zones, byte-identical output to today (golden pipeline snapshot
  unchanged).

## 11. F-F — phase 5: optional follow-ups (deferred)

- [ ] 11.1 Kick/snare spectral split of drum-stem onsets (new analyzer) — decide after watching phase-4
  output on hardware.
- [ ] 11.2 Route-A direct targeting if the phase-3 experiment succeeded; Sub-Buffer per-placement escape
  hatch (possibly via `extra_settings`); vendor-naming import mappings (sequencing guide line 223).

## 12. Land

- [ ] 12.1 Each feature/phase lands as its own PR (branch per change); do not commit to `main` directly.
- [ ] 12.2 Full hermetic suite green (`pytest -m "not live"`); the golden pipeline snapshot and
  `tests/test_editing.py` unchanged (zero fixture churn) for both features.
