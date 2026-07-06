## 1. I3 — constants consolidation (do first; pure data move)

Destination map (keep verbatim during implementation):

| Name | Value | Current location | Destination | Notes |
|------|-------|------------------|-------------|-------|
| `REGRESS_MARGIN` | 1 | `run.py:58` | `tuning.py` (refine section) | Re-export from `run.py` + `refine_loop.py` |
| `STALL_LIMIT` | 2 | `run.py:59` | `tuning.py` | ditto |
| `REFINE_SKIP_OBJECTIVE` | 88 | `run.py:62` | `tuning.py` | `_refine_skip_objective()` moves to `refine_loop.py`; keep the 42-run revision-log-analysis comment with the constant; `test_refine.py:364` imports both from `run` — re-export |
| `SPEED_KEYS` | 17-effect map | `beats.py:90–111` | `effect_meta.py` | `effect_speed_setting` stays in `beats.py`, reads the table; `test_effect_speed.py:5` imports from `beats` — re-export |
| `DIRECTION_KNOBS` | 12-effect map | `weave.py:55–93` | `effect_meta.py` | `direction_setting`/`_effective_direction` stay in `weave.py`; re-export |
| `ENERGY_BAND` | 33-effect map | `qa/rules.py:15–24` | `effect_meta.py` | rules QA keeps enforcing; re-export |
| `DURATION_HIT/PHRASE/CELLABLE` | 3 sets | `qa/rules.py:29–32` | `effect_meta.py` (`duration_class`) | kills cross-module imports at `weave.py:227`, `beats.py:583` |
| `PHRASE_BARS` / `CELL_BARS` | 8 / 2 | `qa/rules.py:33–34` | `tuning.py` | behavior dials (bar math) |
| `MOTION_EFFECTS`, `MOTION_SHARE_MIN` | set / 0.30 | `qa/rules.py:40–42` | derived in `effect_meta.py` / `tuning.py` | `MOTION_SHARE_MIN` is an I7 tuning lever |
| `_BED_EFFECTS`, `_NATIVE_BOUNCE`, `_CHASE_FAMILY` | 3 sets | `weave.py:49,95,99` | `effect_meta.py` flags | private today, no import compat needed |
| `STROBE_CAP_MS`, `SHIMMER_BARS` | 1000 / 2 | `qa/rules.py:48–49` | stay (catalog rule #7 verbatim) | |
| `CARRIER_ROTATION` | 4 effects | `weave.py:198` | stays in `weave.py` | improve-musicality Phase 1 re-keys it |

- [ ] 1.1 Create `pipeline/effect_meta.py` with `@dataclass(frozen=True) EffectMeta` (`speed`,
  `directions`, `energy_band`, `duration_class: Literal["hit","phrase","cellable","free"]`,
  `bed_capable`, `native_bounce`, `chase_family`) and `EFFECT_META: dict[str, EffectMeta]` — one row
  per effect type, each row citing corpus provenance in a comment (`2026-06-12-add-settings-hygiene`
  for SPEED_KEYS ranges, `2026-06-12-add-directional-sweeps` for DIRECTION_KNOBS values).
- [ ] 1.2 Add derived views in `effect_meta.py`: `SPEED_KEYS`, `DIRECTION_KNOBS`, `ENERGY_BAND`,
  `DURATION_HIT`, `DURATION_PHRASE`, `DURATION_CELLABLE`, `MOTION_EFFECTS = DURATION_CELLABLE |
  {"Fire","Galaxy"}`.
- [ ] 1.3 Change `beats.py`, `weave.py`, `qa/rules.py` to import from `effect_meta`; leave re-export
  aliases in each original module (`from .effect_meta import SPEED_KEYS  # re-export: tests + external
  callers`). Remove the cross-module imports at `weave.py:227` and `beats.py:583`.
- [ ] 1.4 Add a **table-integrity test**: derived views from `EFFECT_META` equal a frozen copy of
  today's literals for `SPEED_KEYS`, `DIRECTION_KNOBS`, `ENERGY_BAND`, `DURATION_*`, `MOTION_EFFECTS`
  (checked in once as the drift guard for the transcription).
- [ ] 1.5 Run the full suite; `fixtures/golden_instructions.json` must be **byte-identical** (no
  `XLO_REGEN_GOLDEN`). If step 1 needs a golden regen, the table transcription has a bug — fix it.

## 2. I3 — refine thresholds into `tuning.py`

- [ ] 2.1 Move `REGRESS_MARGIN`, `STALL_LIMIT`, `REFINE_SKIP_OBJECTIVE` (+ `PHRASE_BARS`, `CELL_BARS`,
  `MOTION_SHARE_MIN`) under a new `# -- refine loop control` section in `tuning.py`, keeping each
  constant's provenance comment; amend the `tuning.py` docstring with a one-line scope note.
- [ ] 2.2 Re-export the thresholds from `run.py` so `test_refine.py:364`
  (`from ...pipeline.run import _refine_loop, REFINE_SKIP_OBJECTIVE`) keeps working.

## 3. I3 — extract the pure guards

- [ ] 3.1 Create `pipeline/refine_loop.py`; move `should_skip_refine(first_pass_objective,
  skip_objective) -> bool`, `refine_skip_objective() -> int` (reads `XLO_REFINE_SKIP_OBJECTIVE`, falls
  back to `tuning.REFINE_SKIP_OBJECTIVE`), `plateau_signature(report, verdict) -> tuple`
  (`(objective, advisory, frozenset((section, issue[:64])))`), `design_implicated(plan, section_index,
  findings) -> bool` (rules-finding names a planned effect_type). Call them from the still-monolithic
  loop in `run.py`.
- [ ] 3.2 Add direct unit tests in `tests/test_refine_guards.py` for each pure guard — no loop
  harness: `should_skip_refine` (None disables; equality skips); `plateau_signature`
  equality/inequality incl. issue truncation at 64 chars; `design_implicated` (rules metric + effect
  mention required; wrong section / non-rules metric → False).

## 4. I3 — extract the stateful guards

- [ ] 4.1 `BestTracker` in `refine_loop.py` — owns `best`/`best_applied`/`best_obj`/`open_is_best` +
  stall (guards #4/#5/#9). Port the exact comparison operators verbatim: revert is `obj < best - margin`,
  gain is `obj > best + margin`, a held objective keeps but doesn't reset stall; keep-path
  `max(best_obj, obj)` (run.py:288). Methods: `assess(obj) -> Outcome(reverted, gained)`,
  `keep(instructions, applied, obj)`, `revert() -> (instructions, applied)`, `stalled` property
  (`stall >= stall_limit`).
- [ ] 4.2 `EscalationLedger` in `refine_loop.py` — owns `ledger` (guard #6) + `redesigned` (guard #7):
  `record(rev)`, `prior_sections() -> set[int]`, `should_escalate(si, plan, findings)` (si not yet
  redesigned AND (repeat offender OR `design_implicated(...)`)), `mark_redesigned(si)`.
- [ ] 4.3 Unit-test the boundary arithmetic in `test_refine_guards.py`: `obj == best - margin` keeps;
  `obj == best + margin` keeps-without-gain; stall reset only on gain; `EscalationLedger.should_escalate`
  once-per-run + repeat-offender path + implicated path.

## 5. I3 — extract collaborators + the loop

- [ ] 5.1 `ReportBuilder` — wraps `_report`/`_obj`: flush `save_as` → `real_render.refresh` →
  `qa_eval(..., sampler=…)`, preserving the legacy 5-arg qa signature branch for injected fakes
  (`def qa(instructions, analysis, plan, applied, groups)`). Unit-test the **save-before-sample**
  ordering with a call-order-recording fake.
- [ ] 5.2 `IterationRecorder` — wraps `_record`/`_bundle`: `RevisionLogRecord` assembly + review-bundle
  path guard; pure observability, never raises into the loop.
- [ ] 5.3 `apply_revisions(st, revisions, *, regen, redesign, ledger, findings, log)` — guard #7 +
  splice: per revision, maybe escalate design (structure pinned: `start_ms/end_ms` copied back,
  `target_groups` defaulted), then `replace_section(st.instructions, si, await regen(rev))` and
  `ledger.record(rev)`. Keep the lazy-agent rules (default generator only built when no `regenerate`
  injected; `section_redesigner()` lazy in the redesign path).
- [ ] 5.4 Move the loop body into `async def refine_loop(st, *, client, emitter, ..., skip_objective=None)`
  — same signature and behavior as today's `_refine_loop`; keep every DI keyword seam (`judge`, `qa`,
  `regenerate`, `redesign`, `checkpoint`, `visual_critique`, `revlog`, `sampler`, `clock`). Preserve
  the **re-emit-on-revert** ordering (close → emit → mark `open_is_best`). In `run.py` set
  `_refine_loop = refine_loop`; keep `regenerate_section` (shared with `xlo regen` via `pipeline/regen.py`)
  and the checkpoint functions (`_auto_checkpoint`, imported by `cli.py:13`).
- [ ] 5.5 Unit-test the re-emit-on-revert ordering with a call-order-recording fake client/emitter.

## 6. I3 — verify + import compat + docs

- [ ] 6.1 **Import-compat test**: assert historical paths still resolve —
  `from xlights_orchestrator.pipeline.run import _refine_loop, REFINE_SKIP_OBJECTIVE`;
  `from xlights_orchestrator.pipeline.beats import SPEED_KEYS`;
  `from xlights_orchestrator.qa.rules import ENERGY_BAND, DURATION_CELLABLE`.
- [ ] 6.2 Full suite (65 test files) green with an unchanged golden fixture; `test_refine.py`,
  `test_visual.py`, `test_design_escalation.py`, `test_revision_log.py` pass unmodified; revision-log
  output (JSONL + md) for an identical run is field-for-field identical (spot-check via
  `test_revision_log.py`).
- [ ] 6.3 Update `docs/architecture` pipeline notes; note the new `pipeline/refine_loop.py` and
  `pipeline/effect_meta.py` modules in the roadmap scorecard.

## 7. I4 — reproduce and pin the mypy baseline

- [ ] 7.1 Run the CI-equivalent mypy locally (`uv sync --extra preview && uv run --no-sync mypy`);
  confirm **41 errors / 15 files / 87 source files** (mypy 2.1.0). Retain the scratch capture for
  diffing.
- [ ] 7.2 Add `types-PyYAML` to `[dependency-groups].dev`.

## 8. I4 — Category-A burn-down (Optional State, ~18 findings)

- [ ] 8.1 Add `def require(value: T | None, name: str) -> T` to `pipeline/state.py` (raises
  `RuntimeError` naming the field).
- [ ] 8.2 Apply `require()` in `pipeline/generate.py` (`realize_section`, `generate_instructions`):
  the 11 `union-attr` at lines 153,156,157,159,239,244,247,248,252,256,259 (`st.show_plan.<attr>` /
  `st.music_brief.repetition_map`).
- [ ] 8.3 Apply in `pipeline/run.py:131,257,261` (show_plan); restructure `:366` to
  `_ly = getattr(...) or {}` before `.get` (mirroring :358); annotate `ledger: list[RevisionBrief] = []`
  at :191; annotate `revlog` at :459 — prefer a shared `RevisionSink` Protocol
  (`def write(self, record) -> None`) in `revision_log.py` over `revlog: RevisionLog | NullRevisionLog`.
- [ ] 8.4 Apply in `pipeline/regen.py:93,133` (show_plan / song_analysis — `load_cached_state`
  guarantees both) and `cli.py:32`.

## 9. I4 — Category-B seams (~4 findings)

- [ ] 9.1 `agents/panel.py`: define `class RunsAgent(Protocol): async def run(self, prompt: str) -> Any`
  and type `AnalystSpec.agent` as it (Protocol preferred — test fakes are `SimpleNamespace`s); fix `:135`
  `attr-defined`. For `:144` `misc`, keep `isinstance(r, BaseException)` for the guard and unpack in an
  `else` branch so mypy narrows the `gather(..., return_exceptions=True)` union.
- [ ] 9.2 `models/registry.py:61`: build the TypedDict literally — `settings: AnthropicModelSettings =
  {}` then conditional key assignments (`settings["anthropic_thinking"] = ...`) instead of
  `AnthropicModelSettings(**kw)`.

## 10. I4 — mechanical remainder (~19 findings)

- [ ] 10.1 `qa/__init__.py:34`: annotate the local `subscores` as `dict[str, float]`.
- [ ] 10.2 `qa/rules.py:90`: annotate the empty `events` list.
- [ ] 10.3 `pipeline/beats.py:197,199`: `key=lambda k: d[k]` (keys come from the same dict);
  `:605` annotate the variable `float` at first assignment.
- [ ] 10.4 `pipeline/visual.py:185`: annotate attrs in `RealRender.__init__` (`self._stamp: float |
  None = None`).
- [ ] 10.5 `xlights_core/knowledge/layout_semantics.py:61`: `key=lambda p: p.<field> or 0`.
- [ ] 10.6 `xlights_core/audio/lyrics_align.py:112,118`: annotate `sections`; guard the Optional dict
  before indexing (`if d is None: continue`).
- [ ] 10.7 `xlights_core/preview/layout.py`: `:152` `float(attr or 0)`; `:278–287` rename the scalar
  (the reuse of one name for a list and its element is the actual smell).
- [ ] 10.8 `xlights_core/preview/render.py:115,116`: `assert proc.stdin is not None` after
  `Popen(..., stdin=PIPE)`.
- [ ] 10.9 `xlights_core/knowledge/xsq_extractor.py:72`: annotate `skipped`.
- [ ] 10.10 Run the full suite (`uv run --no-sync pytest`, then the golden pipeline) and `ruff check` —
  every fix above must be zero-behavior; the suite + unchanged golden snapshot are the proof.

## 11. I4 — py.typed markers

- [ ] 11.1 Add empty `py.typed` at `packages/xlights-core/src/xlights_core/py.typed`,
  `packages/xlights-orchestrator/src/xlights_orchestrator/py.typed`,
  `packages/xlights-mcp/src/xlights_mcp/py.typed`.
- [ ] 11.2 Verify wheel inclusion per package: `uv build --package <pkg> && unzip -l dist/<pkg>-*.whl |
  grep py.typed`.

## 12. I4 — harden config and flip the gate

- [ ] 12.1 Add to root `[tool.mypy]`: `warn_unused_ignores = true`, `warn_redundant_casts = true`,
  `check_untyped_defs = true`; keep `ignore_missing_imports = true`; do NOT enable
  `strict`/`disallow_untyped_defs`/`disallow_any_*`. Fix anything the new warnings surface (expected
  near-zero; `warn_unused_ignores` may flag leftovers).
- [ ] 12.2 **Flip CI (BREAKING):** remove `continue-on-error: true` from the mypy step in
  `.github/workflows/ci.yml`; rename it `Type check (mypy)`.
- [ ] 12.3 Rewrite the stale "advisory / backlog is being triaged" comments in `ci.yml` (lines 44–46)
  and root `pyproject.toml` (lines 31–34) to describe the hard gate; document the canonical invocation
  (`uv sync --extra preview && uv run --no-sync mypy`) in the workflow comment.
- [ ] 12.4 **Gate self-test:** verify locally that an injected error (`x: int = "a"`) makes
  `uv run --no-sync mypy` exit ≠ 0 (guards against a silent `files=` misconfiguration). Optional:
  a one-line assertion that mypy checked ≥ 87 files.
- [ ] 12.5 New unit tests where a fix added runtime semantics: `require(None, "show_plan")` raises
  `RuntimeError` naming the field and `require(x, ...)` is identity (in `tests/test_orchestrator.py`);
  `registry._settings()` yields the exact settings dict for a thinking+effort role and `None` for a
  bare one (pins the TypedDict restyle — extend registry coverage / I6's `test_registry`).

## 13. I6 — test_registry.py (smallest, zero fakes)

- [ ] 13.1 Autouse fixture that clears `registry._cfg.cache_clear()` on entry and exit (the `lru_cache`
  hazard).
- [ ] 13.2 Real-config invariants: every role has an entry for every provider in `providers:`; model
  strings prefixed `anthropic:`/`google:`.
- [ ] 13.3 Behavior against a fixture YAML: `active_provider()` default + `XLO_PROVIDER=gemini` wins;
  `model_string("judge")` = `"anthropic:claude-opus-4-8"` default / `"google:gemini-3.5-flash"` under
  gemini; unknown role/provider → `KeyError`.
- [ ] 13.4 `model_snapshot()` returns all six roles under both providers, values `provider-prefix +
  model`. `_settings("director")` → `AnthropicModelSettings` with `anthropic_thinking={"type":
  "adaptive"}` + `anthropic_effort="high"`; `_settings("generator")` has thinking but no effort; any
  gemini role → `None`; **no sampling keys ever present** (the Opus-400 invariant, registry.py:60).
  `build_agent("judge", output_type=JudgeVerdict, system_prompt="x")` constructs without network/API
  key and carries the expected model string.

## 14. I6 — test_cli.py (argparse wiring)

- [ ] 14.1 Capture-kwargs harness: monkeypatch `cli.run_pipeline` + `XLightsClient` (async-context
  stub) and assert the exact kwargs the CLI passes. `--song s.mp3` → `use_cache=True, refine=False,
  max_iterations=3, log_revisions=True, timing_tracks=True, save_as=safe_name("s.mp3")`, attended
  checkpoints (`interpret_checkpoint=_interpret_review`, `design_checkpoint=_design_review`,
  `checkpoint=None`).
- [ ] 14.2 The checkpoint matrix (cli.py:27–29, likeliest silent-regression site): `--auto` → both
  review gates `None`; `--refine --auto` → `checkpoint=_auto_checkpoint`; `--refine` alone →
  `checkpoint=None`. Flags: `--no-save` → `save_as=None`; `--name X` → `save_as="X"`;
  `--no-cache/--no-log/--no-timing-tracks` flip booleans; `--max-iterations 7` parses as int.
- [ ] 14.3 Guard exits: missing LLM key → `SystemExit("No LLM key found")` (monkeypatch `has_llm_key`
  → False); `edit-brief` with neither `--song` nor `--brief` → `SystemExit`; nonexistent brief path →
  `SystemExit` mentioning `run \`xlo run\``. `regen`: `--list`/omitted `--section` prints via
  `format_sections` and needs no key; `FileNotFoundError/IndexError` from `_regen` →
  `SystemExit(str(exc))` (cli.py:113–116); bad subcommand → argparse exit code 2. (A 3-line
  `build_parser()` extraction is acceptable if `main()` resists patching; do not restructure dispatch.)

## 15. I6 — test_brief_editor_http.py

- [ ] 15.1 Ephemeral-port server fixture: `ThreadingHTTPServer(("127.0.0.1", 0), _handler(...))` in a
  daemon thread, yields base URL, `server_close()` in teardown; drive with `urllib.request` (2s
  timeouts); `tmp_path` holds `creative_brief.json` + schema.
- [ ] 15.2 `GET /` → 200 `text/html`, body embeds the brief JSON + schema (`__BRIEF__`/`__SCHEMA__`
  substitutions) and escaped path; `GET /nope` → 404 JSON.
- [ ] 15.3 `POST /save` valid → 200 `{"ok": true}`, file contains the edit, `$schema` first,
  un-rendered `group_motifs` preserved. Structurally invalid (e.g. `sections` not a list) → 400 with
  `error` truncated ≤300 chars (brief_editor.py:201) and the file untouched (atomic `.tmp`-replace
  never ran). Missing/zero Content-Length → 400, not a hang.
- [ ] 15.4 `serve()`-level schema-missing fallback: page renders with `SCHEMA={}`
  (brief_editor.py:209–210) via `render_page` composition or a handler built with `schema={}`.

## 16. I6 — test_mcp_server.py

- [ ] 16.1 `_ctx(client)` helper (two `SimpleNamespace` layers:
  `request_context.lifespan_context["client"]`) + duck-typed fake client; call tool coroutines
  directly (`await server.xl_get_models(_ctx(fake))`), falling back to `mcp._tool_manager` or explicit
  `mcp.tool()(fn)` registration if a FastMCP version wraps them un-callably. May require adding `mcp`
  to the root test env — verify CI's `uv sync` installs the workspace member.
- [ ] 16.2 Read tools (`xl_get_version`, `xl_get_show_folder`, `xl_get_models`, `xl_get_model`,
  `xl_get_controllers`): pass-through shape (`xl_get_models` → `{"models":[...], "groups":[...]}`;
  `xl_get_model`/`xl_get_controllers` → `model_dump()`ed dicts).
- [ ] 16.3 `_call` error translation: fake raising `XLightsConnectionError("down")` →
  `RuntimeError("XLightsConnectionError: down")`; same for `KnobValueError`, `ValueError`, `KeyError`.
- [ ] 16.4 Write tools: `xl_new_sequence` forwards `duration_secs/frame_ms/media_file/force` verbatim
  (default `force=False` reaches the client); `xl_close_sequence` forwards `force/quiet`;
  `xl_save_sequence` passes `name=None` through.
- [ ] 16.5 `xl_add_effect_raw` gates: `end_ms <= start_ms` → `ValueError("bad timing…")` before any
  client call; target not in `get_models()` → `ValueError`; client `worked=false` →
  `RuntimeError("PresetPlacementError: …")`. `xl_add_effect`/`xl_validate_preset`: monkeypatch
  `server.place_preset`/`server.validate_preset` to capture knob/palette/layer forwarding. Audio: with
  the `xlights_core.audio` import forced to raise, `xl_analyze_song` →
  `RuntimeError("audio extra not installed: …")` not an ImportError traceback.
- [ ] 16.6 One `httpx.MockTransport` composition smoke test reusing `tests/fixtures/*.json` to prove
  the serialization path.

## 17. I6 — schema-drift guard

- [ ] 17.1 Harvest + redact real cached artifacts (trimmed to 1–2 sections) into
  `tests/fixtures/agent_payloads/`: `show_plan.json`, `section_plan.json`, `section_effects.json`,
  `music_brief.json`, `structure_out.json`, `rhythm_out.json`, `harmony_out.json`, `lyric_out.json`,
  `judge_verdict.json`, `visual_findings.json`, `instructions.json`, `song_analysis.json`,
  `revision_log_record.json` (≥12 payloads). Seed from real artifacts, NOT `model_dump()` of fresh
  objects.
- [ ] 17.2 `tests/test_schema_drift.py`: parametrized `model.model_validate_json(payload)` over all
  cases; a `test_instructions_cache_shape` that validates each item in `instructions.json` as
  `EffectInstruction`. Document the failure protocol in the module docstring (revert to a
  backward-compatible field-with-default, OR bump the fixture *and* the cache key per the run.py:390
  precedent).
- [ ] 17.3 `required_fields.json` manifest + a test comparing each model's `model_json_schema()`
  required-field set against it, so an *additive* required field fails even if the payload includes it.
- [ ] 17.4 Provide an `XLO_REGEN_PAYLOADS=1` helper script (deliberate regeneration only — never an
  automatic rewrite).

## 18. Shared — advisory CI coverage (optional; own commit, droppable)

- [ ] 18.1 Add `pytest-cov` to `[dependency-groups].dev`.
- [ ] 18.2 In `.github/workflows/ci.yml` run `uv run --no-sync pytest --cov=packages
  --cov-report=term-missing:skip-covered --cov-report=xml`; publish a `$GITHUB_STEP_SUMMARY` line +
  upload `coverage.xml` as an artifact. **No** `--cov-fail-under` (visibility only); no external upload
  service. Measure runtime before merging.

## 19. Land

- [ ] 19.1 I3, I4, and I6 each land as their own PR(s) on a branch — never commit to `main` directly.
  Within I4, order commits so each is green under the advisory gate; the CI flip is last. Within I6,
  each of steps 13–17 can land as its own small PR (none depends on another).
- [ ] 19.2 Full hermetic suite green under `-m "not live"` with no API keys; golden fixture unchanged;
  `ruff check` clean.
