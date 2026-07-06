## Context

This change bundles three independent code-health roadmap items (I3, I4, I6). They are grouped
because they share a posture — behavior-preserving hardening that makes later feature work safe — and
because I4 (mypy) and I6 (coverage) both touch the same CI file and both propose the same optional
coverage step, and I3's decomposition benefits from the durable typing I4 lands.

### I3 — refine-loop decomposition and constants consolidation

`_refine_loop` lives at `pipeline/run.py:135–305` (~170 lines). Its nine guards, verbatim from the
current-state inventory (run.py line numbers):

1. **Skip-high-objective gate** (lines 211–216): if `skip_objective is not None and best_obj >=
   skip_objective`, record a `finalize` record with `human_decision="skip-high-objective"` and return
   before any Judge/critic spend. Threshold `REFINE_SKIP_OBJECTIVE = 88` (line 62), env-overridable
   via `_refine_skip_objective()` (lines 65–70, reads `XLO_REFINE_SKIP_OBJECTIVE`, 101 = never skip).
   Wired at line 470.
2. **Hard iteration cap** (line 220): `for i in range(max_iterations)` — "HARD cap — cannot be
   exceeded"; deliberately never delegated to the Judge. State: `iters`.
3. **Plateau detector** (lines 236–243): signature = `(objective, advisory, frozenset((r.section_index,
   issue[:64]) for r in verdict.revisions))`; equal to the previous iteration → log "plateau", record
   `human_decision="plateau"`, break *before* applying revisions. State: `prev_sig`.
4. **Objective-regression revert** (lines 275–284): `reverted = obj < best_obj - REGRESS_MARGIN`
   (margin=1, line 58). On revert restore `best`/`best_applied`, *re-emit the reverted best
   immediately* (close + emitter) so the open xLights sequence, the sampler, and the next iteration's
   critic all see the kept render; `stall += 1`. State: `best, best_applied, best_obj, open_is_best`.
5. **Stall stop** (lines 284, 289, 297–298): consecutive reverts increment `stall`; a genuine gain
   (`obj > best_obj + REGRESS_MARGIN`) resets it; a held objective (creative change, no score move)
   neither gains nor stalls. `stall >= STALL_LIMIT` (2, line 59) terminates. State: `stall`.
6. **Anti-oscillation ledger** (line 191 `ledger = []`, line 267 `ledger.append(rev)`): every applied
   revision is remembered; consumed twice — rendered into the Judge prompt (`judge_mod.render_input(
   report, plan, brief, ledger)`, line 230) and `prior = {r.section_index for r in ledger}` (line 247)
   marks repeat-offender sections eligible for design escalation. State: `ledger`.
7. **Design escalation** (lines 153–170 + 250–265): a section is escalated to the Director's
   `section_redesigner()` once per run (`redesigned: set[int]`) when it is a repeat offender OR its
   brief is implicated (`_design_implicated`: a `metric == "rules"` finding whose detail names one of
   the section's planned `effect_types`). The redesigned SectionPlan has its structure pinned
   (`start_ms/end_ms` copied back, `target_groups` defaulted). Best-effort: failures log a warning and
   fall through to plain regen. State: `redesigned, _rd_agent`.
8. **Visual backstop flooring** (line 245): `floored = floor_visual_revisions(report.findings,
   judge_revs)` (`refine.py:57–74`) — a critic-confirmed `visual:*` severity=error finding for a
   section the Judge didn't act on becomes a revision anyway; logged with `origin="backstop"` (lines
   290–294).
9. **Best-restore at exit** (lines 300–305): unconditionally restore `best`; if the open sequence
   isn't the best (`open_is_best` false), re-emit; write the final `finalize` record. State:
   `open_is_best`.

The nested closures (all local to `_refine_loop`): `_regen` (148–151), `_redesign` (156–163),
`_design_implicated` (165–170), `_report` (172–184), `_obj` (186–187), `_bundle` (195–199), `_record`
(201–209). `_report` is the subtlest: it saves the sequence and refreshes the real render *before*
sampling so coverage QA sees the render being scored (172–179), and it keeps a legacy 5-arg QA
signature when a fake `qa` is injected (180–184) — the shape every fake in `test_refine.py` relies on
(`def qa(instructions, analysis, plan, applied, groups)`).

The scattered constants (`pipeline/tuning.py`'s docstring deliberately scopes itself to
structural/mechanical dials staying beside their code, which was right for brightness but left
per-effect metadata fragmented across four modules):

```
beats.py:90    SPEED_KEYS: dict[str, tuple[str, float, float, str]]   # 17 effects: (key, lo, hi, fmt)
weave.py:55    DIRECTION_KNOBS: dict[str, dict[str, tuple[str, str]]] # 12 effects: direction -> (key, value)
qa/rules.py:15 ENERGY_BAND: dict[str, tuple[int, int]]               # 33 effects: catalog §2 bands
qa/rules.py:29 DURATION_HIT / DURATION_PHRASE / DURATION_CELLABLE    # PHRASE_BARS=8, CELL_BARS=2
qa/rules.py:40 MOTION_EFFECTS = DURATION_CELLABLE | {"Fire", "Galaxy"}
# cross-module imports:
weave.py:227   from ..qa.rules import DURATION_CELLABLE
beats.py:583   from ..qa.rules import (CELL_BARS, DURATION_CELLABLE, DURATION_HIT, DURATION_PHRASE, ...)
```
Plus private sets in `weave.py`: `_BED_EFFECTS = {"Color Wash", "Plasma", "On"}` (49),
`_NATIVE_BOUNCE = {"SingleStrand", "Garlands"}` (95), `_CHASE_FAMILY` (99). Loop-control thresholds at
`run.py:58–62`: `REGRESS_MARGIN = 1`, `STALL_LIMIT = 2`, `REFINE_SKIP_OBJECTIVE = 88`.

The safety net: `tests/test_golden_pipeline.py` (exact snapshot of the deterministic generate stage,
103 instructions in `fixtures/golden_instructions.json`, explicitly built as a safety net for
behavior-preserving refactors); `tests/test_refine.py` (15 hermetic tests covering the loop
end-to-end, importing `_refine_loop`, `REFINE_SKIP_OBJECTIVE`, `_refine_skip_objective` from
`xlights_orchestrator.pipeline.run`); `test_visual.py`, `test_design_escalation.py`,
`test_revision_log.py` (drive `_refine_loop` directly); `test_effect_speed.py:5` imports `SPEED_KEYS`
from `pipeline.beats`.

### I4 — mypy gate and py.typed

`.github/workflows/ci.yml:44–49` runs `uv run --no-sync mypy` with `continue-on-error: true` and a
comment saying the backlog "is being triaged before this becomes a hard gate." Root
`pyproject.toml:35–38` is the entire config (`python_version = "3.11"`, `ignore_missing_imports =
true`, `files = ["packages"]` — so tests are *not* checked, a deliberate scope choice). Dev group pins
`mypy>=1.11`; the lock resolves to **mypy 2.1.0**. CI installs `uv sync --extra preview` plus
`librosa soundfile`, runs steps with `--no-sync`.

Measured baseline (2026-07-05, CI-equivalent env): **41 errors in 15 files (checked 87 source
files).** By code: `union-attr` 20, `assignment` 5, `arg-type` 5, `var-annotated` 4, `operator` 2,
`typeddict-item`/`return-value`/`misc`/`index`/`attr-defined` 1 each. The roadmap's "~30" is stale;
the count is env-sensitive (a dependency-light venv reports 40 slightly different ones), so the gate
is only meaningful measured against the CI dependency set. Per-file fix strategy in tasks.md §5.

All three packages build with hatchling and enumerate their package dir; hatchling includes *all*
files under a listed package dir in the wheel (already relied on for `models/config.yaml` and
`agents/prompts/`), so shipping the marker is literally `touch src/<pkg>/py.typed` — no build-config
change.

### I6 — edge test coverage

Test-suite conventions new tests must follow: hermetic by default (`addopts = "-m 'not live'"`;
`live` is the only marker); fake agents via PydanticAI `TestModel` (`test_golden_pipeline.py:122–126`)
or `SimpleNamespace(output=…)`; fake xLights via `httpx.MockTransport` + recorded JSON fixtures
(`test_client.py:32–40`) or duck-typed clients; `XLO_CACHE_DIR` monkeypatched to `tmp_path`; guides
load best-effort. The agent `output_type`s and their persistence: `ShowPlan` (cache `creative_brief`),
`SectionPlan`, `SectionEffects`⊃`EffectInstruction` (cache `instructions`), `MusicBrief` (cache
`song_description`), the four panel analyst outs (`StructureOut`/`RhythmOut`/`HarmonyOut`/`LyricOut`,
transient), `JudgeVerdict`, `VisualFindings` (review-bundle `findings.json`), plus non-agent persisted
`SongAnalysis` (cache `song_analysis`) and `RevisionLogRecord` (`revision_log.jsonl`).

## Goals / Non-Goals

**Goals:**
- I3: every §2.1 guard is a named function/class with at least one direct unit test that constructs
  no Judge/emitter/State-with-plan harness; `run.py` drops well below its current 486 lines; four
  parallel per-effect tables collapse into one; refine thresholds live in `tuning.py`; all historical
  import paths still resolve; the golden fixture is byte-identical (no `XLO_REGEN_GOLDEN`).
- I4: `uv run --no-sync mypy` exits 0 in the CI env (0 errors, 87+ files); the mypy CI step hard-fails;
  `py.typed` ships in all three wheels; `warn_unused_ignores`/`warn_redundant_casts` on; zero runtime
  behavior change proven by the unchanged golden snapshot; only `types-PyYAML` (+ optional
  `pytest-cov`) added.
- I6: the four named edges are covered hermetically; ≥12 frozen schema-drift payloads validate in CI;
  an additive required-field change fails a test with the documented failure-protocol message; CI
  optionally publishes a coverage summary + `coverage.xml` artifact with no threshold.

**Non-Goals:**
- No refine-loop *behavior* change (I3 is code-motion only); no new objective metrics.
- No mypy `strict`/`disallow_untyped_defs`/`disallow_any_*` (freeze today's honesty level; strictness
  increments are separate per-package steps); tests stay out of the mypy scope (`files = ["packages"]`).
- No `--cov-fail-under` threshold initially (visibility only); no external coverage upload service.
- No structured `Finding.effect_type` field (defer; out of I3's behavior-preserving scope).

## Decisions

**I3.1 — Extract into `pipeline/refine_loop.py`; `run.py` re-exports.** `run.py` keeps `run_pipeline`
as the stage skeleton and `_refine_loop = refine_loop`; `regenerate_section` (shared with `xlo regen`
via `pipeline/regen.py`) and the checkpoint functions (`_auto_checkpoint`, imported by `cli.py:13`)
stay reachable. The DI seams the hermetic tests use are contracts, not incidental: `judge`, `qa`,
`regenerate`, `redesign`, `checkpoint`, `visual_critique`, `revlog`, `sampler`, `clock` remain keyword
parameters of `refine_loop`. The lazy-agent rules remain: the default generator agent is only built
when no `regenerate` is injected (constructing a real Agent needs an API key hermetic tests lack), and
`section_redesigner()` stays lazy inside the redesign path. *Alternative weighed:* a `RefineContext`
dataclass to shrink the 20-keyword signature — deferred (open question), because it forces edits in
`run_pipeline` and every test and is only worth it if Phase 2 adds parameters anyway.

**I3.2 — Guards become named units.** Pure/stateless: `should_skip_refine(first_pass_objective,
skip_objective)`, `refine_skip_objective()`, `plateau_signature(report, verdict)`,
`design_implicated(plan, section_index, findings)`. Stateful, one class each: `BestTracker` (owns
best/best_applied/best_obj/open_is_best + stall — guards #4/#5/#9, with `assess(obj) -> Outcome(reverted,
gained)`, `keep`, `revert`, `stalled`) and `EscalationLedger` (owns `ledger` + `redesigned` — guards
#6/#7). Side-effecting collaborators stay injectable: `ReportBuilder` (wraps `_report`/`_obj`,
preserves the legacy 5-arg qa branch), `IterationRecorder` (wraps `_record`/`_bundle`, pure
observability, never raises into the loop), `apply_revisions` (guard #7 + splice). `refine_loop` is
then ~60 lines of orchestration: *skip gate → [report → visual findings → judge → decide → plateau
check → floor visual revisions → apply revisions (escalating where warranted) → clamp/finalize/emit →
assess & keep-or-revert → record → stall check] → restore best → finalize record.* *Alternative
weighed:* leave the loop monolithic and only extract constants — rejected because Phase 2 threads new
guards through the same body and every guard is currently testable only end-to-end.

**I3.3 — Constants: two destinations honoring `tuning.py`'s scope line.** (a) `pipeline/tuning.py`
gains a `# -- refine loop control` section for the loop thresholds (they are tunable behavior dials,
exactly what tuning.py is for), each keeping its provenance comment (e.g. the 42-run revision-log
analysis behind `REFINE_SKIP_OBJECTIVE`). (b) A new per-effect metadata table `pipeline/effect_meta.py`
(orchestrator-side, since every consumer is orchestrator-side), one `@dataclass(frozen=True)
EffectMeta` row per effect type (`speed`, `directions`, `energy_band`, `duration_class`, `bed_capable`,
`native_bounce`, `chase_family`), with derived views (`SPEED_KEYS`, `DIRECTION_KNOBS`, `ENERGY_BAND`,
`DURATION_HIT/PHRASE/CELLABLE`, `MOTION_EFFECTS`) so every existing name keeps working; each row cites
its corpus provenance (`2026-06-12-add-settings-hygiene`, `2026-06-12-add-directional-sweeps`). The
detailed destination map (which constant, current location, destination, notes) is in tasks.md §1.
Constants that stay put: `STROBE_CAP_MS`/`SHIMMER_BARS` (quote catalog rule #7 verbatim, belong beside
it) and `CARRIER_ROTATION` (improve-musicality Phase 1 re-keys it; moving it now churns that change).
*Alternative weighed:* put the metadata table in `xlights_core.knowledge` (which already owns
corpus-derived effect knowledge) — deferred; starting orchestrator-side is the smaller diff, revisit
if F-E layout onboarding needs it core-side (open question).

**I4.1 — Zero-findings, not a ratchet.** With only 41 mechanical findings, a baseline/ratchet system
(mypy-baseline files, per-module overrides deleted over time) is overkill and leaves ignore-debt. Burn
the list to zero in one change, then flip CI to hard-fail in the *same* PR; the gate is "mypy exits 0",
full stop. Inline `# type: ignore[code]` is permitted only with a same-line reason, and
`warn_unused_ignores` makes stale ignores errors, so ignore-count cannot silently grow. *Alternative
weighed:* advisory-on-PRs / hard-on-main — rejected; it splits the signal and lets PRs merge red, and
the finding count (0) doesn't justify it.

**I4.2 — Config hardening is modest and deliberate.** Add `warn_unused_ignores`, `warn_redundant_casts`,
`check_untyped_defs`; keep `ignore_missing_imports = true` (librosa/vamp/demucs/lyricsgenius have no
stubs); do NOT enable `strict`/`disallow_untyped_defs`/`disallow_any_*` — the gate's value is stopping
*new* drift, which zero-findings already does; strictification is a separate, noisier, per-package
diff. Add `types-PyYAML` to the dev group so yaml stubs are present regardless of which transitive dep
currently drags them in (today's clean `registry.py:15` is accidental). The `uv.lock` pins mypy 2.1.0;
bumps arrive as explicit lock-update PRs — do NOT pin beyond `>=1.11` in `pyproject.toml`.

**I4.3 — Fix-by-category, zero behavioral change.** Category A (Optional-State, ~18 findings): add a
3-line `require(value: T | None, name: str) -> T` helper to `pipeline/state.py` (raises `RuntimeError`
naming the field), narrow once at function entry (`plan = require(st.show_plan, "show_plan")`), use the
local. Provably safe because a `None` there would already `AttributeError` one line later; `require()`
only improves the message. Category B (protocol the seam, ~4 findings): `panel.py` gets `class
RunsAgent(Protocol): async def run(self, prompt: str) -> Any` (Protocol preferred over
`pydantic_ai.Agent[Any,Any]` because test fakes are `SimpleNamespace`s) + `isinstance(r, BaseException)`
gather narrowing; `registry.py:61` builds the TypedDict literally (`settings: AnthropicModelSettings =
{}` then conditional key assignments) instead of `**kw`; `revision_log.py` gets a `RevisionSink`
Protocol and `run.py:459` an annotation. Mechanical remainder (~19): annotations, `or 0` / `or {}`
guards, `assert proc.stdin is not None`, the `layout.py` scalar-vs-list variable rename, the
`qa/__init__.py` `dict[str, float]` fix.

**I4.4 — `py.typed` in all three packages.** Empty markers at
`packages/xlights-core/src/xlights_core/py.typed`, `.../xlights_orchestrator/py.typed`,
`.../xlights_mcp/py.typed`. Effects: PEP 561 consumers see the packages as typed; if the workspace ever
switches from source-tree checking to built-wheel checking, cross-package types keep resolving; the
marker is an implicit contract the hard gate now guarantees. Verify with `uv build --package
xlights-core && unzip -l dist/xlights_core-*.whl | grep py.typed` per package.

**I6.1 — Assert at the wiring boundary, fake the entry points.** `test_cli.py`: `main(argv)` is
already injectable; monkeypatch `cli.run_pipeline` and `XLightsClient` (async-context stub) and assert
the *exact kwargs* the CLI passes into the pipeline — the wiring is the product. Prefer the
`run_pipeline` kwargs boundary (public contract) over patching private `cli._run`/`cli._regen`, to keep
private patches to the two dispatch shims. If `main()` resists patching, a 3-line `build_parser()`
extraction is acceptable; do not restructure command dispatch. `test_registry.py`: nothing external —
test the real `config.yaml` for invariants and point `_CONFIG` at a fixture YAML for behavior; wrap the
`@functools.lru_cache` on `_cfg()` (`registry.py:21`) in an autouse fixture that clears the cache on
entry and exit so ordering can't leak. `test_brief_editor_http.py`:
`ThreadingHTTPServer(("127.0.0.1", 0), _handler(...))` on an ephemeral port in a daemon thread is
hermetic (loopback, port 0, no `webbrowser`); drive with `urllib.request`, teardown `server_close()` in
a finally. `test_mcp_server.py`: fake `Context` via two `SimpleNamespace` layers
(`request_context.lifespan_context["client"]`); call tool coroutines directly, falling back to
`mcp._tool_manager` or explicit `mcp.tool()(fn)` registration if a FastMCP version wraps them
un-callably.

**I6.2 — Frozen, hand-seeded schema-drift payloads.** One checked-in known-good JSON per schema,
validated against the current model; payloads *never auto-regenerate* — updating one is a deliberate
act standing in for "I am knowingly invalidating cached briefs on disk." Seed each fixture from a real
cached artifact (redacted, trimmed to 1–2 sections) so it carries realistic optional-field usage — NOT
from `model_dump()` of a fresh object, which only contains defaults and follows renames automatically.
A second cheaper assertion compares `model.model_json_schema()` required-field sets against a frozen
`required_fields.json` so a *new required field* fails even if the payload happens to include it. An
`XLO_REGEN_PAYLOADS=1` helper script is acceptable (mirroring the golden's `XLO_REGEN_GOLDEN`); an
automatic rewrite is not. Failure protocol (in the module docstring): either revert to a
backward-compatible change (new field with default) or intentionally bump the fixture *and* the cache
key (the run.py:390 precedent) — a bump without a cache-key bump is exactly the bug this guard catches
(the silent `except Exception → recompute` at run.py:394–396, or a hard crash for
`creative_brief`/`instructions` which validate without try/except at run.py:411, 427–429).

**Shared — advisory CI coverage.** Both I4 and I6 propose the same step: add `pytest-cov` to the dev
group, run `uv run --no-sync pytest --cov=packages --cov-report=term-missing:skip-covered
--cov-report=xml`, publish a `$GITHUB_STEP_SUMMARY` line + upload `coverage.xml` as an artifact, no
`--cov-fail-under` and no external upload service (keeps CI hermetic). Land it once, as its own commit
so it can be dropped independently.

## Risks / Trade-offs

**I3:**
- [Subtle behavior change in revert/stall arithmetic during extraction — e.g. `max(best_obj, obj)` on
  the keep path, run.py:288] → Port expressions verbatim into `BestTracker`; boundary unit tests
  (`obj == best - margin` keeps, `obj == best + margin` keeps-without-gain, stall reset only on gain);
  `test_refine.py` exercises every branch end-to-end.
- [Table transcription error in `effect_meta.py` — a knob-key typo silently no-ops at emit time] →
  Frozen-literal equality test (step 1: derived views must equal a frozen copy of today's literals);
  golden snapshot byte-compare; no `XLO_REGEN_GOLDEN` anywhere in the change (if step 1 needs one, the
  transcription has a bug).
- [Breaking hermetic tests' injected-fake signatures — legacy 5-arg `qa`, `regenerate(rev)`,
  `redesign(rev, findings)`] → Keep all keyword seams identical; `ReportBuilder` preserves the
  legacy-signature branch explicitly.
- [Losing the re-emit-on-revert ordering (close → emit → mark `open_is_best`) or the save-before-sample
  ordering in `_report`] → the exact bugs those lines were added to fix; both orderings get their own
  unit tests with a call-order-recording fake client/emitter.
- [Collision with improve-musicality Phase 1 landing in parallel — touches `section_carrier`,
  escalation spending] → the sequencing table places I3 after Phase 1; the effect-metadata step (1–2)
  can land any time.
- [tuning.py scope creep (loop control ≠ show feel)] → explicit new section header + a one-line scope
  amendment in the docstring.

**I4:**
- [A "mechanical" narrow changes behavior — e.g. `require()` raising where code previously limped on
  `None`] → every Category-A site is provably post-population today (a `None` there would already
  `AttributeError` one line later); full suite + golden snapshot per commit.
- [mypy version drift re-opens the gate (2.x minors add checks)] → `uv.lock` pins 2.1.0; bumps arrive
  as explicit lock-update PRs where new findings are fixed in the same diff; do not pin beyond `>=1.11`.
- [Local runs disagree with CI (the 40-vs-41 trap)] → document the canonical invocation
  (`uv sync --extra preview && uv run --no-sync mypy`) in the workflow comment; optional
  checked-file-count assertion (≥87 files) protects against a thinner venv silently checking fewer
  modules.
- [`ignore_missing_imports = true` hides a genuinely mistyped third-party usage] → accepted for the
  audio stack; revisit with scoped per-module `[[tool.mypy.overrides]]` as a later tightening step.
- [Hard gate frustrates rapid prototyping] → the escape hatch is the documented same-line
  `# type: ignore[code]  # reason`; `warn_unused_ignores` garbage-collects them; mypy is incremental.
- [`py.typed` exposes half-true types of `xlights-core` to external consumers] → the gate is the
  mitigation: core is checked clean before the marker ships in the same PR.

**I6:**
- [FastMCP decorator wraps tools un-callably in some version] → pin/inspect `mcp` version; fall back to
  plain functions + explicit `mcp.tool()(fn)` registration (behavior-identical).
- [CLI tests over-fit to internals (patching `cli._run`)] → assert the `run_pipeline` kwargs boundary;
  keep private patches to the two dispatch shims.
- [Drift fixtures drift from reality] → seed from real cache artifacts; add the required-fields
  manifest; refresh fixtures only when a schema change legitimately lands.
- [ThreadingHTTPServer test flakes (port reuse, slow teardown)] → port 0, `server_close()` in a
  finally-teardown fixture, bounded urllib timeouts (2s).
- [Coverage step slows CI or misattributes uv-workspace paths] → `--cov=packages` with coverage paths
  config if needed; keep it advisory; measure runtime before merging.
- [`lru_cache` on `_cfg()` leaks fixture config into later tests] → a dedicated autouse fixture in
  `test_registry.py` clearing the cache on entry and exit.

## Migration Plan

- **CI gate flip is the one BREAKING step** and lands last within the I4 PR, after the backlog is
  zeroed, so no PR is ever blocked by pre-existing findings. Commits are ordered so each is
  independently green under the *advisory* gate before the flip.
- **All import paths preserved** by re-export aliases (`from .effect_meta import SPEED_KEYS  #
  re-export`, `_refine_loop = refine_loop`, thresholds re-exported from `run.py`), so cached-workflow
  scripts and external callers keep working; an import-compat test asserts they still resolve.
- **`py.typed` ships in the same PR that reaches 0 findings**, so no half-typed package is ever
  advertised as typed.
- **Schema-drift fixtures are a one-way ratchet**: bumping one requires a cache-key bump per the
  run.py:390 precedent; the failure-protocol docstring documents this.
- **No golden regeneration** anywhere in I3 or I4 (behavior-preserving). improve-musicality regenerates
  the golden per phase; this change must not.

## Open Questions

1. **tuning.py vs a separate `refine_tuning` module** — the roadmap says "into `pipeline/tuning.py`";
   its docstring currently scopes itself to artistic dials. Recommended: amend the docstring (one file
   to look in) rather than add a sibling module.
2. **Where does `effect_meta.py` live?** All consumers are orchestrator-side today, but
   `xlights_core.knowledge` owns corpus-derived effect knowledge. If F-E layout onboarding ever needs
   effect metadata core-side, core is the better home; starting orchestrator-side is the smaller diff.
3. **Context object now or later?** A `RefineContext` dataclass would clean up the 20-keyword signature
   but forces edits in `run_pipeline` and every test — worth doing only if improve-musicality Phase 2
   adds more parameters anyway.
4. **Should `_design_implicated`'s substring match (`e in f.detail`) become structured?** A `Finding.
   effect_type` field would replace prose matching, but changes `Finding` and is out of
   behavior-preserving scope. Defer; note for improve-musicality.
5. **Archive the pending changes first?** `add-refine-skip-high-objective` is implemented-but-unarchived
   and specifies lines this change moves; archiving it before I3 keeps OpenSpec history clean. (Roadmap
   Horizon 1 also lists archiving `add-song-end-envelope-fade` and `add-targeted-section-regen`.)
6. **I4 State-typing altitude** — `require()` is minimal; whether `State` should grow typed accessors
   (`State.plan → ShowPlan`, raising) or split into per-stage dataclasses intersects I3's extraction —
   decide there, keep I4 minimal.
7. **Type-check tests too?** `files = ["packages"]` excludes `tests/`; checking tests would catch
   fixture drift but adds a large annotation surface of intentional fakes — out of scope for I4,
   reconsider with I6.
8. **`xlights-mcp` strictness** — at ~240 lines and 0 findings, should it pilot `disallow_untyped_defs
   = true` via a per-package override? Cheap, low blast radius.
9. **mypy vs adding pyright** — editors mostly run pyright (differing inference). One gate is enough;
   pyright-advisory as a follow-up look, or noise?
10. **Coverage destination** — job summary only vs an artifact XML for future trend tooling; decide when
    the F-G dashboard is scoped. **Coverage backend** — plain artifact + step summary (proposed) vs
    Codecov PR annotations; start with the former.
11. **Where should MCP tests live?** Workspace-root `tests/` (single pytest run, matches today) vs a
    per-package `packages/xlights-mcp/tests/`. Recommend workspace root.
12. **Drift-guard scope for `SongAnalysis`** — a full fixture is bulky (~100 KB); trim to one
    beat/segment/stem each and rely on the required-fields manifest for the rest?
13. **Should the drift guard pin enum vocabularies** (`Decision.action`, `JudgeVerdict.verdict`
    literals) the revision log/checkpoints string-match on? Cheap to add to the manifest.
14. **`test_orchestrator.py` overlap** — audit before writing `test_cli.py` so CLI tests stop at the
    kwargs boundary and don't duplicate pipeline-behavior assertions.

## Notes

- **I3 acceptance criteria (verbatim from the doc):** `pipeline/refine_loop.py` exists and `run.py`'s
  refine content is ≤ a thin wrapper + re-exports (run.py drops well below its current 486 lines);
  every §2.1 guard is a named function/class with ≥1 direct unit test that constructs no
  Judge/emitter/State-with-plan harness; `REGRESS_MARGIN`/`STALL_LIMIT`/`REFINE_SKIP_OBJECTIVE` live in
  `tuning.py` and `XLO_REFINE_SKIP_OBJECTIVE` still works (test_refine.py:363–372 unchanged);
  `SPEED_KEYS`/`DIRECTION_KNOBS`/`ENERGY_BAND`/`DURATION_*` derive from one table and the cross-module
  imports at weave.py:227 and beats.py:583 are gone; all historical import paths resolve; the full
  suite is green with `fixtures/golden_instructions.json` unchanged; the revision-log output (JSONL +
  md) for an identical run is field-for-field identical.
- **I4 references:** PEP 561 (py.typed distribution of inline types); hatchling package-dir file
  inclusion (already relied on for `models/config.yaml` and `agents/prompts/`); measured baseline
  scratch capture retained during implementation for diffing; roadmap R1 scorecard row ("mypy is
  advisory (`continue-on-error`), no `py.typed`").
- **I6 references:** conventions exemplars `test_client.py` (MockTransport + fixtures),
  `test_golden_pipeline.py` (`_test_agent`, fake client, `XLO_CACHE_DIR`), `test_refine.py` (duck-typed
  fakes), `test_brief_editor.py` (existing unit layer); cache-key-bump precedent run.py:390–391,
  407–408; silent-recompute branch run.py:393–396. I1 (token/cost telemetry) later extends the
  `RevisionLogRecord` schema this guard freezes.
- **Roadmap I3/I4 doc note on OpenSpec:** the I3 doc suggests an OpenSpec change (`refactor-refine-loop`)
  since show-refinement is spec'd but its behavior is unchanged (tasks code-motion only); the I4/I6
  docs say tooling-only items "need no OpenSpec capability delta." This change nonetheless expresses
  intent via the `type-safety`, `test-coverage`, and `code-structure` capabilities (plus a
  behavior-preserving `show-refinement` restatement) because OpenSpec requires ≥1 delta per change.
