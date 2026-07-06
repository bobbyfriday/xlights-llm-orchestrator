## Why

The project runs an active cost-reduction campaign — guide-extract trimming, tiered per-role model
routing (`models/config.yaml` routes analysts/generators to Sonnet-tier and
director/synthesizer/judge/visual-critic to Opus-tier), the refine-loop skip-high-objective gate
(`REFINE_SKIP_OBJECTIVE = 88`, justified by "revision-log analysis (42 runs)"), and I8's tiered
visual critique — **without a single token being counted anywhere in the codebase**. Every cost
claim to date is an estimate. PydanticAI already computes what we need: every `AgentRunResult`
carries a `usage()` returning a `RunUsage` dataclass with request/response token counts (including
prompt-cache splits), and we throw it away at all seven `.run()` call sites (`(await
agent.run(p)).output` discards the wrapper). The revision log already records a per-role `models`
snapshot per iteration — it is one field away from being a per-run cost ledger.

Meanwhile each refine iteration pays the most expensive model in the fleet to look at up to six
stills and six ten-second MP4 clips with two full markdown guides (~51k chars) in its system prompt
— roughly 30–40k multimodal tokens per iteration — for findings that are **advisory only**. Its four
aspects (`coverage`, `color`, `motion`, `energy`) are largely computable from data we already have:
the `.fseq` is the exact per-node RGB of every frame, and the layout gives node→group mapping.

And every model-routing decision in `models/config.yaml` is justified by an informal, undocumented
experiment — the evidence is literally a YAML comment ("live A/B'd: valid structured output, rules
92"). There is no way to re-run it, no record of what was held constant, and no cost dimension. The
stage cache is keyed by `sha1(audio bytes)[:16]` + stage name only — provider/model appear nowhere —
so `XLO_PROVIDER=gemini xlo run` silently reuses Claude's cached `song_description`/`creative_brief`/
`instructions`, making any naive A/B invalid.

This change is the cost/measurement/eval cluster. I1 (token telemetry) unblocks F-G (dashboard) and
F-H (A/B harness); I8 (tiered visual analysis) makes every refine iteration >10× cheaper while
*adding* objective rendered metrics that do not exist today.

## What Changes

**I1 — token & cost telemetry (unblocks F-G and F-H):**
- Add a run-scoped **usage collector** (`telemetry.py`, contextvar-scoped) with a one-line capture
  helper called at each of the seven `.run()` sites: analyst (`panel.py:135`), synthesizer
  (`panel.py:158`), director (`run.py:415`), generator (`generate.py:158` — covers first pass, refine
  regen, and `xlo regen`), redesigner (`run.py:163`, keyed `director`), judge (`run.py:229`), visual
  critic (`visual.py:94`). `telemetry.start_run()` at the top of `run_pipeline()` and `regen_section()`.
- Extend `RevisionLogRecord` (additive, defaulted, backward compatible) with `usage: dict[str,
  RoleUsage]` (per-role tokens since the previous record), `usage_total: dict[str, RoleUsage]`
  (finalize only), and `cost_usd: float | None` (finalize only; `None` when any price unknown).
- Add a `pricing:` block to `models/config.yaml` (USD per 1M tokens, keyed by bare model id: Claude
  rows real — opus-4-8 $5/$25, sonnet-4-6 $3/$15, cache read 0.1× input, cache write 1.25× input;
  Gemini rows commented TODO) and pure `price_for()`/`estimate_cost()` in `models/registry.py`.
- Add a `log.info` per-run cost summary line and a best-effort `usage.json` artifact under
  `cache_root()/<song_key>/` so non-refine runs get telemetry too. Convention: `cost_usd is None` ⇒
  unknown; `0.0` is reserved for genuinely-zero (fully cached, zero-LLM) runs.

**I8 — tiered visual analysis (fseq metrics + tiered critique):**
- **Tier 0 — deterministic fseq metrics (every iteration, ~free, no LLM):** new
  `xlights_core/preview/metrics.py` (`group_channel_index`, `FseqSeries` — per-group
  brightness/lit-fraction/motion series, pure numpy, no orchestrator/client imports) and
  `qa/fseq_metrics.py::evaluate` emitting five metric families as subscores + `fseq:*` findings:
  coverage, motion, music-sync (brightness-derivative × beat-grid cross-correlation), color/palette
  adherence + distinctness, and section-signature similarity (pixel-level repetition-rhyme /
  dynamic-range). Thread `fseq_series` through `qa.evaluate` and the refine loop's `_report`. Unlike
  the LLM critique, these findings **may be `objective=True`** — rolled out advisory-first, then
  `coverage`/`motion`/`sync` flip to objective after a calibrated pass; `color`/`rhyme` stay advisory.
  `XLO_FSEQ_METRICS=0` kill switch. When a series is supplied, the 3-point `make_lit_sampler`
  coverage retires.
- **Tier 1 — contact sheets on a cheap model (changed/flagged sections only):**
  `PreviewRenderer.render_contact_sheet(section, n=8)` tiles 6–9 beat-aligned frames (~512px, ~1–2k
  tokens) plus an optional per-pixel-std motion-heatmap tile; drop both guides from the critic prompt;
  new `visual_critic_lite` role routed to the worker tier. Critique a section only when its instruction
  hash changed since its last critique **or** Tier 0 flagged it.
- **Tier 2 — today's still+clip on the pro model, rarely:** the current `make_visual_critique` path
  survives as the escalation, firing only on Tier 0/1 disagreement, ≥2-revision churn, or a
  once-per-run final gate that runs on the **real render** when the media-attached export is possible.

**F-G — cost & quality dashboard (S once I1 lands):**
- New `reporting.py` module + `xlo report` subcommand (argparse; **no** `has_llm_key()` gate,
  deterministic, offline): `discover_logs`, `load_records` (tolerant line-by-line parse), `group_runs`,
  `summarize_run`, `build_report`, `render_text`, `render_html`. Typed `RunSummary`/`Report` pydantic
  models so F-H can consume `Report.model_dump()`.
- Metrics catalog: cost per show, cost per objective point gained (`∞ (no gain)` when gain ≤ 0), score
  trajectory, section churn, revert/regression frequency + wasted spend, skip-gate hit rate,
  model-tier attribution, stop-reason mix, judge-vs-objective agreement, finding mix.
- Compute once, render twice: terminal (stdlib formatting, no `rich`/`tabulate`) by default; `--html
  [PATH]` writes one self-contained page (no JS, no external URLs, inline SVG sparklines/bars,
  light/dark); `--json` emits the `Report`; `--reprice`; `--song`; `--cache-dir`. Pre-I1 logs parse
  fully (cost cells `—`, quality metrics complete, a costed-runs caveat line). Optional additive
  pipeline assist: `stop_reason` + `redesigned_sections` on `RevisionLogRecord` to distinguish
  stall-vs-cap.

**F-H — provider A/B eval harness (M, needs I1):**
- Per-role provider overrides in `registry.provider_for(role)` (`XLO_PROVIDER_<ROLE>` > `XLO_PROVIDER`
  > config default); `model_string`/`_settings`/`model_snapshot` resolve per role so a mixed arm's
  logged `models` field is truthful.
- **BREAKING (cache layout):** add `models_fingerprint()` and a `models: bool` opt-in to
  `cache_path`; namespace the LLM-stage caches (`song_description`, `creative_brief`, `instructions`,
  `visual_review/`) under an `m-<fp>` dir so two arms never read each other's artifacts; keep
  `song_analysis`, `targetable_groups_*`, and the shared `revision_log.jsonl` un-namespaced. Existing
  per-song LLM caches go cold once (one re-spend, regenerate on next run). This also turns
  `XLO_PROVIDER=gemini xlo run` from silently-wrong into correct.
- New `pipeline/ab.py` (`ArmSpec`, `parse_arm`, `arm_env`, `run_arm`, `run_ab`) + `xlo ab` command:
  repeatable `--arm SPEC` (≥2; `base_provider *("+" role "=" provider)`), `--repeat N` (interleaved
  A,B,A,B), always unattended, strict multi-key preflight (every named provider's key present before
  any spend). Analyze-once + inject the same `SongAnalysis`; warm the targetable-groups probe once;
  per-arm `save_as` names. Results land in the F-G surface (group by `run_id`/`models`) plus a tiny
  `ab_runs.json` manifest written incrementally. Reports medians + ranges (never single numbers);
  "indistinguishable when ranges overlap"; no significance tests in v1.

## Capabilities

### New Capabilities
- `cost-telemetry`: capture per-role/per-iteration LLM token usage into a run-scoped collector, price
  it from a config table, and surface per-run cost (revision-log fields, `usage.json`, summary line).
- `cost-quality-dashboard`: a deterministic offline analyzer + `xlo report` over the revision-log
  JSONL producing cost/quality metrics as terminal, HTML, and JSON.
- `provider-ab-harness`: run a fixture song through multiple provider routings under controlled
  conditions with model-fingerprinted cache isolation, and report per-arm distributions.

### Modified Capabilities
- `revision-log`: iteration/finalize records additionally carry per-role token usage, run totals, and
  estimated run cost; optional `stop_reason`/`redesigned_sections` for terminal-state attribution.
- `visual-critique`: critique becomes tiered — free deterministic fseq metrics first, cheap
  contact-sheet critique on changed/flagged sections, pro still+clip only as a rare escalation.
- `show-refinement`: deterministic rendered-pixel fseq metrics (coverage/motion/sync) become
  objective-gate eligible, replacing the 3-point coverage sampler; only changed/flagged sections are
  re-critiqued each iteration.

## Impact

- **New code:** `xlights_orchestrator/telemetry.py`, `xlights_orchestrator/reporting.py`,
  `xlights_orchestrator/qa/fseq_metrics.py`, `xlights_orchestrator/pipeline/ab.py`,
  `xlights_core/preview/metrics.py`.
- **Modified code:** `revision_log.py`, `models/registry.py`, `models/config.yaml`, `agents/panel.py`
  (:135,:158), `pipeline/run.py` (:163,:229,:415, `_refine_loop`, `run_pipeline` install/summary),
  `pipeline/generate.py` (:158), `pipeline/visual.py` (:94, `make_visual_critique`, `make_lit_sampler`,
  `make_tiered_critique`), `pipeline/cache.py` (`cache_path` namespacing, `models_fingerprint`),
  `pipeline/regen.py` (start_run + namespaced rehydration), `agents/visual_critic.py` (lite prompt +
  `render_sheet_input`), `qa/__init__.py` (`fseq_series` kwarg), `qa/coverage.py`,
  `xlights_core/preview/render.py` (`render_contact_sheet`), `cli.py` (`report` + `ab` subparsers).
- **Deps:** none added (terminal report uses stdlib formatting; metrics use numpy already present).
- **Tests:** `tests/test_telemetry.py` (new), `tests/test_reporting.py` (new,
  `tests/fixtures/revision_logs/`), `tests/test_ab.py`-style harness tests, extend
  `tests/test_revision_log.py`, `tests/test_orchestrator.py`, `tests/test_refine.py`,
  `tests/test_preview.py`, `tests/test_visual.py`, `tests/test_coverage_qa.py`; opt-in `-m live`
  smokes; golden pipeline (`test_golden_pipeline.py`) stays byte-identical.
- **Risk:** I1 is best-effort and cannot break a run (telemetry `record()` is `except Exception →
  log.debug`). I8 rolls objective metrics out advisory-first behind a kill switch. F-H's cache
  namespacing is a one-time cold-cache event (accepted, documented); env-var arm isolation is
  finally-restored.
