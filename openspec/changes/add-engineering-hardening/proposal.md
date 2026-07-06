## Why

Three internal code-health items from the July-2026 roadmap (I3, I4, I6) that harden what already
exists so later feature work is safe. They share no runtime behavior change — they are refactor and
tooling — but each closes a class of silent decay.

- **I3 — `_refine_loop` is the highest-risk function in the codebase.** It began (change
  `2026-06-08-add-refine-loop`) as a simple test→judge→regenerate cycle with three terminators; five
  subsequent changes each threaded a new guard through the same body (objective-regression revert,
  plateau detector, design escalation, skip-high-objective gate, visual backstop flooring). The
  result is `pipeline/run.py:135–305` (~170 lines): seven control-flow guards, five-plus nested
  closures (`_regen`, `_redesign`, `_report`, `_obj`, `_record`, `_bundle`, `_design_implicated`),
  and a 20-parameter signature — every guard testable only through the whole loop.
  `improve-musicality` Phase 2 (treatments + energy-keyed coverage QA) and Phase 1's new advisory
  metrics flow through *exactly* this code; the roadmap sequences I3 before Phase 2. Separately,
  roadmap R3/R4 (constants consolidation) is only half done: `pipeline/tuning.py` gathers the
  show-feel dials, but refine thresholds and per-effect metadata tables remain scattered across four
  modules with cross-module imports.
- **I4 — mypy is advisory, so it decays.** The codebase is fully annotated (June R1) but CI runs
  mypy with `continue-on-error: true`; the workflow comment itself says the backlog "is being triaged
  before this becomes a hard gate." Advisory type-checking rots: nobody reads a red-but-ignorable
  check, findings pile onto the backlog invisibly, and annotations drift from truth. The backlog
  already contains real smells (`agents/panel.py` types an agent as bare `object` then calls `.run()`;
  `pipeline/generate.py` dereferences `st.show_plan.sections` on an `Optional`; `models/registry.py`
  builds `AnthropicModelSettings` via untyped `**kw` — the exact construction that silently 400'd when
  Opus rejected sampling params). No package ships a `py.typed` marker (PEP 561), so a fully-clean
  codebase still presents as *untyped* to any consumer, including our own cross-package boundary.
- **I6 — the edges are untested.** The deterministic core is well covered, but the places a human, a
  shell, an HTTP client, or an LLM provider touch the system are not: `cli.py` (zero tests),
  `models/registry.py` (zero tests — the single routing point for every LLM call),
  `brief_editor.py`'s HTTP layer, and the entire MCP server (`packages/xlights-mcp`, ~240 lines, 15
  tools). There is no schema-drift guard: a pydantic field rename or a new required field breaks every
  cached brief on disk, surfacing mid-run (or worse, silently swallowed by the "stale cache → recompute"
  branch at `run.py:395`, quietly discarding an expensive panel run).

## What Changes

**I3 — decompose `_refine_loop`; finish constants consolidation (behavior-preserving):**
- Extract the loop and its guards into a new `pipeline/refine_loop.py`; `run.py` keeps `run_pipeline`
  as the stage skeleton and re-exports the old names so every existing import keeps working.
- Each of the nine guards in the §2.1 inventory becomes a named, individually-testable function or
  small class (`should_skip_refine`, `refine_skip_objective`, `plateau_signature`,
  `design_implicated`, `BestTracker`, `EscalationLedger`, `ReportBuilder`, `IterationRecorder`,
  `apply_revisions`, `refine_loop`).
- Move refine thresholds (`REGRESS_MARGIN`=1, `STALL_LIMIT`=2, `REFINE_SKIP_OBJECTIVE`=88, plus
  `PHRASE_BARS`=8 / `CELL_BARS`=2 / `MOTION_SHARE_MIN`=0.30) into `pipeline/tuning.py` under a new
  "refine loop control" section, keeping each provenance comment; re-export from `run.py`.
- Consolidate the four parallel per-effect tables (`SPEED_KEYS`, `DIRECTION_KNOBS`, `ENERGY_BAND`,
  `DURATION_HIT/PHRASE/CELLABLE`, `MOTION_EFFECTS`, and the private `_BED_EFFECTS`/`_NATIVE_BOUNCE`/
  `_CHASE_FAMILY` sets) into one data-driven `pipeline/effect_meta.py` table with derived views;
  the cross-module imports at `weave.py:227` and `beats.py:583` are removed. All historical import
  paths still resolve via re-export aliases.

**I4 — promote mypy to a hard CI gate; ship `py.typed`:**
- Burn the measured backlog (41 errors / 15 files / 87 source files, mypy 2.1.0, CI-equivalent env
  as of 2026-07-05) to **zero** in one change, then flip CI to hard-fail in the same PR.
- **BREAKING (CI):** remove `continue-on-error: true` from the `Type check (mypy)` step in
  `.github/workflows/ci.yml`; a red mypy now fails the PR. Rewrite the stale "advisory / ~30-finding
  backlog" comments in `ci.yml` (lines 44–46) and root `pyproject.toml` (lines 31–34).
- Harden `[tool.mypy]`: add `warn_unused_ignores`, `warn_redundant_casts`, `check_untyped_defs`
  (keep `ignore_missing_imports = true`; deliberately NOT `strict`/`disallow_untyped_defs`). Add
  `types-PyYAML` to the dev group.
- Ship a `py.typed` marker in all three packages
  (`xlights_core`, `xlights_orchestrator`, `xlights_mcp`); verify each ships in its built wheel.
- Optional: advisory coverage reporting in CI (`pytest-cov`, job-summary + `coverage.xml` artifact,
  no threshold).

**I6 — close the edge test gaps:**
- `tests/test_cli.py`: argparse wiring for the 3 subcommands (`run`, `regen`, `edit-brief`) and 14
  flags, the `--auto`/`--refine` checkpoint matrix, guard exits, exception→`SystemExit` mapping.
- `tests/test_registry.py`: `active_provider`/`model_string`/`model_snapshot`/`_settings`/`build_agent`,
  the `XLO_PROVIDER` override, and the no-sampling-params (Opus-400) invariant; the `_cfg` `lru_cache`
  hazard handled by a dedicated fixture.
- `tests/test_brief_editor_http.py`: GET/POST/404/400 through a real loopback `ThreadingHTTPServer`;
  invalid saves leave the file untouched.
- `tests/test_mcp_server.py`: all 15 tools' happy-path or gate, `_call`'s typed-error translation,
  `xl_add_effect_raw` gates — the whole `xlights-mcp` package goes from 0 tests to covered.
- `tests/test_schema_drift.py` + `tests/fixtures/agent_payloads/`: one frozen known-good JSON payload
  per agent `output_type` and per persisted cache artifact (≥12 payloads), validated in CI, plus a
  required-fields manifest so an additive breaking change fails a test, not a run.
- Optional: the same advisory CI coverage step as I4 (shared).

## Capabilities

### New Capabilities
- `type-safety`: mypy passes as a HARD CI gate against the CI dependency set (0 errors); every
  package ships a PEP 561 `py.typed` marker present in its built wheel.
- `test-coverage`: the named untested edges (`cli.py`, `models/registry.py`, `brief_editor.py` HTTP
  surface, the MCP server) are covered hermetically, and a schema-drift guard freezes agent
  `output_type`s and persisted cache artifacts.
- `code-structure`: the refine loop's guards live as named, individually-testable units and the
  scattered per-effect metadata / refine thresholds are consolidated into single sources, with all
  historical import paths preserved.

### Modified Capabilities
- `show-refinement`: the bounded-and-provably-terminates requirement is restated so each termination
  guard is an independently-testable named unit (behavior unchanged; decomposition only).

## Impact

- **I3 code:** `pipeline/run.py` (loses the loop body, keeps a thin wrapper + re-exports), new
  `pipeline/refine_loop.py`, new `pipeline/effect_meta.py`, `pipeline/tuning.py` (new refine-control
  section), `pipeline/beats.py`, `pipeline/weave.py`, `qa/rules.py` (import from `effect_meta`);
  tests `test_refine.py`, `test_golden_pipeline.py`, `test_effect_speed.py`, `test_visual.py`,
  `test_design_escalation.py`, `test_revision_log.py`, new `tests/test_refine_guards.py`. Risk: a
  behavior-preserving refactor guarded by the golden snapshot (must stay byte-identical, no
  `XLO_REGEN_GOLDEN`) and the full hermetic loop suite.
- **I4 code:** `.github/workflows/ci.yml`, root `pyproject.toml` (`[tool.mypy]`, dev group), three
  `src/<pkg>/py.typed` markers, ~15 source files burned down (`pipeline/generate.py`, `run.py`,
  `regen.py`, `cli.py`, `agents/panel.py`, `models/registry.py`, `qa/__init__.py`, `qa/rules.py`,
  `pipeline/beats.py`, `pipeline/visual.py`, `xlights_core/knowledge/layout_semantics.py`,
  `xlights_core/audio/lyrics_align.py`, `xlights_core/preview/layout.py`, `render.py`,
  `xlights_core/knowledge/xsq_extractor.py`), new `require()` helper in `pipeline/state.py`. Zero
  behavioral changes; only `types-PyYAML` (+ optional `pytest-cov`) added to the dev group. **CI
  behavior is BREAKING:** PRs with type errors now fail.
- **I6 code:** four new test files + `tests/fixtures/agent_payloads/*.json` + `required_fields.json`,
  possibly a 3-line `build_parser()` / plain-function MCP registration refactor if decorators resist
  direct invocation, `.github/workflows/ci.yml` (optional coverage step). No production code behavior
  change.
- **Deps:** `types-PyYAML` (dev), optional `pytest-cov` (dev). No new runtime dependencies.
