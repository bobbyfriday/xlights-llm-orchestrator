## Why

A full pipeline run is long, network-heavy, and largely unobservable, and the roadmap's Horizon 4
("Operability & evaluation") groups four items that make it survivable, diagnosable, watchable, and
eventually runnable without a human at a terminal. Today:

- **Transient failures kill or silently degrade runs (I2).** A run makes ~10–20 LLM requests
  (3–4 analysts, synthesizer, director, one generator call per section, judge + visual critic +
  regens per refine iteration) and *hundreds* of xLights REST calls (one `addEffect` per placed
  effect, plus probe/save/render/export). One 429/529 on a panel analyst drops it from the brief
  (`agents/panel.py:142–145`) with a nameless `log.warning`; a 529 on the director or synthesizer
  aborts the run after minutes of audio/stem work; a momentary xLights hiccup during
  `apply_instructions` fails the whole emit stage even though the very next request would have
  succeeded. The only explicit retry anywhere is `lyricsgenius(retries=1)` in `lyrics.py:60–62`.
- **Best-effort failures are invisible (I5).** The best-effort posture (lyrics, stems, visual
  critique, real render, timing tracks, caching are enrichments) is correct, but it is implemented
  as 45 `except Exception` blocks across 20 files (measured 2026-07-05, matching the roadmap count);
  12 are fully silent, the rest scatter across debug/info/warning with no rule. When a show "looks
  off," the operator cannot tell "stems failed" from "the critic never ran" from "coverage QA was
  blind." The target: turn "the show looks off" into "stems failed, brief had no instruments."
- **Attended runs hold a terminal hostage (F-I).** An attended `xlo run --refine` is a 10–30 minute
  pipeline whose only live surface is stdout, and it stops at blocking `input()` prompts
  (`run.py:106,115,96,120`) that park the async event loop. There is no view of stage progress,
  per-section generation, QA scores per iteration, or refine decisions.
- **Every run needs a live GUI xLights (F-J).** The one hard dependency blocks CI full-pipeline
  evals, cloud execution, and fast refine loops. An offline preview renderer already exists and
  already feeds the critic and coverage sampler; a spike must answer honestly what truly requires the
  live app (render fidelity is the open question).

## What Changes

**I2 retry/backoff for transient failures:**
- Add one thin, stdlib-only async retry primitive `xlights_core.retry.with_retry()` (exponential
  backoff + full jitter; no `tenacity` dependency) plus a transport predicate `xlights_transient()`.
- Add an LLM transient predicate `llm_transient()` and a `run_agent()` wrapper in
  `models/registry.py`; route the run-fatal and best-effort LLM call sites through it with per-site
  attempt counts (director/synthesizer/generator/judge = 3; analysts/visual-critic/redesigner = 2).
- Wrap the xLights transport boundary inside `XLightsClient`: reads retry on connection error AND
  timeout; mutations retry on connection error only, **inside the write lock**, preserving ordering;
  `render_all`/`export_video_preview` are excluded. Split the catch-all transport mapping so
  "provably never sent" is distinguishable.
- Panel analysts retry once before being dropped, and the drop log **names the analyst key** at
  WARNING (`agents/panel.py`).

**I5 diagnosable best-effort failures / degradation logging:**
- One logging convention applied to all 45 blocks: silent `pass` is **banned**; cosmetic
  degradations log `debug`, whole-capability losses log `warning` — so `grep -i warning` is a
  complete degradation list.
- New per-run degradations collector `xlights_orchestrator/degradations.py` (ContextVar pattern,
  best-effort, closed capability taxonomy), an end-of-run summary block, and a best-effort
  `degradations.json` written beside `revision_log.jsonl`.
- Make `groups.py:43` (failed group *listing*) re-raise instead of limping on an empty list; a
  structural audit test bans silent swallows going forward. `xlights-core` blocks get the convention
  only (no orchestrator imports); the orchestrator reports core-owned outcomes at the seam.

**F-I live progress streaming UI:**
- New `progress.py` (`ProgressEvent`, thread-safe append-only `ProgressBus` with queue fan-out,
  `NullProgressBus` twin), injected into `run_pipeline`/`_refine_loop` (default `NullProgressBus`,
  `--auto`/tests unchanged), with emits at existing seams (stage bracketing, per-section, per-score,
  refine decisions, checkpoints, terminal `done`).
- New stdlib-only `live_server.py` (`ThreadingHTTPServer`, `daemon_threads`, port 0) serving an SSE
  event stream, a self-contained live HTML page (stage timeline, section grid, SVG QA sparkline,
  revlog tail, checkpoint panel), and a `POST /checkpoint/<id>` route.
- A `CheckpointGate` that replaces the four blocking `input()` checkpoints with browser
  approve/edit, waiting via `asyncio.to_thread(queue.get)` so the loop is never parked; terminal
  fallbacks stay wired. New `--no-browser` CLI flag; `--auto` semantics untouched.

**F-J headless / preview-only iteration mode (exploratory spike):**
- Run a spike (not a shipped feature) to determine what truly requires live xLights, measured with
  evidence: an offline-vs-real fidelity report, a re-verified client-call inventory, and a
  version-stamped test of xLights batch/CLI render on macOS and Linux (Xvfb).
- Land the durable artifact regardless of outcome: a checked-in fixture `.fseq` + layout pair and a
  hermetic test running the coverage sampler / Tier-0 metrics over it (seed of the CI eval suite);
  optionally the `get_models` prefetch batching seam.
- Produce a written go/no-go against the decision table (option (a) file-based emitter +
  `BatchRenderer`; hybrid folded into I8; or fallback batching), naming the chosen follow-up.

## Capabilities

### New Capabilities
- `fault-tolerance`: a shared transient-only retry/backoff primitive and its application at the LLM,
  xLights-transport, and panel-analyst seams (I2).
- `degradation-logging`: the best-effort logging convention plus a per-run degradations collector,
  end-of-run summary, and `degradations.json` artifact (I5).
- `live-progress`: a live browser progress surface (event bus + SSE server + page) and browser-backed
  approval checkpoints replacing the blocking terminal prompts (F-I).

### Modified Capabilities
- `xlights-read-access`: reads and mutations self-heal on transient transport failures with bounded
  retry, mutations connection-only inside the write lock (I2).
- `show-refinement`: attended checkpoints are answerable from a browser and never park the event
  loop; the end-of-run degradations summary is part of the run's output (I5/F-I).
- `show-orchestration`: the pipeline emits a live progress event stream and can run headless against
  a pre-rendered fixture `.fseq` for evaluation, without a live GUI xLights (F-I/F-J).
- `visual-critique`: best-effort degradations of the critic / real render are reported to the
  per-run degradations summary rather than swallowed (I5).

## Impact

- **New modules:** `packages/xlights-core/src/xlights_core/retry.py`;
  `packages/xlights-orchestrator/src/xlights_orchestrator/degradations.py`, `progress.py`,
  `live_server.py` (and possibly `checkpoints.py`).
- **Modified code:** `xlights_core/client.py` (`_request`, `_mutate`, transport mapping, constructor
  knob), `xlights_core/exceptions.py`, `xlights_core/__init__.py`; orchestrator `models/registry.py`,
  `agents/panel.py`, `pipeline/run.py`, `pipeline/generate.py`, `pipeline/visual.py`,
  `pipeline/groups.py`, `qa/coverage.py`, `effect_emitter.py`, `pipeline/weave.py`,
  `pipeline/media.py`, `pipeline/timing.py`, `pipeline/finalize.py`, `pipeline/triggers.py`,
  `pipeline/regen.py`, `lyrics.py`, `revision_log.py`, `cli.py`; core `audio/analyzer.py`,
  `audio/extractors/stems.py`, `audio/lyrics_align.py`, `knowledge/layout_semantics.py`.
- **Tests:** new `tests/test_retry.py`, `tests/test_degradations.py`, `tests/test_progress.py`,
  `tests/test_live_server.py`; extensions to `tests/test_client.py`, `tests/test_orchestrator.py`,
  `tests/test_refine.py`, `tests/test_targetable_groups.py`, `tests/test_brief_editor.py`; a
  structural log-audit test; a headless fixture `.fseq` test; the golden pipeline snapshot must stay
  byte-identical under the null bus and logging-only edits.
- **Deps:** none new (stdlib-first throughout). **Docs:** `docs/usage.md` (retry knob, degradations
  taxonomy + `degradations.json`, run-mode matrix), plus a project-convention note that new
  best-effort blocks must log.
- **Risk profile:** I2 and I5 are behavior-preserving hardening (retry only on transient classes;
  logging-only except the one `groups.py:43` re-raise and the collector). F-I is additive behind a
  null default (`--auto`/golden unchanged). F-J ships no production behavior change (a spike + a
  fixture test + an optional batching seam).
