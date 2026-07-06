## 1. I2 — retry/backoff for transient failures

- [x] 1.1 Add `packages/xlights-core/src/xlights_core/retry.py` with async `with_retry(fn, *,
  retryable, attempts=3, base_delay=1.0, factor=2.0, max_delay=20.0, jitter=0.5, label="")`
  (exponential backoff, full ±jitter band, WARNING per retry with label/attempt/cause, original
  exception type propagates on exhaustion) and `xlights_transient(exc) = isinstance(exc,
  (XLightsConnectionError, XLightsTimeout))`; export both from `xlights_core/__init__.py`.
- [x] 1.2 Split the catch-all transport mapping in `client.py:96`: introduce
  `XLightsTransportError(XLightsConnectionError)` in `exceptions.py` for the sent-but-failed case so
  existing `except XLightsConnectionError` callers still catch both.
- [x] 1.3 Add `XLightsClient._request_with_retry(...)`; route read commands (`get_models`,
  `get_model`, `get_show_folder`, `get_open_sequence`, ...) through it with `xlights_transient`; change
  `_mutate` to retry on `XLightsConnectionError` only, **inside the write lock**; exempt `render_all`
  and `export_video_preview` from mutation retry. Add constructor knob `retry_attempts: int = 3`
  (0/1 disables).
- [x] 1.4 Add `llm_transient(exc)` (`_TRANSIENT_HTTP = {408,429,500,502,503,529}`; `ModelHTTPError`
  status test, else `httpx.TimeoutException`/`TransportError`) and `run_agent(agent, prompt, *, role,
  attempts=3)` in `models/registry.py`.
- [x] 1.5 Route the LLM call sites through `run_agent` with the per-site attempts: director
  (`run.py:415`), synthesizer (`panel.py:158`), generator (`generate.py:158`), judge (`run.py:229`)
  = 3; panel analysts (`panel.py:135`), visual critic (`visual.py:94`), section redesigner
  (`run.py:163`) = 2.
- [x] 1.6 Panel change (`agents/panel.py`): retry each analyst once inside the semaphore; `zip(
  analysts, results)` so the drop log names the analyst `key` at WARNING; the terminal loss reports
  `degradations.note("refine:analyst-drop", ...)` (once I5 lands).
- [x] 1.7 Tests — new `tests/test_retry.py`: success-first (one call, no sleep); transient×2 then
  success (three calls, value returned); non-retryable first try (one call, original type propagates);
  exhaustion (`attempts` calls, last exception unchanged); backoff monotone + capped (patch
  `random.uniform`, capture `asyncio.sleep` args); predicate tests (`llm_transient(ModelHTTPError(429))`
  true, 400 false, `UnexpectedModelBehavior` false; `xlights_transient` over the whole taxonomy).
- [x] 1.8 Tests — extend `tests/test_client.py` with `MockTransport` handlers: read `getModels`
  `ConnectError`×2 then 200 (3 transport calls, result returned); mutation `addEffect` `ConnectError`
  then 200 (placed exactly once); mutation `ReadTimeout` (no retry — `XLightsTimeout` after one
  attempt); 503 "Unknown model." (no retry — `XLightsResponseError` immediately); lock-hold ordering
  test (a retrying mutation + a concurrent second mutation → the second's transport call happens only
  after the first completes).
- [x] 1.9 Tests — panel/refine: analyst raising `ModelHTTPError(529)` once then succeeding (brief has
  its output, no drop warning); always-failing analyst dropped after exactly 2 calls with a WARNING
  naming its key (`caplog`); all-analysts-fail still `RuntimeError`; judge raising 529-once completes
  the iteration; visual critique raising twice skips findings and the loop continues.
- [x] 1.10 Docs — note retry behavior + any env knob in `docs/usage.md`; add the double-retry-avoidance
  note in `lyrics.py`'s docstring; confirm the full hermetic suite passes with no fixture changes and
  no measurable slowdown (retry tests use `base_delay=0`).

## 2. I5 — diagnosable best-effort failures / degradation logging

- [x] 2.1 Add `packages/xlights-orchestrator/src/xlights_orchestrator/degradations.py`: `Degradation`
  model, `DegradationLog` (capability-keyed dedup, `note`, `summary`), ContextVar `_current`,
  `start_run()`/`current()`, module-level best-effort `note(capability, exc_or_detail, *, stage=None,
  level=WARNING)`, `render_summary()` (pure list→text), and the closed capability-key taxonomy in the
  module docstring.
- [x] 2.2 Install per run: `degradations.start_run()` at the top of `run_pipeline()` and
  `regen_section()`; summary emission (WARNING when non-empty, INFO "no degradations" otherwise) +
  best-effort `cache_root()/<song_key>/degradations.json` write at both exits, including the
  early-return checkpoints at `run.py:405,423`.
- [x] 2.3 Sweep `pipeline/run.py` (9 blocks) to the §2.2 targets (see design `## Notes`), including the
  `audio:stems` seam check (`if stems and not st.song_analysis.stems: note("audio:stems", ..., stage=
  "interpret")`).
- [x] 2.4 Sweep `pipeline/visual.py` (6) and `pipeline/groups.py` (5), including making `groups.py:43`
  (failed group *listing*) **re-raise** `XLightsConnectionError` instead of returning `[]`; update its
  docstring and the "returns []" caller contract.
- [x] 2.5 Sweep the remaining orchestrator files to the convention: `effect_emitter.py:84`
  (`emit:view`), `qa/coverage.py:31` (`qa:coverage-blind`, once-per-run flag on the closure),
  `weave.py:316`, `media.py`, `timing.py`, `finalize.py`, `triggers.py`, `lyrics.py`, `regen.py`,
  `revision_log.py` (level check only — do not report to the collector).
- [x] 2.6 Sweep `xlights-core` (convention only, no collector import): `audio/analyzer.py` ×4,
  `audio/extractors/stems.py` ×2, `audio/lyrics_align.py`, `knowledge/layout_semantics.py` ×2.
- [x] 2.7 Wire the core/orchestrator seam observations: `audio:stems` from `st.song_analysis.stems`
  emptiness; render-order from the discarded `bool` returns of `patch_view`/`patch_xsq_render_order`.
- [x] 2.8 Optional finalize-record field: add `degradations: list[str] = []` to `RevisionLogRecord`
  and populate at both finalize call sites (skip-gate and end-of-loop); keep old JSONL lines valid.
- [x] 2.9 Tests — new `tests/test_degradations.py`: `note()` with no active log is a no-op that still
  logs and never raises (raising fake detail); dedup (two `note("visual:critique", ...)` → one item,
  `count==2`, first detail kept); `render_summary()` empty vs non-empty; ContextVar isolation across
  two sequential `start_run()`s.
- [x] 2.10 Tests — pipeline integration (extend `test_orchestrator.py`): injected `visual_critique`
  fake that raises → finalize summary contains `visual:critique`×N and the run still completes; all
  fakes healthy → empty summary, `degradations.json` absent/empty. Per-block caplog tests for
  `qa/coverage` (blind warning exactly once across many `evaluate` calls) and `effect_emitter`
  (`emit:view` + fallback).
- [x] 2.11 Tests — `groups.py:43` re-raise: update `tests/test_targetable_groups.py` so a client whose
  `get_group_names` raises now propagates `XLightsConnectionError` (was `[]`); keep the probe-failure
  fallback tests unchanged. Add the structural log-audit test (AST walk: ban any `except Exception`
  whose body has no `log.`, no `note(`, no `raise`; auto-skip `server.py`/`brief_editor.py`).
- [x] 2.12 Back-compat + docs: golden pipeline snapshot byte-identical (logging-only edits);
  `ruff check` clean; document the taxonomy table + "reading a degradations summary" in `docs/usage.md`
  and add the project-convention note that new best-effort blocks must log.

## 3. F-I — live progress streaming UI

- [x] 3.1 Add `packages/xlights-orchestrator/src/xlights_orchestrator/progress.py`: `ProgressEvent`
  (frozen dataclass: seq, ts, type, stage, section, payload), `ProgressBus` (lock + append-only list +
  per-client `queue.Queue` fan-out; monotonic seq; `emit`/`subscribe(since)`/`unsubscribe`;
  `emit()` swallows-and-logs), and `NullProgressBus`. Pure stdlib, no pipeline imports.
- [x] 3.2 Inject the bus: add keyword-only `progress=None` to `run_pipeline` (run.py:320) and
  `_refine_loop` (run.py:135), resolved to `NullProgressBus()`; add the stage-level emits at the
  run.py seams, per-section emits via a wrapper loop in run.py (leaving `generate.py:234–261`
  untouched), refine emits inside `_record` (run.py:201) plus decision-point emits (skip-gate :211,
  plateau :238, revert :275, stall :297), and the terminal `done` after finalize.
- [x] 3.3 Add `CheckpointGate` (in `progress.py` or a sibling `checkpoints.py`) with `async wait(kind,
  body_md, options)` that registers a pending checkpoint, emits `checkpoint`, waits via `await
  asyncio.to_thread(self._q.get)`, and emits `checkpoint_resolved`; browser checkpoint factories
  mapping actions to the existing return contracts (`bool` for stage gates, `Decision` for refine).
  Add a `final_checkpoint` parameter to `run_pipeline` replacing the hardcoded `_final_approval` at
  run.py:481 (default preserves behavior).
- [x] 3.4 Add `live_server.py`: `LiveProgressServer(bus, gate, *, port=0)` on a daemon thread
  (`daemon_threads=True`), `start(open_browser=True)` returning the URL + `threading.Timer(0.4,
  webbrowser.open)`, `stop()`; handler factory routing `GET /` (page), `GET /events` (SSE: replay
  `subscribe(since=Last-Event-ID)`, then `q.get(timeout=15)` → `id:/data:` frames, `: hb` heartbeat on
  `queue.Empty`, unsubscribe on write error; omit `Content-Length`, set `text/event-stream` +
  `no-cache`), `POST /checkpoint/<id>` (validate id → 409 on stale; put action on the gate queue),
  `GET /revlog?tail=20`.
- [x] 3.5 Add the page: a `_PAGE`-style module constant + `render_page()` placeholder substitution
  (stdlib only, no external resources): stage timeline, per-section grid, inline-SVG QA sparkline +
  subscore bar row, revlog tail, checkpoint panel; one `EventSource("/events")` dispatcher keyed on
  `event.type`.
- [x] 3.6 CLI wiring in `cli.py::_run`: `--no-browser` flag; `live = not args.auto and not
  args.no_browser`; build real `ProgressBus`/`CheckpointGate`/started `LiveProgressServer` when live
  (route the browser checkpoint factories), else `NullProgressBus`/no server/no gate/today's
  injections; stdout mirror line with the URL on every pending checkpoint; `stop()` in a `finally`
  after emitting `done`.
- [x] 3.7 Tests — new `tests/test_progress.py`: emit/subscribe ordering, seq monotonicity,
  late-subscriber replay via `since`, fan-out to two queues, unsubscribe, emit-never-raises (poisoned
  subscriber queue), thread-safety (emit from N threads → correct count/order).
- [x] 3.8 Tests — pipeline emission (extend `test_orchestrator.py`/`test_refine.py`): pass a real
  `ProgressBus`, assert the event sequence (stage bracketing, one `section` per section, one `score`
  per refine iteration, `refine` payloads matching the captured `RevisionLogRecord`, `done` last);
  assert `progress=None` emits nothing and the golden snapshot is byte-identical.
- [x] 3.9 Tests — new `tests/test_live_server.py` (loopback, port 0): `GET /` contains the substituted
  page (no leftover placeholders); open `/events`, feed 3 synthetic events, parse frames (`id:`
  ordering, `data:` JSON, heartbeat after a small injected timeout); reconnect with `Last-Event-ID: 2`
  → replay starts at 3. Checkpoint round-trip: `gate.wait(...)` in a task → `checkpoint` event on the
  stream → `urllib`-POST `{"action":"proceed"}` → task resolves `True` + `checkpoint_resolved`; refine
  kind returns a proper `Decision`; stale/unknown id → 409, pending checkpoint unconsumed.
- [x] 3.10 Tests — fallback: with no live gate wired, monkeypatch `builtins.input` and assert
  `_interpret_review`/`_design_review` still gate exactly as today; verify the page loads zero external
  resources (grep the page constant for `http`/`//` URLs). Docs — README run-mode matrix (attended+
  browser / attended+terminal / auto) + the URL line.

## 4. F-J — headless / preview-only iteration mode (spike)

- [ ] 4.1 Fixture prep: run the normal pipeline on one finished show with `--save-as`, finalize
  (media attached), and keep `<seq>.xsq`, `<seq>.fseq`, `xlights_rgbeffects.xml`,
  `xlights_networks.xml`, the staged MP3, and the revision log.
- [ ] 4.2 S1 — `scripts/spike_fj_fidelity.py` (spike-only): build `PreviewRenderer(fseq, rgb, net)` +
  `RealRender(save_as, duration_s)` against a live xLights with the fixture open; emit
  `fidelity_report.json` with per-section, per-group `{brightness_delta, lit_fraction_agreement,
  hue_distance}`; add a `--group-masks` debug mode writing per-group projected masks as PNGs.
- [ ] 4.3 S1 decision replay: re-run `qa.evaluate` with a sampler backed by each render path over the
  fixture's iteration history; count objective-score and keep/revert disagreements.
- [x] 4.4 S2 — re-grep `client.*` across `packages/xlights-orchestrator/src/` and
  `xlights_core/editing.py`; diff against the design's client-call inventory (11 methods → 9 REST
  commands); note any drift.
- [ ] 4.5 S3 — prototype xLights batch/CLI render on macOS, then Linux (AppImage + Xvfb): document the
  exact version + invocation; capture (a) exit behavior with no display, (b) the produced `.fseq`,
  (c) wall time; diff the `.fseq` byte/channel-for-channel against the REST render (numpy diff reusing
  `load_fseq`) and against the `renderAll`+`saveSequence` ~2s baseline.
- [x] 4.6 Confirm or refute the inference that `RealRender` never engages mid-run on media-less
  sequences — observed on a live run's logs.
- [x] 4.7 Land the durable artifact regardless of outcome: a checked-in fixture `.fseq` + layout pair
  (small — low channel count or truncated frames, optionally zstd) and a hermetic test running the
  coverage sampler + Tier-0-style metrics over it (seed of the CI eval suite). Hermetic unit tests for
  the script's pure parts (mask projection, delta metrics, `.fseq` diff) against a tiny synthetic
  `.fseq`.
- [x] 4.8 Optional fallback batching seam: cache `get_models()` per emit instead of per placement
  (pass a prefetched name set through `apply_instructions`), with a hermetic test using the existing
  fake-placement pattern.
- [x] 4.9 Write-up + go/no-go against the decision table: name the chosen follow-up (option (a)
  file-based emitter + `BatchRenderer` OpenSpec change; hybrid folded into I8; or fallback batching).
  Gate the live S1/S3 steps behind `XLO_LIVE=1`-style gating — never in CI.

## 5. Land

- [ ] 5.1 Each roadmap item lands as its own PR (branch per item); never commit to `main` directly.
- [x] 5.2 Run `openspec validate add-pipeline-operability --strict` (0 errors) and the full hermetic
  suite (`pytest -m "not live"`) + `ruff check`; confirm the golden pipeline snapshot is byte-identical
  under the null bus and the logging-only edits.
- [x] 5.3 Verify no new runtime dependency was added and the live page / progress surfaces load zero
  external resources; update `docs/usage.md` per items 1.10 / 2.12 / 3.10.
