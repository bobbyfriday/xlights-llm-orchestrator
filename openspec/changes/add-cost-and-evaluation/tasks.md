## 1. I1 — token & cost telemetry

- [x] 1.1 Create `packages/xlights-orchestrator/src/xlights_orchestrator/telemetry.py` with
  `RoleUsage` (`requests`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`),
  `UsageLog` (`record`/`drain_delta`/`snapshot`; totals map + delta window), the `_current`
  `ContextVar`, and module functions `start_run()`, `current()`, `record(role, result)`. `record()`
  maps `RunUsage` fields → `RoleUsage` (audio fields ignored), wrapped in a best-effort
  `except Exception` → `log.debug` (telemetry never breaks a run).
- [x] 1.2 Instrument the seven `.run()` sites — split each `(await agent.run(...)).output` into
  result-then-`telemetry.record(role, res)`-then-`.output`: `agents/panel.py:135` (`"analyst"`),
  `agents/panel.py:158` (`"synthesizer"`), `pipeline/run.py:415` (`"director"`),
  `pipeline/generate.py:158` (`"generator"` — covers first pass, refine regen, `xlo regen`),
  `pipeline/run.py:163` (`"director"` redesigner), `pipeline/run.py:229` (`"judge"`),
  `pipeline/visual.py:94` (`"visual_critic"`).
- [x] 1.3 Install the collector: `telemetry.start_run()` as the first statement of `run_pipeline()`
  (`pipeline/run.py`, before step 1) and `regen_section()` (`pipeline/regen.py`) so manual regens are
  measured.
- [x] 1.4 Extend `RevisionLogRecord` with `usage: dict[str, RoleUsage] = {}` (per-role tokens since the
  previous record), `usage_total: dict[str, RoleUsage] = {}` (finalize only), `cost_usd: float | None =
  None` (finalize only). Extend `_render_md()` with the finalize-only tokens/cost tail line (iteration
  records stay uncluttered).
- [x] 1.5 Wire the deltas in `_refine_loop`: fetch the active `UsageLog` via `telemetry.current()`,
  thread into `_record()`; add `usage=usage_log.drain_delta()` to every record and
  `usage_total=snapshot()`/`cost_usd=estimate_cost(...)` to both finalize sites (skip-high-objective
  `run.py:214` and end-of-loop `run.py:305`).
- [x] 1.6 Add the `pricing:` block to `models/config.yaml` (Claude rows real: opus-4-8 `{input:5.00,
  output:25.00, cache_read:0.50, cache_write:6.25}`, sonnet-4-6 `{input:3.00, output:15.00,
  cache_read:0.30, cache_write:3.75}`; Gemini rows commented TODO). Add `price_for(model_id)` and
  `estimate_cost(models, usage) -> float | None` (None if any role with nonzero usage lacks a price
  row) next to `_cfg()` in `models/registry.py`.
- [x] 1.7 Summary + artifact at the end of `run_pipeline()` (after step 6, before `return st`,
  unconditionally): `log.info("run usage: %s tokens in / %s out across %d requests — est. $%.2f", …)`
  ("$unknown" when cost is None) and a best-effort `usage.json` under `cache_root()/<song_key>/`
  (list-of-runs keyed by `run_id`: `{run_id, ts, provider, models, usage_total, cost_usd}`).
- [x] 1.8 Document `usage.json`, the JSONL fields, and the None-vs-zero cost convention in
  `docs/usage.md`.
- [x] 1.9 `tests/test_telemetry.py` (new): `UsageLog` accumulation (two `record()`s sum; `drain_delta()`
  empties the window not totals); duck-typed fake result with `.usage()`; a fake *without* `.usage()`
  is a no-op (keeps every existing fake-agent test green); ContextVar isolation (no active log ⇒ no-op;
  concurrent `asyncio.gather` tasks record into the same run's log).
- [x] 1.10 Extend `tests/test_revision_log.py`: JSONL round-trip of a record with
  `usage`/`usage_total`/`cost_usd`; a **pre-I1 line (string literal) still validates** yielding
  `usage == {}`, `cost_usd is None`; markdown finalize line renders tokens+cost, iteration records
  don't.
- [x] 1.11 Extend `tests/test_orchestrator.py`/`test_refine.py`: a hermetic pipeline with fakes whose
  `.usage()` returns fixed numbers asserts the finalize `usage_total` equals the sum and per-iteration
  deltas partition it. Cost-math units: `estimate_cost()` with real Claude rows (142k in / 31k out on
  sonnet-4-6 ⇒ $0.891); unpriced model ⇒ None; zero usage ⇒ 0.0; cache tokens priced at cache rates.
- [x] 1.12 Confirm `test_golden_pipeline.py` stays byte-identical (verified: same sha; TestModel usage
  changes NO generation output) and `uv run ruff check` is green. Opt-in `-m live` smoke added
  (`test_live_analyst_records_usage`); requires a real key so it is not run here.

## 2. I8 — tiered visual analysis (fseq metrics + tiered critique)

- [ ] 2.1 Create `packages/xlights-core/src/xlights_core/preview/metrics.py` (pure numpy, **no
  orchestrator/client imports** — write the no-client contract into the docstring): `group_channel_index`
  (join `parse_models()` start_channel/n_pixels with `<modelGroups>` membership; channel-bound per
  `render.py:48`; unknown/empty groups omitted) and `FseqSeries` (per-group B/L/M series in one
  vectorized pass, `lit_threshold=30`; `section_slice(start_ms, end_ms)`). No behavior change anywhere
  yet.
- [ ] 2.2 Unit-test `metrics.py` against synthetic fixtures extending `tests/test_preview.py`'s
  `_write_fseq`/`_minimal_layout`: 2 groups × 4 nodes × 100 frames @ 50ms — group A blinks white on a
  500ms beat grid, B holds dim red, C dark; assert motion A ≫ B ≈ 0; sync A ≈ max, B ≈ baseline;
  coverage flags C only when its section intensity ≥ 0.5; lit-threshold agrees with `make_lit_sampler`
  (>30). Group-index fixture: channels bounded, overlap allowed, unknown group omitted, unresolvable
  StartChannel skipped like `parse_models`.
- [ ] 2.3 Create `packages/xlights-orchestrator/src/xlights_orchestrator/qa/fseq_metrics.py::evaluate(
  plan, analysis, series, *, repetition_map) -> (subscores, findings)` emitting the five families
  (`fseq:coverage`, `fseq:motion`, `fseq:sync`, `fseq:color`, `fseq:rhyme`/`fseq:range`) as subscores +
  `Finding(metric="fseq:*", objective=False)`; unreadable inputs → `({}, [])` (never gate blind). Add
  the `XLO_FSEQ_METRICS=0` kill switch.
- [ ] 2.4 Thread `fseq_series` through `qa/__init__.py::evaluate(..., sampler=None, fseq_series=None)`
  and the refine loop's `_report` closure (`run.py:172-184`, construct/refresh the series after the
  save-flush, mtime invalidation like `make_lit_sampler`); retire the 3-point sampler path when a
  series is present (show coverage equal-or-better on a real run first).
- [ ] 2.5 Test the metric families: color (pure red vs `["Red","Green"]` ⇒ adherence ~0.5 +
  missing-green finding; three near-identical warm hues vs a 3-color palette ⇒ distinctness failure);
  rhyme/range (duplicate a section ⇒ similarity ≈ 1.0 for shared labels; invert brightness ⇒
  dynamic-range > 0); neutrality (missing fseq / zstd error / empty groups ⇒ `({}, [])` and an
  unchanged objective score).
- [ ] 2.6 Calibration pass: run 2–3 refine-enabled songs; compare fseq findings against the same
  iterations' LLM findings and review bundles in the revision log; set thresholds; document them in the
  module like `qa/coverage.py`.
- [ ] 2.7 Tier 1: add `PreviewRenderer.render_contact_sheet(section, n=8)` (6–9 beat-aligned frames
  tiled ~512px + optional per-pixel-std heatmap tile, reusing `_project`/`_frame_img`); add a lite
  prompt (no `with_guides`) + `render_sheet_input(...)` to `agents/visual_critic.py`; add the
  `visual_critic_lite` worker-tier role to `models/config.yaml`; section-hash tracking (sha256 of
  sorted `model_dump_json`s — the stage-cache idiom) `{section_index: hash}`; `make_tiered_critique`
  factory in `pipeline/visual.py`; swap the default in `run_pipeline` behind the `visual_critique=None`
  seam so injected fakes keep working.
- [ ] 2.8 Test the contact sheet (deterministic frame selection from a fixed beat list; PNG dims + tile
  count; heatmap tile non-uniform iff frames differ) and Tier routing without LLMs (fake lite/pro
  critics counting calls + a scripted Tier 0): iteration 2 after a single-section regen critiques
  exactly one section; disagreement triggers exactly one Tier 2 call; unchanged+unflagged sections
  trigger none; `XLO_FSEQ_METRICS=0` yields today's behavior.
- [ ] 2.9 Tier 2 demotion: the old `make_visual_critique` becomes the escalation, firing only on Tier
  0/1 disagreement, ≥2-revision churn (anti-oscillation ledger), or a once-per-run final gate on
  `RealRender` (media-attached export). Review bundle keeps working — montages + `metrics.json` land in
  the same `visual_review/iterN/` directory.
- [ ] 2.10 Flip the gate: promote `fseq:coverage`/`motion`/`sync` to `objective=True` after the step-2.6
  evidence; `fseq:color`/`rhyme` ship advisory. Announce in `docs/usage.md` env knobs.
- [ ] 2.11 Opt-in `-m live` end-to-end: one run asserts the review bundle contains `metrics.json` +
  montages and the real-render final gate fired (following `test_real_render.py`). Confirm the hermetic
  suite green and the golden fixture untouched.

## 3. F-G — cost & quality dashboard

- [x] 3.1 Reconcile field names against I1's shipped writer (`usage`, `usage_total`/`run_usage`,
  `cost_usd`, `pricing`); F-G's loader must match I1's writer exactly; write the post-I1 fixture from
  I1's actual output.
- [x] 3.2 Create `packages/xlights-orchestrator/src/xlights_orchestrator/reporting.py` — load layer:
  `discover_logs(root)` (`root.glob("*/revision_log.jsonl")`, skips `targetable_groups_*.json` by
  shape), `load_records(path)` (tolerant per-line `model_validate_json`, count-and-skip on
  `ValidationError`/`JSONDecodeError`), `group_runs(records)` (ordered dict keyed by `run_id`, file
  order). Deterministic — no LLM, no xLights, no network.
- [x] 3.3 Metrics layer: `RunSummary` (run_id, song_key, iterations, first/final objective, advisory,
  `trajectory: list[IterationPoint]`, churn `Counter`, `revisions_by_origin`, reverts, `stop_reason`,
  `skipped_by_gate`, `has_cost`, `role_usage`, `cost_usd`, `cost_per_point`, `models`) + `summarize_run`;
  `Report` (runs, `skipped_lines`, `fleet` rollups) + `build_report` (discover→load→group→summarize→
  aggregate). Compute cost per show, cost per objective point gained (`∞ (no gain)` when gain ≤ 0, never
  a division error), skip-gate hit rate, stop-reason mix, per-section churn, finding mix by source,
  per-role/per-tier cost attribution, revert frequency + wasted spend, judge-vs-objective agreement.
  Prefer the record's run-time `cost_usd`; recompute only under `--reprice` or when absent. Pricing via
  a `pricing()` accessor next to `_cfg()` in `models/registry.py` (added by I1; F-G reads it).
- [x] 3.4 Renderers (compute once, render twice — arithmetic lives only in summarize/build):
  `render_text(report)` (fixed-width stdlib tables, the costed-runs caveat line, `—` for missing cost,
  no `rich`/`tabulate`); `render_html(report)` (one self-contained page, the roadmap CSS block, inline
  SVG score sparklines + horizontal churn bars, no JS/external URLs, escape all detail strings,
  light/dark).
- [x] 3.5 CLI: add the `report` subparser to `cli.py` (`--song`, `--cache-dir`, `--html [PATH]`,
  `--json`, `--reprice`); dispatch synchronously (no `asyncio.run`, no `XLightsClient`, **no
  `has_llm_key()` gate**); `--song` reuses `_song_key`; `--json` prints
  `report.model_dump_json(indent=1)`.
- [x] 3.6 Optional pipeline assist (coordinate with I3): additive `stop_reason: str | None = None`
  (`skip-gate|accept|stop|plateau|stall|cap`) and `redesigned_sections: list[int] = []` on
  `RevisionLogRecord`; the dashboard treats absence as `stall-or-cap` for old runs.
- [x] 3.7 `tests/test_reporting.py` (new) with fixtures under `tests/fixtures/revision_logs/`, hermetic
  (matching `test_revision_log.py`): programmatic fixtures via the real `RevisionLog` writer into
  `tmp_path`, plus checked-in raw pre-I1 and post-I1 JSONL that freeze backward compatibility. Load
  layer (malformed line skipped+counted; multiple `run_id`s group in order; `discover_logs` finds
  exactly two logs past a decoy `targetable_groups_x.json`, `XLO_CACHE_DIR` monkeypatched). Metrics
  golden values (trajectory 71→78→76(revert)→90 ⇒ revert count 1, gain 19, cost/point = Σcost/19;
  skip-gate single-finalize counts as a skip, no cost/point; zero-gain ⇒ `∞ (no gain)`; mixed pre/post
  corpus reports `has_cost` and totals only costed runs). Renderers (substring assertions on the caveat
  line and `—`; HTML contains no `http://`/`https://`/`<script`, escapes `<b>&`). CLI end-to-end via
  capsys; `--json` round-trips through `Report.model_validate_json`.
- [x] 3.8 Empty-cache behavior: `xlo report` exits 0 with "no revision logs found under <root>". One
  `README.md` CLI-section paragraph; note in the roadmap scorecard that F6 is closed by F-G.

## 4. F-H — provider A/B eval harness

- [x] 4.1 Registry per-role overrides: add `provider_for(role)` (`XLO_PROVIDER_<ROLE>` > `XLO_PROVIDER`
  > config default) to `models/registry.py`; switch `model_string` (line 33), `_settings` (line 49),
  and `model_snapshot` (line 40) from `active_provider()` to `provider_for(role)` per role;
  `build_agent` needs no signature change; `active_provider()` stays as the fallback base.
- [x] 4.2 Test the registry (mirroring `test_registry_reroute_via_env`, via `monkeypatch.setenv`):
  `XLO_PROVIDER_JUDGE=gemini` + `XLO_PROVIDER=anthropic` ⇒ `model_string("judge").startswith("google:")`
  while `model_string("director").startswith("anthropic:")`; `model_snapshot()` reflects the mix;
  unknown role/provider raises.
- [x] 4.3 Cache namespacing (ship even if nothing else in F-H lands — it fixes `XLO_PROVIDER=gemini xlo
  run`): add `models_fingerprint()` (stable 8-hex sha1 of the sorted per-role `model_snapshot()`) and a
  `models: bool = False` parameter to `cache_path` in `pipeline/cache.py`; flip call sites per the
  design table — namespace `song_description` (`run.py:391`, `regen.py:69`), `creative_brief`
  (`run.py:409`, `regen.py:46,62`, `cli.py:59`), `instructions` (`run.py:426,474`, `regen.py:61,122`),
  and `visual_review/` (`visual.py`, `run.py:468`); leave `song_analysis` (`run.py:380`,
  `regen.py:71`), `targetable_groups_*` (`groups.py:53`), and `revision_log.jsonl/.md`
  (`run.py:458-459`) un-namespaced. No legacy-path read fallback.
- [x] 4.4 Cache-isolation regression test (the most important test in the change): with `XLO_CACHE_DIR`
  at `tmp_path`, run the fake-agent pipeline under provider A, flip to provider B, assert the B run does
  **not** read A's `creative_brief`/`instructions` (distinct `m-*` dirs on disk) while `song_analysis`
  and `targetable_groups_*` paths are shared. Regen compatibility: `regen.load_cached_state` finds the
  namespaced artifacts under the same routing and raises the existing `FileNotFoundError` under a
  different routing.
- [x] 4.5 Create `packages/xlights-orchestrator/src/xlights_orchestrator/pipeline/ab.py`: `ArmSpec`
  (label, provider, `role_overrides`), `parse_arm(spec)` (`base_provider *("+" role "=" provider)`,
  validating roles/providers against `_cfg()` so typos die at parse time), `arm_env(arm)` (context
  manager setting `XLO_PROVIDER` + `XLO_PROVIDER_<ROLE>`, restoring prior values on exit even on
  failure), `run_arm` (calls `run_pipeline` in-process under `arm_env`), `run_ab(song, arms, *, repeat,
  …)`. Analyze-once + inject the same `SongAnalysis`; warm the `targetable_groups` probe once before arm
  1; interleaved repeats (A,B,A,B); per-arm `save_as` names (`{name_prefix}_{arm_i}_{repeat_j}` via
  `safe_name`); write `ab_runs.json` incrementally after each run.
- [x] 4.6 Summary extraction: a pure `summarize_runs(jsonl_lines, run_ids) -> ArmSummary` (first/final
  scores, iterations, reverts, subscores, per-iteration deltas) — implement it as / reuse F-G's
  `summarize_run` in `reporting.py` and import it here rather than duplicating the arithmetic.
- [x] 4.7 CLI: add the `ab` subparser to `cli.py` following the `run` parser's shape (repeatable
  `--arm`, `--repeat`, `--max-iterations`, `--name-prefix`, `--keep-sequences`); hard-wire
  `refine=True`, `checkpoint=_auto_checkpoint`, `interpret_checkpoint=None`, `design_checkpoint=None`,
  `log_revisions=True`; strict multi-key preflight (every provider named by any arm has its key, refuse
  otherwise); print the terminal summary (per-arm median + min–max range, per-metric deltas,
  "indistinguishable when ranges overlap"). Arms run sequentially (do not attempt concurrency).
- [x] 4.8 Test the harness (hermetic, over the golden-test fakes — `TestModel` agents, `_FakeClient`,
  fake emitter, injected analysis): arm-spec parsing round-trips + validation failures + env
  set/restore including on exception inside `arm_env`; `run_ab` 2 arms × 2 repeats ⇒ 4 runs, interleaved
  order, distinct `run_id`s, one shared `revision_log.jsonl`, correct `ab_runs.json`, truthful per-arm
  `models`; `summarize_runs` medians/ranges/revert-counts and the "indistinguishable" rule; a mixed arm
  (`gemini+judge=anthropic`) is labeled truthfully everywhere.
- [~] 4.9 Post-I1 columns: `summarize_runs` surfaces cost via the reused `summarize_run` once records
  carry usage (no harness change). `config.yaml` "live A/B'd" comment replaced with a pointer to
  `xlo ab`. DEFERRED (needs real keys + xLights): the estimated-spend warning and the `-m live`
  two-arm smoke — not runnable hermetically here.

## 5. Land

- [ ] 5.1 Each roadmap item lands via its own pull request on a branch (never commit to `main`
  directly); order per the roadmap: I1 → I8 Tiers 0–1 → F-G → F-H (cache namespacing first, harness
  second). Run `openspec validate add-cost-and-evaluation --strict` and the full hermetic suite before
  each PR.
- [ ] 5.2 Verify the >10× visual-analysis cost drop on a like-for-like refine run using I1 telemetry
  (else counted calls × estimated sizes in the revision log), and attach the before/after as the I8
  archive evidence.
