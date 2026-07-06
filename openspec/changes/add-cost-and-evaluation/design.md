## Context

This change bundles four dependency-linked roadmap items into one cost/measurement/eval cluster. The
roadmap dependency chain: **I1 token telemetry** unblocks **F-G dashboard** and **F-H A/B harness**;
**I8 tiered visual analysis** is cheaper visual analysis whose metrics feed F-A's QA and whose savings
I1 makes measurable. Recommended sequencing: I1 (step 1) → I8 Tiers 0–1 (step 2) → … → F-G/F-H (step
8, "harvest the telemetry from step 1").

**Current state — I1 (telemetry).** The workspace resolves `pydantic-ai>=1.0` to **pydantic_ai
2.5.0** (verified in-venv 2026-07-05). `pydantic_ai.usage.RunUsage` is a dataclass with fields:
`input_tokens`, `cache_write_tokens`, `cache_read_tokens`, `output_tokens`, `input_audio_tokens`,
`cache_audio_read_tokens`, `output_audio_tokens`, `details: dict[str,int]`, `requests`, `tool_calls`;
plus `.total_tokens` property, `.incr(other)` in-place accumulator, `.has_values()`. `input_tokens` is
the *uncached* remainder — total prompt = `input_tokens + cache_write_tokens + cache_read_tokens`;
multimodal (visual-critic) image tokens report inside `input_tokens`. There are exactly **seven** LLM
`.run()` sites (§ proposal), all discarding the wrapper via `(await agent.run(p)).output`. Site #4
(`generate.py:158`) is the leverage point — shared by first-pass generation, the automatic refine loop
(`regenerate_section`, `run.py:124`), and manual `xlo regen` (`regen.py`). The revision log only
exists *during refine* (constructed at `run.py:455–459`) and a `--no-log`/hermetic run has no log at
all, so the panel/director/first-pass generation run *before* it — usage needs a run-scoped
accumulator that pre-dates and outlives the loop, with the revision log as one *view*. `models/config.yaml`
is the single lru-cached routing table (role → per-provider model id) — the natural home for prices,
since a price is a property of a model id.

**Current state — I8 (visual analysis).** `make_visual_critique(client, *, save_as, song_key,
cache_root, critic=None, max_sections=6, clip_secs=10, enable_video=True, real=None)` (`visual.py:48`)
builds the async callable the refine loop invokes each iteration (`run.py:224–228`, best-effort). Per
call it flushes the `.fseq` (`save_sequence`), builds `PreviewRenderer(fseq, rgbeffects, networks)`,
prefers the real xLights render when exportable (`use_real = real is not None and await
real.refresh(client)`), picks the brightest frame per section (max 6), takes a still + ≤10s clip, runs
the multimodal agent, converts to advisory `Finding`s (`to_findings()` hard-codes `objective=False`,
`visual_critic.py:74–81`), and persists a review bundle to `cache_root/song_key/visual_review/iterN/`.
Cost anatomy of one iteration on the **planner tier**: guides ~13k (~51k chars: sequencing 23,926 +
layering 27,086), stills ~7–9k, clips ~15k+, context JSON ~1k → **~30–40k multimodal tokens**, ×
`max_iterations` (default 3). Two structural wastes: it re-judges **all** sections every iteration
though `regen` is section-scoped (`replace_section` splices one section), and its findings cannot move
the objective gate. The deterministic eyes already exist: `load_fseq` returns `uint8 [num_frames,
channels]`; `render.py:43` builds the node→channel map; but `make_lit_sampler` (`visual.py:105`) only
samples pointwise at three timestamps (`_SAMPLES = (0.25, 0.5, 0.75)`, `coverage.py:16`), rendering a
full 1280×720 PNG per sample just to count `max(RGB) > 30` pixels. `qa/coverage.py` scores sections
with intensity ≥ `MIN_INTENSITY = 0.5` against `EXPECTATION = 0.6` × the show's own peak, failing
under `FAIL_FRACTION = 0.5` → an objective error; coverage already joins the *objective* average
(`qa/__init__.py:24–28`) — the precedent this design generalizes. `parse_models` yields per-model
`start_channel`/`n_pixels` (Default-preview models only); group membership lives in `<modelGroups>`
(walked by `layout_semantics.py`). `RealRender` (`visual.py:155–215`) exports the true render
(media-attached sequences only; a media-less export crashes xLights), caches by `.xsq` mtime.

**Current state — F-G / F-H (reporting & routing).** `RevisionLogRecord` (`revision_log.py:33-52`)
already carries `obj_before/obj_after/obj_delta`, `reverted`, `regenerated_sections`, `revisions`
(with `origin: "judge"|"backstop"`), `judge` dict, `human_decision`, and the per-role `models`
snapshot — every field the *quality* half of the dashboard needs. The `_record` closure
(`run.py:201-209`) writes at: skip-high-objective early return (`run.py:214`,
`human_decision="skip-high-objective"`, a `finalize` at iteration 0), accept/stop (`run.py:233`),
plateau (`run.py:240`), every applied iteration (`run.py:290`), and finalize (`run.py:305`). Two stop
causes are **not** distinguishable today: the stall stop (`run.py:297-298`) and the `max_iterations`
cap both fall through to finalize. `RevisionLog.write` opens with `"a"` so one `revision_log.jsonl`
accumulates *many runs* — grouping key is `(song_key, run_id)`. `models/registry.py` (72 lines) is the
whole routing layer: `active_provider()` re-reads `os.environ["XLO_PROVIDER"]` every call; `XLO_PROVIDER`
flips **all six roles at once** — there is no per-role override; `model_string(role, *, provider=None)`
and `_settings(role, *, provider=None)` already accept an explicit provider but nothing passes it;
sampling params are deliberately never set (removed on Opus 4.8 → 400), so **runs are not
reproducible**. `pipeline/cache.py` keys everything by `sha1(audio bytes)[:16]` + stage name —
provider/model appear **nowhere** — so `XLO_PROVIDER=gemini xlo run` silently reuses Claude's
`song_description`/`creative_brief`/`instructions`, and the second run's log records
`models: {director: google:..., ...}` against outputs Claude produced. `cli.py` uses **argparse** (not
click) with subcommands `run`/`regen`/`edit-brief`; `run`/`regen` gate on `has_llm_key()`.

## Goals / Non-Goals

**Goals:**
- Turn every future run into evaluation data: per-role/per-iteration token counts and per-run cost in
  the revision log, plus a `usage.json` for non-refine runs; prices are data, not code.
- Cut visual-analysis cost >10× per refine iteration while *adding* objective rendered metrics that do
  not exist today (coverage/motion/sync from the exact `.fseq`).
- A deterministic offline dashboard (`xlo report`) answering cost-per-show, cost-per-point, churn,
  reverts, skip-gate rate, tier attribution — no LLM, no xLights, no network.
- A repeatable provider A/B harness (`xlo ab`) that produces *data* (distributions), with correct
  cache isolation so arms never contaminate each other, feeding the F-G surface.
- Telemetry never breaks a run; new QA metrics roll out advisory-first behind a kill switch; every
  pre-existing hermetic test passes unmodified.

**Non-Goals:**
- No retroactive backfill of token counts for past runs (unrecoverable; rendered `—`/unknown).
- No proxy-cost estimation for pre-I1 logs (would fabricate exactly the numbers this exists to make
  real).
- No significance tests in the A/B harness v1 (n ≤ 5 songs × 3 repeats can't carry them); no LLM seed
  or temperature control (registry deliberately sets none).
- No `rich`/`tabulate`/new dependency for reporting; renderers are formatting-only.
- Tier 2 is the *current* visual-critic code, demoted — not a rewrite.

## Decisions

**1. Telemetry via a ContextVar collector + explicit per-site capture.**
A run-scoped `UsageLog` installed in a `ContextVar` (`telemetry.py`), with `telemetry.record(role,
result)` called at each of the seven sites (each `(await agent.run(p)).output` becomes `res = await
agent.run(p)` / `telemetry.record("judge", res)` / `verdict = res.output`). *Alternative rejected:*
wrapping `Agent` in `registry.build_agent()` for automatic capture — it would miss context we may want
later (section index, iteration) and would not cover injected test fakes; seven explicit greppable
lines match the codebase's "plain async stages" style, and `build_agent` stays a pure constructor.
*Alternative rejected:* threading a collector through `State` — `panel.run_panel` and the
`make_visual_critique` closure never see `State` construction; a contextvar reaches every await point
under `run_pipeline` (and propagates through `asyncio.gather`, so the concurrent `Semaphore(3)`
analysts each record correctly) without signature churn; `State` gets a read-only view at finalize.
`record()` maps `RunUsage` → `RoleUsage` (`requests`, `input_tokens`, `output_tokens`,
`cache_read_tokens`, `cache_write_tokens`; audio fields ignored for now) and is fully best-effort
(`except Exception → log.debug`) so a fake without `.usage()` or an absent collector is a defined
no-op. `RunUsage.incr()` is reused for summation.

**2. Per-role granularity, per-site context deferred.** Analysts record as one `analyst` role (not
`analyst:structure`) so the role key matches `model_snapshot()` keys and the pricing lookup; the
redesigner records as `director` (it routes as the director role in config.yaml). Per-iteration delta
attribution comes for free from the record's existing `iteration`; per-section attribution is a cheap
later extension (an optional `events` list) once F-G asks — the map shape leaves room.

**3. JSONL schema extension is additive, defaulted, backward compatible.** `usage`/`usage_total`
default `{}`, `cost_usd` defaults `None`, so old JSONL lines validate unchanged (pinned by test). The
`_record()` closure adds `usage=usage_log.drain_delta()` to every record (each iteration carries the
tokens spent producing it); the finalize record additionally carries `usage_total=snapshot()` and
`cost_usd=estimate_cost(...)`. Pre-loop spend (panel/director/first-pass) lands in the first record's
delta — acceptable for iteration analysis, and fully broken out in `usage.json`. `_render_md()` gains
one finalize-only tail line (`**Tokens:** generator 142k→31k · critic 97k→4k · … · **$2.41**`).

**4. Prices are data in `models/config.yaml`, cost is a pure function.** New top-level `pricing:`
block keyed by bare model id, USD per 1M tokens. Claude rows real: `claude-opus-4-8: {input: 5.00,
output: 25.00, cache_read: 0.50, cache_write: 6.25}`, `claude-sonnet-4-6: {input: 3.00, output: 15.00,
cache_read: 0.30, cache_write: 3.75}` (cache read 0.1× input, cache write 1.25× input per Anthropic).
Gemini rows commented TODO — *do not guess*; a missing entry ⇒ cost `None`, never zero.
`price_for(model_id)` and `estimate_cost(models, usage) -> float | None` (returns `None` if any role
with nonzero usage lacks a price row) live next to `_cfg()` in `registry.py`. Convention: `None` ⇒
unknown; `0.0` ⇒ genuinely zero (fully cached).

**5. I8 three tiers, cheapest first, each escalating only what it can't settle.**
- *Tier 0 fseq metrics* (`preview/metrics.py`, pure numpy, **no client/orchestrator imports** — an
  F-J-alignment contract in the docstring): `group_channel_index(rgbeffects, networks, groups)` joins
  `parse_models()` with `<modelGroups>` membership (channel-bound per `render.py:48`, unknown/empty
  groups omitted); `FseqSeries` computes per-group brightness `B[g][t]=v[t,nodes_g].mean()`, lit
  fraction `L[g][t]=(v>lit_threshold).mean()` (threshold 30, matching `make_lit_sampler`), and motion
  `M[g][t]=|v[t]-v[t-1]|[nodes_g].mean()` in one vectorized pass (a 4-min song at 50ms × ~20k channels
  is a ~92 MB uint8 array, reduced immediately to per-group float32 series). Five metric families in
  `qa/fseq_metrics.py::evaluate(plan, analysis, series, *, repetition_map) -> (subscores, findings)`:
  **coverage** (`fseq:coverage`, generalizes `coverage.evaluate` from the full series, attributable),
  **motion** (`fseq:motion`, per-group frame-delta normalized by brightness, section = lit-weighted
  mean), **sync** (`fseq:sync`, cross-correlate positive d/dt brightness with a beat impulse train
  from `SongAnalysis.beats`, ±1 frame, lag-0 normalized against a circular-shift baseline),
  **color** (`fseq:color`, 24-bin lit-node hue histogram vs planned palette — adherence + distinctness
  catching "gold+amber+warm-white reads as one color" when three planned hues are <~20° apart), and
  **rhyme/range** (`fseq:rhyme`/`fseq:range`, cosine similarity between sections sharing a
  `repetition_map` label; spread between quietest/loudest — the pixel-level complement of
  improve-musicality's instruction-level metrics). Unreadable inputs → `({}, [])` (never gate blind).
- *Tier 1 contact sheets* (`PreviewRenderer.render_contact_sheet`): 6–9 beat-aligned frames tiled to
  ~512px (~1–2k tokens) + optional per-pixel-std heatmap tile; drop both guides (saves ~13k) but keep
  the per-section context JSON and the "judge against the music at that moment" framing; new
  `visual_critic_lite` role (worker tier: `anthropic: claude-sonnet-4-6` / `gemini:
  gemini-3.1-flash-lite`) via `build_agent`; scope = sections whose sha256 instruction hash changed
  since last critique OR Tier 0 flagged.
- *Tier 2 escalation* (today's `make_visual_critique`, unchanged): fires only on Tier 0/1 disagreement,
  ≥2-revision churn (the anti-oscillation ledger tracks this), or a once-per-run final gate on
  `RealRender`. Cost after (6-section show, 3 iters): ~100–120k planner tokens → ~15–25k mostly worker
  + one small planner call, >10× cheaper.

**6. fseq metrics may enter the objective gate — advisory-first rollout.** They are deterministic and
reproducible, the stated bar. Land everything `objective=False` for logged runs, calibrate thresholds
against the revision log, then flip `coverage`/`motion`/`sync` to `objective=True`; `color`/`rhyme`
stay advisory (taste-adjacent). `XLO_FSEQ_METRICS=0` disables the whole family (mirrors
`XLO_REFINE_SKIP_OBJECTIVE`). When `fseq_series` is supplied, `make_lit_sampler`/3-point coverage
retire (the series strictly dominates them) — shown equal-or-better on a real run first. `qa.evaluate`
grows an optional `fseq_series` keyword next to `sampler`; `_report` (`run.py:172-184`) constructs the
series after the save-flush (mtime invalidation like `make_lit_sampler`).

**7. Offline-vs-real fidelity caveat.** The `.fseq` channel data *is* the true render (Tier 0 measures
ground-truth per-node values). What is approximate is downstream: the offline orthographic-splat
*projection* vs xLights' preview drawing (why Tier 1/2 prefer real frames when `real.refresh()`
succeeds), *staleness* (metrics run only after the save-flush), and *scope* (offline parsers include
Default-preview models only, so props parked elsewhere are invisible to metrics and montages).
Therefore keep one real-render check per run — the Tier 2 final gate on `RealRender` — as the
ground-truth backstop.

**8. F-G is a package module behind `xlo report`, not a script.** A standalone script would re-declare
the schema or import the package anyway and would drift (the original 42-run analysis script no longer
exists). `reporting.py` (sibling of `revision_log.py`, deliberately *not* under `pipeline/` — it never
touches a live run) gets the real `RevisionLogRecord`, real `cache_root()`, and pytest coverage.
`RunSummary`/`Report` are pydantic so the computed layer is serializable (`--json`, F-H input).
Compute once, render twice: all arithmetic in `summarize_run`/`build_report`, `render_text`/`render_html`
format only (divergence = a bug in the split). `xlo report` must **not** gate on `has_llm_key()`.
Discovery via `root.glob("*/revision_log.jsonl")` naturally ignores top-level `targetable_groups_*.json`
(they're files). Prefer the record's run-time `cost_usd` (rates as-of-run beat rates as-of-report);
`--reprice` recomputes. Graceful degradation on pre-I1 logs is a hard requirement: `has_cost: bool` per
run; when false cost cells render `—`, cost metrics are omitted, aggregate cost counts only costed runs
with an explicit "12 of 42 runs have cost data" caveat, and all quality metrics work at full fidelity.

**9. F-H: env-var per-role overrides + model-fingerprinted cache namespacing + `xlo ab`.**
`provider_for(role)` resolves `XLO_PROVIDER_<ROLE>` > `XLO_PROVIDER` > config default;
`model_string`/`_settings`/`model_snapshot` switch to it per role (making a mixed arm's logged `models`
truthful, e.g. `{generator: google:gemini-3.1-flash-lite, judge: anthropic:claude-opus-4-8}`); env
vars match the config's "no code change" philosophy and work for plain manual runs
(`XLO_PROVIDER_JUDGE=gemini xlo run …`). `cache_path(key, stage, *, models=False)` namespaces LLM-stage
artifacts under `m-<models_fingerprint()>` (one *whole-snapshot* fingerprint — over-invalidates
slightly but is impossible to get wrong, and stage inputs are transitively coupled). Namespaced:
`song_description`, `creative_brief`, `instructions`, `visual_review/`. Shared: `song_analysis`
(deterministic audio), `targetable_groups_*` (layout-fingerprinted), and `revision_log.jsonl` (one
per-song log containing *all* arms, distinguished by `run_id`+`models` — what the F-G analyzer groups
by). **No legacy-path read fallback** (would re-open the cross-provider reuse bug); existing caches go
cold once. `xlo ab` (Option A CLI, not a pytest suite — pytest wants pass/fail, an A/B produces *data*)
runs arms sequentially (the `XLightsClient` mutation lock + single live app + process-global env swap
forbid concurrency), always unattended, strict multi-key preflight, analyze-once + inject the same
`SongAnalysis`, warm the probe cache once, interleaved repeats. A thin hermetic pytest layer tests the
harness itself with the golden-test fakes. Results reuse the F-G surface (group by `run_id`) plus an
`ab_runs.json` manifest written incrementally.

**10. Statistical honesty with small n.** Repeats minimum before believing any delta; report per-arm
median + min–max range for every metric; an arm-vs-arm delta smaller than either arm's range is
"indistinguishable". Valid conclusions: categorical failures ("gemini flash-lite emitted invalid
structured output in 2/3 runs"), consistent large gaps (non-overlapping ranges across ≥3 repeats on ≥2
songs), cost ratios (token counts far less noisy than scores). Invalid: "provider A is better", any
single-run comparison, extrapolation beyond the fixture songs or the current prompt set (a prompt edit
invalidates prior A/B data — the models fingerprint does not hash prompts; noted in the report header).
Fixture set: 3–5 short (≤90s) committed songs spanning vocal/instrumental, high/low energy,
simple/complex sectioning.

## Risks / Trade-offs

- [I1: telemetry failure breaks a run — the one thing observability must never do] → `record()` fully
  best-effort (`except Exception → log.debug`), mirroring `RevisionLog.write()`; collector absence is a
  defined no-op.
- [I1: PydanticAI renames `RunUsage` fields again (were `request_tokens`/`response_tokens` in 0.x)] →
  field mapping isolated in one function; a unit test constructs a real `RunUsage` so an upgrade breaks
  a test, not a run.
- [I1: stale price table silently misprices] → prices are data with a source header comment; unknown
  model ⇒ `cost_usd: None`, never a guessed number.
- [I1: existing ~65 test files' fake agents lack `.usage()`] → duck-typed best-effort capture (tested
  explicitly); zero test-fixture churn.
- [I1: ContextVar surprises if two pipelines run concurrently in one process] → ContextVar is
  per-task-tree; each `run_pipeline` calls `start_run()` in its own context (documented in docstring).
- [I8: miscalibrated Tier 0 thresholds enter the gate → wrong reverts/stalls] → advisory-first rollout
  before flipping objective; per-metric flip; `XLO_FSEQ_METRICS=0`; thresholds documented with
  evidence like `coverage.py`.
- [I8: whole-fseq load heavy on long songs (~100 MB uint8)] → acceptable; if not, reduce per zstd block
  during decode and keep only per-group float32 series.
- [I8: offline projection/scope gaps (non-Default-preview props invisible)] → metrics read channels not
  projections (only the group index must be complete; log group channel coverage); Tier 2 final gate on
  RealRender backstops.
- [I8: 512px montage too coarse — lite model misses defects] → Tier 0 flags independently
  (disagreement escalates); montage size/tile count are dials; calibration compares Tier 1 vs today.
- [I8: carried-forward findings go stale after whole-list passes] → tag carried findings ("[prev
  iter]"); hash the *finalized* section slice so whole-list changes re-trigger critique.
- [I8: beat grid vs fseq frame grid misalignment (lead-in, 50ms quantization)] → ±1 frame tolerance;
  correlate at small lags and report argmax lag as diagnostic; RealRender's ffprobe offset trick shows
  the lead-in pattern.
- [I8: new lite role missing under a provider → runtime KeyError] → I6's `test_registry.py`
  every-role×provider invariant covers it once `visual_critic_lite` is added.
- [F-G: I1 lands with different field names] → F-G sequenced after I1; plan step 1 is reconciliation;
  the post-I1 fixture is written from I1's actual output, not the design doc.
- [F-G: historical JSONL (fields added over 63 changes) fails validation] → tolerant per-line parse
  with a surfaced skipped-line counter; pydantic defaults absorb missing fields; checked-in raw
  fixtures pin the oldest shape.
- [F-G: cost-per-point divides by zero/negative gain] → defined rendering `∞ (no gain)`; skip-gate runs
  excluded from the aggregate by construction; golden test.
- [F-G: append-mode file mixes aborted/partial runs (no finalize)] → summarized from the last
  iteration, flagged `incomplete`, counted separately.
- [F-G: report grows into a second rendering codebase] → hard rule — arithmetic only in
  summarize/build; renderers formatting-only; no JS, no new deps.
- [F-H: cache namespacing invalidates all existing per-song LLM caches] → one-time re-spend on next
  run; `song_analysis` (the expensive deterministic part) untouched.
- [F-H: env-var override leaks out of an arm on exception] → `arm_env` is a context manager with
  finally-restore; the exception path is tested explicitly.
- [F-H: conclusions over-read from tiny n] → medians+ranges only; hard-coded "indistinguishable" rule;
  no significance stats v1.
- [F-H: judge role differs across arms → the referee changes with the player] → objective/advisory
  scores come from deterministic QA, not the judge — the primary comparison metric is provider-neutral;
  judge verdicts only steer trajectories (reported as convergence behavior).
- [F-H: a 3-arm × 3-repeat A/B is ~9 full refine runs of real money] → short fixture songs; strict
  key/arm preflight; print an estimated-spend warning (post-I1, from historical per-run cost).

## Migration Plan

- **I1 schema:** additive/defaulted — old `revision_log.jsonl` lines validate unchanged (test-pinned).
  No retroactive backfill; the F-G analyzer treats absent `usage_total` as "unknown", rendered
  distinctly from `$0.00`. Detection heuristic: records with `usage == {} and usage_total == {}` and a
  `ts` before the I1 ship date are pre-telemetry; after it, an empty map on a finalize record means "no
  LLM calls" (skip-high-objective on fully cached stages). One `docs/usage.md` paragraph documents
  `usage.json`, the JSONL fields, and the None-vs-zero convention.
- **I8 gate flip:** land advisory, calibrate on 2–3 refine songs, document thresholds in the module,
  then flip `coverage`/`motion`/`sync` objective; announce in `docs/usage.md` env knobs. The golden
  test doesn't cover refine, so nothing regenerates.
- **F-H cache layout (BREAKING for the cache dir):** existing per-song LLM caches are simply cold after
  the change — they regenerate on the next run; `regen.py`'s `FileNotFoundError` message already says
  "run `xlo run` first". No legacy-path fallback by design. Ship the registry override + cache
  namespacing first (independently valuable — fixes `XLO_PROVIDER=gemini xlo run`), the harness after.

## Open Questions

- **I1 per-analyst split:** one `analyst` role now (matches routing/pricing keys) vs `analyst:structure`
  etc. — proposal: one role, add optional `details: dict[str,int]` on `RoleUsage` if F-G wants the
  split.
- **I1 per-section/per-stage attribution:** F-G's "which sections churn" could use `section_index` on
  generator events — deferred; needs an `events` list rather than role maps (compatibly addable).
- **I1 Gemini pricing ownership:** who keeps Google's rates current; should `estimate_cost` warn once
  when an active provider has unpriced models?
- **I1 thinking tokens:** verify PydanticAI folds Anthropic thinking (billed as output) into
  `output_tokens` (expected) or exposes them in `details`; pin with the live smoke.
- **I1 `usage.json` shape:** list-of-runs per song key (proposed) vs one file per run — list-per-song is
  simpler for the dashboard scan.
- **I8 brightness proxy:** `max(R,G,B)` (matches sampler) vs luma for color — proposal: max for
  coverage/motion, luma inside `fseq:color` only.
- **I8 where sync lives long-term:** `fseq:sync` and `qa/sync.py` both feed the objective average —
  merge (rendered sync supersedes instruction sync when a series exists) or keep both?
- **I8 carry-forward vs drop** for unchanged sections' Tier 1 findings — leaning carry, tagged, with the
  plateau detector's signature ignoring tagged findings.
- **I8 Tier 0 at generate time?** to gate the skip-high-objective decision with rendered evidence —
  cheap once the series exists; changes `REFINE_SKIP_OBJECTIVE` calibration.
- **I8 montage color fidelity vs downscale:** 512px / 9 tiles ≈ 170px/frame — does Tier 1 get one
  extra full-res still for its worst Tier-0-scored moment?
- **I8 F-J alignment:** `FseqSeries` avoids any client dependency from day one (yes — paths only);
  write it into the module docstring as a contract.
- **F-G where does I1 put non-refine spend?** panel/synthesizer/director-first-pass run before
  `_refine_loop`; if I1 logs pre-loop usage as an iteration-0 / `kind="generate"` record, cost-per-show
  is whole-show; else F-G labels its number "refine cost" honestly. Settled in I1.
- **F-G cache-hit accounting:** should `RunSummary` mark which stages were cache hits (I1 could log a
  zero-usage marker) for apples-to-apples cost-per-show?
- **F-G song display names:** derive from `description.md`'s first heading (read-only heuristic) vs a
  tiny `meta.json` at run time (touches the pipeline).
- **F-G should `stop_reason` ride with I1 or I3?** I3 rewrites `_refine_loop` into named guard
  functions — the natural moment for each guard to record its own name.
- **F-G→F-H interface:** is `Report.model_dump()` + `--json` sufficient as the A/B comparison input, or
  does F-H want `summarize_run` granularity? (Design F-H against the JSON schema F-G ships.)
- **F-H prompt fingerprinting:** should `models_fingerprint` also hash system prompts / a package
  version so prompt edits auto-invalidate caches and A/B comparability is machine-checked? (Broader than
  F-H — changes cache behavior for everyone.)
- **F-H fixture songs:** real licensed MP3s under `data/` (not committed) vs synthesized short audio
  (hermetic but may not exercise stems/lyrics paths meaningfully).
- **F-H same-provider A/B:** the arm grammar covers providers only; extending to inline model/settings
  (`anthropic+generator.model=claude-haiku-4-5`) starts duplicating config.yaml — alternatively
  `--config path/to/alt-config.yaml` per arm.
- **F-H F-J interaction:** once headless offline-render iteration exists, should `xlo ab` gain
  `--headless` + a CI/pytest entry point? The `run_ab()` seam is designed additive.
- **F-H visual critic in arms pre-I8?** the most expensive role, advisory only, doubles arm cost — a
  `--no-visual` flag (a small new `run_pipeline` off switch, since passing `visual_critique=None` with
  `refine=True` currently builds a real critique).

## Notes

- The roadmap notes F-H's implementation "should open a new change, likely split as
  `add-provider-cache-namespacing` (registry override + cache namespacing, independently valuable) and
  `add-provider-ab-harness` (the harness)." This change keeps them in one `provider-ab-harness`
  capability but the tasks group orders the cache-namespacing steps first (independently shippable) so
  the split can still be honored at PR time.
- F-H's summary-extraction (`summarize_runs(jsonl_lines, run_ids) -> ArmSummary`) is intended to be the
  *same* function as F-G's `summarize_run` — implement it in the F-G `reporting.py` and import it in
  the harness rather than duplicating the arithmetic.
- I8 step-7 note: the change doc's before/after cost evidence for the I8 archive comes from I1's
  telemetry if landed; else from counted calls × estimated sizes in the revision log.
