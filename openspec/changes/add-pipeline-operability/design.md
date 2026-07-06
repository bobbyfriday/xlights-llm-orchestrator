## Context

This change bundles the four Horizon-4 "Operability & evaluation" roadmap items that harden and
observe a full pipeline run. They are independently landable but share seams and idioms, so they are
authored as one cluster.

**I2 — current state.** `xlights_core/exceptions.py` defines the taxonomy callers branch on:
`XLightsError` → `XLightsConnectionError` (nothing listening / transport failure, `client.py:92–97`),
`XLightsTimeout` (connect/read timeout, `client.py:90`), `XLightsNotImplemented` (HTTP 504
"not implemented", `client.py:118–122`), `XLightsResponseError` (any other non-200; carries
`status_code` + message) → `XLightsTargetMissing` (503 "target element" on addEffect, `client.py:124`)
and `XLightsUnsavedChanges` (504 disambiguated by message, `client.py:118`). `XLightsClient._request`
(`client.py:73`) maps `httpx.TimeoutException → XLightsTimeout`, `httpx.ConnectError →
XLightsConnectionError`, any other `httpx.HTTPError → XLightsConnectionError`. All mutations funnel
through `_mutate`, serialized on `self._write_lock` (an `asyncio.Lock`, `client.py:58`) with
`DEFAULT_WRITE_TIMEOUT = 300.0` (line 35). xLights reports operational errors as **503** (busy,
"Unknown model.", "No sequence open.") and overloads **504** for both not-implemented and
unsaved-changes — so "HTTP 5xx ⇒ retryable" is *wrong here*; the 5xx codes carry semantic,
non-transient meanings. LLM calls use PydanticAI 2.5.0 defaults; its `retries` setting governs
*output-validation* re-prompting, a different mechanism that must never be conflated with transport
retry (a schema failure repeats identically at full token cost). `agents/panel.py:130–145` runs
analysts under `Semaphore(3)`, `gather(return_exceptions=True)` returns the bare exception (losing the
analyst `key`), and `run_panel` raises `RuntimeError` only if *all* fail. `effect_emitter.apply_
instructions` catches only the semantic skip set `_SKIPPABLE = (PresetPlacementError,
XLightsTargetMissing, ValueError, KnobValueError, KeyError)` (line 16); transport errors abort the
whole emit (correct posture, brittle for a one-request blip).

**I5 — current state.** 45 `except Exception` blocks across 20 files (verified 2026-07-05):
12 fully silent (`pass`/bare fallback), 2 `debug`, 6 `info`, 17 `warning`, 4 re-raise (out of scope).
Distribution: 9 in `pipeline/run.py`, 6 in `pipeline/visual.py`, 5 in `pipeline/groups.py`, 4 in
`audio/analyzer.py`, 3 in `xlights-mcp/server.py` (out of scope), plus singles across
`lyrics.py` (×2), `stems.py` (×2), `layout_semantics.py` (×2), `revision_log.py`, `effect_emitter.py`,
`qa/coverage.py`, `timing.py`, `finalize.py`, `triggers.py`, `media.py`, `regen.py`, `weave.py`,
`brief_editor.py`, `agents/guide.py`, `lyrics_align.py`. Per-block targets are tabulated in `## Notes`
(I5 inventory) so nothing is lost. A run where stems, real render, and coverage sampling all failed
produces, at INFO, two mid-run lines and *zero* mention of coverage blindness, and nothing aggregates
them at the end.

**F-I — current state.** `brief_editor.py` (222 lines) is the stdlib-browser pattern to extend
("Stdlib only (http.server); no framework, no CDN"): a page-as-Python-string `_PAGE` (28–147) with
`render_page()` placeholder substitution (150–156), a handler factory `_handler(...)` (172–202) whose
`do_GET`/`do_POST /save` validate via `save_brief()` (159–169, atomic `.json.tmp` rename), and
`serve()` (205–222) binding `ThreadingHTTPServer(("127.0.0.1", port), …)` with `port=0`, opening the
browser via `threading.Timer(0.4, …)` (216), then blocking in `serve_forever()`. It never returns
edits to a running pipeline. `run_pipeline()` (run.py:320–486) is a sequential stage skeleton
(analyze / groups probe / interpret / design / generate / apply-render / refine / finalize) with
checkpoints injected as callables (`None` = no gate); `--auto` (cli.py:80) is read in exactly three
places (cli.py:27–29). The four blocking `input()` sites are `_interpret_review` (run.py:115),
`_design_review` (run.py:106), `_interactive_checkpoint` (run.py:96), `_final_approval` (run.py:120).
`qa/__init__.evaluate` returns a `QAReport` (objective/advisory scores, findings, subscores); `_record`
(run.py:201–209) already serializes a `RevisionLogRecord` — effectively the event stream F-I needs.

**F-J — current state.** Every run needs a live GUI xLights over REST (`XLightsClient`). The offline
`xlights_core.preview` (`fseq.py` `load_fseq`, `layout.py` `parse_controllers`/`parse_models`/
`model_world_pixels`, `render.py` `PreviewRenderer`) is an xLights-free *replayer* of an
already-rendered `.fseq`; it renders no *effects*. `RealRender` (visual.py:155) is the real xLights
export, gated by the media-attach quirk (`export_video_preview` crashes on a media-less sequence,
`client.py:258–260`); because the in-run sequence is always a media-less ANIMATION (media patched
offline at finalize, `finalize.py:26–33`), the guardrail returns `False` mid-run and both critique
and sampler already fall back to the offline renderer — i.e. **the refine loop's in-flight decisions
already run on offline renders today**; the live app's irreplaceable mid-run contribution is producing
the `.fseq`. The client-call inventory (§2.3 of the F-J doc) shows 11 distinct `XLightsClient` methods
→ 9 REST commands; only the once-per-layout targetability probe and `render_all` genuinely require the
live app. `finalize.py` is the existence proof that `.xsq` mutation is doable offline.

## Goals / Non-Goals

**Goals:**
- One transient-only retry primitive applied at three seams; the terminal failure keeps its original
  exception type so every existing `except`/`isinstance` path still works (I2).
- Zero fully-silent best-effort blocks; a per-run degradations summary that names what was lost and
  why, plus a machine-readable `degradations.json` (I5).
- An attended run is glanceable in a browser tab (stage/section/score/refine views) and its four
  approval checkpoints are answerable there without parking the event loop; `--auto` and every test
  see zero behavior change (F-I).
- An honest, evidence-backed answer to "what truly requires live xLights?" and a checked-in fixture
  `.fseq` + hermetic test that seeds CI full-pipeline evals (F-J).

**Non-Goals:**
- No new runtime dependencies; stdlib-first throughout (no `tenacity`, no web framework, no CDN).
- I2 does not retry schema/validation failures, auth/bad-request errors, xLights semantic 503/504, or
  `render_all`/`export_video_preview`; it does not touch `lyricsgenius`'s internal `retries=1` or
  PydanticAI's output-validation retries.
- I5 does not change any run artifact except adding `degradations.json` (and optionally a defaulted
  revision-log field); it is logging-only except the single `groups.py:43` re-raise.
- F-I does not add a dual stdin+browser race, does not persist the event stream, and does not embed
  the brief editor into the checkpoint in v1.
- F-J ships **no** shipped headless feature: it is a spike + a fixture test (+ an optional batching
  seam). Reimplementing the xLights render engine in Python is rejected without a spike task.

## Decisions

**1. Retry primitive lives in `xlights-core`, is callable-wrapping, and has no third-party dep.**
`with_retry(fn, *, retryable, attempts=3, base_delay=1.0, factor=2.0, max_delay=20.0, jitter=0.5,
label="")` runs `fn()`, and on a retryable exception sleeps exponential backoff with a full ±50%
jitter band and re-runs up to `attempts`; non-retryable and final failures propagate unchanged; each
retry logs WARNING with label, attempt count, and cause. Placed in core (bottom of the dependency
graph) so the orchestrator can reuse it for LLM calls. *Rationale:* ~30 lines, stdlib-first house
style; callable-wrapping (`await with_retry(lambda: agent.run(prompt), …)`) keeps the retry visible at
the seam and does not wrap injected fakes invisibly. *Alternatives:* `tenacity` (rejected — decorator
indirection fights the injected-fake test pattern and adds a dependency); decorating call sites
(rejected — hides the seam, wraps fakes). Defaults 3/1s/2×/20s ⇒ worst-case added latency ≈3–4.5s per
call, negligible against LLM latency and the 300s write timeout. Full jitter because the panel
launches 3 analysts near-simultaneously and synchronized retries would re-collide on the same
rate-limit window. Constructor knob `retry_attempts: int = 3` on the client (0/1 disables for tests).

**2. Retryable-vs-non-retryable is an explicit, unit-tested classification, not "5xx ⇒ retry".**
LLM: retry `ModelHTTPError` with `status_code in {408,429,500,502,503,529}` and
`httpx.TimeoutException`/`ConnectError`/`RemoteProtocolError` escaping the provider; never retry
`UnexpectedModelBehavior`, `ModelHTTPError` 400/401/403/404/413/422, `UsageLimitExceeded`,
`ContentFilterError`, `pydantic.ValidationError`. xLights: reads retry on `XLightsConnectionError` and
`XLightsTimeout`; mutations retry on `XLightsConnectionError` only; never retry `XLightsNotImplemented`,
`XLightsTargetMissing`, `XLightsUnsavedChanges`, or generic `XLightsResponseError`. Genius unchanged.
*Rationale:* rate-limit/overload/timeout are time-correlated and clear on their own; schema/auth
failures repeat identically and re-bill full input tokens; xLights' 5xx are semantic state, not
transport. *Alternative weighed:* retrying a "busy" `XLightsResponseError` by message string — rejected
in v1 because message strings are not a stable API; extend the predicate later with logged evidence
(the I5 summary will surface which errors actually occur). The two predicates live next to their
taxonomies: `xlights_transient()` in core; `llm_transient()` in the orchestrator (owner of the
`pydantic_ai` dependency), isolated in one function so a PydanticAI rename fails a test, not a run.

**3. LLM retry is applied via one `run_agent()` wrapper, per-site attempt counts.** Rather than
editing all seven call sites, `models/registry.py` gains `run_agent(agent, prompt, *, role,
attempts=3)`. Director (`run.py:415`), synthesizer (`panel.py:158`), generator (`generate.py:158`),
judge (`run.py:229`) → attempts=3 (failure aborts a run/section, or the judge escapes `_refine_loop`).
Panel analysts (`panel.py:135`) → attempts=2 (roadmap "retry once before being dropped"; the drop path
is the backstop, retry stays inside the `Semaphore(3)`). Visual critic (`visual.py:94`) and section
redesigner (`run.py:163`) → attempts=2 (already under best-effort guards; one retry turns "advisory
lost this iteration" into "usually fine"). *Rationale:* one instrumentation home also collapses I1's
telemetry to a single point. Fakes never raise transient classes ⇒ single attempt, identical behavior.

**4. xLights retry wraps the transport boundary inside the client, and mutation retry is
connection-only inside the lock.** Add `_request_with_retry`; route reads with `xlights_transient`;
change `_mutate` to retry on `XLightsConnectionError` only, **holding the write lock across the
backoff**. *Rationale for lock-hold:* the lock enforces "one shared open sequence"; interleaving
another mutation between a failed attempt and its retry could change the open-sequence state the
retried command assumes (a `closeSequence` sneaking between two `addEffect` attempts). Bounded ≤~4.5s
vs the 300s write timeout. *Rationale for connection-only:* an `XLightsTimeout` after a mutation is
ambiguous (the `addEffect` may have landed but lost its response; retry could double-place via
`_free_layer` stacking). `httpx.ConnectError` proves the request never reached xLights.
`render_all`/`export_video_preview` are excluded entirely (long-running; a timeout means "still
rendering"; re-issuing piles work on the app). `effect_emitter.apply_instructions` and
`groups._probe` need no change — their skip-vs-abort semantics sit above the now-self-healing
transport. *Alternative rejected:* retrying outside the lock (breaks ordering).

**5. Split the catch-all transport mapping so "provably never sent" is precise.** `client.py:96`
currently maps any `httpx.HTTPError → XLightsConnectionError`, conflating "never sent" with "sent,
response lost". Introduce `XLightsTransportError(XLightsConnectionError)` for the sent-but-failed case
so existing `except XLightsConnectionError` callers keep catching both, and the mutation predicate can
require the provably-unsent case. *Alternative:* a boolean `request_sent` attribute (less clean;
subclass chosen).

**6. The panel drop names the analyst and can report to the collector.** Pair each `gather` result
with its spec via `zip(analysts, results)` (gather preserves input order) so the WARNING names the
lost analyst key; the terminal loss also calls `degradations.note("refine:analyst-drop", …)` once I5
lands. Retry stays inside the semaphore so concurrency never exceeds 3.

**7. One logging convention applied 45 times; silent `pass` is banned.** `log.debug("<what>
skipped/fallback: %s", exc)` for cosmetic degradations (cache miss/write, per-call fallback inside an
already-reported capability, expected recompute); `log.warning("<capability> lost: %s", exc)` (or
`degradations.note(...)`) when a whole capability is gone. INFO is reserved for *positive* progress, so
`grep -i warning` over a run log is a complete degradation list even without the collector. Keep the
repo's `# noqa: BLE001 — <reason>` convention on the `except` line. Every block logs at least DEBUG
with the exception value. *The full per-block target table is preserved verbatim in `## Notes`.*

**8. The degradations collector is a ContextVar, best-effort, with a closed taxonomy.**
`xlights_orchestrator/degradations.py`: `Degradation(capability, detail, count=1, stage=None)`,
`DegradationLog` (dict keyed by capability → dedup, `note`, `summary`), a ContextVar `_current`,
`start_run()`/`current()`, and a module-level `note(capability, exc_or_detail, *, stage=None,
level=WARNING)` that logs AND records in one call and is itself wrapped in `except Exception →
log.debug` (observability must never break a run, mirroring `RevisionLog.write`). *Closed capability
taxonomy* (docstring; free-form keys would defeat dashboard aggregation): `audio:lyrics`,
`audio:stems`, `audio:instrumental-refine`, `groups:probe`, `emit:view`, `qa:coverage-blind`,
`qa:render-flush`, `visual:critique`, `visual:real-render`, `visual:fseq-metrics` (reserved for
add-cost-and-evaluation's deterministic Tier-0 fseq-metrics skip site), `refine:redesign`, `refine:analyst-drop`,
`generate:triggers`, `finalize:media`, `finalize:timing-tracks`, `finalize:xsq-patch`,
`cache:post-refine`. *Alternative weighed:* merging with I1's `UsageLog` into one `runinfo.py` —
deferred (keep separate modules, extract a shared `_ContextCollector` only if a third collector
appears). Stage attribution is passed explicitly per call site (zero magic) rather than via a stage
ContextVar.

**9. End-of-run summary + `degradations.json`, installed at the two pipeline entry points.**
`start_run()` at the top of `run_pipeline()` and `regen_section()`; a summary block (WARNING when
non-empty — a degraded run should end loudly, INFO "no degradations" otherwise) + a best-effort
`cache_root()/<song_key>/degradations.json` write at *both* exits, including the early-return
checkpoints at `run.py:405,423`. Optional cheap tie-in: `RevisionLogRecord` gains `degradations:
list[str] = []` (capability keys only; backward-compatible default). The summary sits beside
`revision_log.jsonl` and I1's `usage.json` so F-G can correlate expensive × degraded × low-score runs.

**10. Core/orchestrator boundary rule for I5.** `xlights-core` must not import the orchestrator
collector (dependency direction) and does not grow its own; core blocks get the *convention* only. The
orchestrator reports core-owned capabilities by observing outcomes at the seam it already sees:
`audio:stems` from `st.song_analysis.stems` emptiness after analyze; `audio:lyrics` from the existing
`run.py:367` block + "still no lines" at :371; render-order from the `bool` returns of `patch_view`/
`patch_xsq_render_order` that finalize currently discards.

**11. `groups.py:43` (failed group *listing*) re-raises; a structural audit test enforces "no silent
swallows".** A failed *listing* has no useful degraded mode (empty `available_groups` poisons the
Director prompt "choose from: nothing" and produces a garbage cached brief, after paying analysis +
panel + director tokens); raising `XLightsConnectionError` early fails before any LLM spend. A failed
*probe* (line 62) keeps its sane full-list fallback. A cheap AST-walk test bans any `except Exception`
whose body contains neither a `log.` call, a `note(` call, nor a `raise` (auto-skips the `server.py`/
`brief_editor.py` re-raise patterns). *Other re-raise candidates* (`run.py:440`/`regen.py:128`
`get_show_folder`, `run.py:178` render flush, `effect_emitter.py:84` view fallback) stay best-effort
with warning + collector; the summary exists to inform a later re-raise decision.

**12. F-I progress bus is injected, not module-level, and never breaks a run.** `ProgressEvent(seq,
ts, type, stage="", section=None, payload={})` with `type ∈ {stage, section, score, refine,
checkpoint, checkpoint_resolved, log, done}`; `ProgressBus` (lock + append-only list + per-client
`queue.Queue` fan-out; `emit()` swallows-and-logs like `RevisionLog.write`); `NullProgressBus` twin.
Add keyword-only `progress=None` to `run_pipeline`/`_refine_loop`, resolved `progress = progress or
NullProgressBus()` (the `revlog = revlog or NullRevisionLog()` idiom). `--auto` and every test pass
nothing → zero behavior change; the golden pipeline snapshot must be byte-identical. Emits land at the
existing seams enumerated in `## Notes` (F-I emission map); per-section emits use a wrapper loop in
run.py so `generate.py` stays untouched; refine emits live inside `_record` so the SSE stream and
revision log can never disagree.

**13. SSE over long-poll for the live server.** New stdlib-only `live_server.py`:
`LiveProgressServer(bus, gate, *, port=0)` on a daemon thread (`daemon_threads=True`), `start()` opens
the browser via `threading.Timer(0.4, …)` and returns the URL, `stop()` = `shutdown()` +
`server_close()`. Routes: `GET /` (the page), `GET /events` (SSE: replay `bus.subscribe(since=
Last-Event-ID)`, then loop `q.get(timeout=15)` → `id: {seq}\ndata: {json}\n\n`, heartbeat `: hb\n\n`
on `queue.Empty`, unsubscribe on write error), `POST /checkpoint/<id>`, `GET /revlog?tail=20`.
*Rationale:* on localhost with one viewer, SSE's only cost (a pinned thread per client) is negligible
and it deletes the entire client-side polling machinery in exchange for ~15 lines of handler loop;
built-in `EventSource` gives auto-reconnect + `Last-Event-ID` replay for free. *Alternative:*
long-poll (more robust across proxies we don't have; more client machinery). SSE responses omit
`Content-Length` and set `text/event-stream` + `no-cache`.

**14. `CheckpointGate` replaces the blocking `input()` without parking the loop; terminal fallbacks
stay wired.** The pipeline registers a pending checkpoint and emits a `checkpoint` event
`{id, kind, body_md, options}`; the UI shows approve/edit; `POST /checkpoint/<id>` validates the id
(stale → 409) and puts the action on the gate's `queue.Queue`; the pipeline waits via `action = await
asyncio.to_thread(self._q.get)` (thread-safe, does *not* park the event loop, unlike raw `input()`),
maps the action to the existing return types (`bool` for stage gates, `Decision` for refine), and
emits `checkpoint_resolved`. Browser factories (`browser_interpret_review`, etc.) share today's
signatures. `_interpret_review`/`_design_review`/`_interactive_checkpoint`/`_final_approval` stay in
run.py and remain the wired defaults for `--no-browser`, `--auto`, or a failed server bind; each
`checkpoint` event is mirrored to stdout with the URL. A `final_checkpoint` parameter replaces the
hardcoded `_final_approval` at run.py:481 (default preserves behavior). *Alternative rejected:* dual
stdin+browser race (two authorities for one decision invites lost answers).

**15. CLI wiring keeps `--auto` untouched by construction.** In `cli.py::_run`, `live = not args.auto
and not args.no_browser`; when live, build a real `ProgressBus`, `CheckpointGate`, and started
`LiveProgressServer` and route the browser checkpoint factories; otherwise `NullProgressBus`, no
server, no gate, and today's `None`/`_auto_checkpoint` injections. New `--no-browser` flag reproduces
today's terminal-only attended behavior byte-for-byte. Server `stop()` in a `finally` after emitting
`done`.

**16. F-J is a decision-first spike; option (a) is the only true headless path and is gated on
evidence.** Three options weighed: (a) xLights batch/CLI render behind the existing `emitter=`
injection seam — the only true headless path, but with the hidden cost of reimplementing
`addEffect`-side validation as `.xsq` writing (M–L even on a "yes"); (b) reimplement effect rendering
in Python — **rejected without a spike task** (unattainable/harmful parity against the upstream C++
engine, the very ground truth the offline replay is measured against); (c) hybrid — cache one live
render per look-generation, iterate offline on the cached `.fseq` (works for reads/QA/critique/judge;
cannot make the *current* refine loop headless because every accepted revision regenerates
instructions and needs a re-render). The spike (S1 fidelity report, S2 client-call re-inventory, S3
prototype CLI render on macOS then Linux/Xvfb) ends at the decision table in `## Notes`; two cheap
wins land regardless: CI evals on a checked-in fixture `.fseq`, and optional fallback batching (cache
`get_models()` per emit instead of per placement). *Decision criteria and full spike protocol are
preserved verbatim in `## Notes`.*

## Risks / Trade-offs

- [I2: retrying a non-idempotent xLights mutation double-applies it] → Mutations retry only on
  `ConnectError` (provably unsent); timeouts surface immediately; `render_all`/export excluded.
- [I2: backoff inside the write lock stalls other writers] → Bounded ≤~4.5s vs the existing 300s write
  timeout; the alternative (retry outside the lock) breaks ordering — chosen deliberately.
- [I2: retries mask a persistently sick provider/xLights, tripling time-to-failure] → attempts hard-
  capped at 3; every retry logs WARNING with cause; terminal failure unchanged in type and content.
- [I2: rate-limit retry storms across concurrent analysts] → full jitter; retries stay inside
  `Semaphore(3)`; analysts get only 2 attempts.
- [I2: PydanticAI exception surface shifts between versions] → predicate isolated in one function with
  direct unit tests constructing real exception instances; a rename fails a test, not a run.
- [I2: `run_agent` wrapper changes fake-agent call counts in existing tests] → fakes never raise
  transient classes ⇒ single attempt; verified by running the suite unmodified.
- [I5: the collector itself fails and takes a run down] → `note()` is internally best-effort
  (`except Exception → log.debug`); summary emission and JSON write sit in their own guard.
- [I5: `groups.py:43` re-raise breaks a flow relying on the empty-list limp-through] → the only caller
  stores the list and would fail at emit anyway; test-pinned; an empty list from a *successful* call
  still returns normally.
- [I5: warning fatigue for per-iteration capabilities] → the collector dedupes with counts; a first-
  occurrence-WARNING/subsequent-DEBUG knob is left out of v1 deliberately.
- [I5: capability-key taxonomy drifts (typos → phantom capabilities)] → keys are module-level
  constants (a `Literal` once I4's mypy gate lands).
- [I5: double-reporting once I2 lands (retry warning + drop warning + collector note)] → retries log
  their own WARNINGs; only the *terminal* loss calls `note()`.
- [F-I: blocking the asyncio loop while waiting on a browser action] → `await asyncio.to_thread(
  queue.get)` in `CheckpointGate.wait`; bus emit is plain thread-safe code callable from any thread.
- [F-I: operator closes the tab and the run waits forever] → stdout mirror line with the URL on every
  `checkpoint` event; page reopen replays via Last-Event-ID + `/revlog`.
- [F-I: SSE handler thread leaks after disconnect] → ~15s heartbeat forces a write; `BrokenPipeError`/
  `ConnectionResetError` ends the handler and unsubscribes; `daemon_threads=True` guarantees exit.
- [F-I: event payload drift vs the revision log] → refine events emitted inside `_record` from the
  same `RevisionLogRecord` fields; one construction site.
- [F-I: behavior change for `--auto`/tests/cached runs] → explicit injection with `NullProgressBus`
  default; golden test unchanged; `--auto` wiring untouched.
- [F-I: port collisions / concurrent runs] → port 0 everywhere; each run prints its own URL. Security:
  bind 127.0.0.1 only; checkpoint ids are single-use random tokens; no state-changing GET routes.
- [F-J: xLights CLI render doesn't exist / crashes headless on Linux] → a valid spike outcome; the
  fallback batching and fixture-based CI evals still land; re-check on future releases.
- [F-J: CLI render produces a subtly different `.fseq`] → byte/channel diff is S3's hard gate; anything
  beyond ≤1 LSB fails option (a).
- [F-J: fidelity gap is scene-dependent] → report per-group/per-section deltas, require agreement on
  *decisions* (lit-fraction, keep/revert), not pixel equality.
- [F-J: writing effect XML bypasses `addEffect` validation] → keep the once-per-layout live probe; add
  an offline structural validator; consider file-based `checkSequence` as a post-write lint.
- [F-J: macOS `SANDBOX_DATA` pathing breaks off-macOS] → `resolve_artifact` already falls back to the
  show folder; S3 verifies where a Linux build writes.
- [F-J: spike scope creep into building the emitter] → the spike ends at the decision table; the
  implementation is a separate OpenSpec change.

## Migration Plan

All four items are backward-compatible and independently landable. I2 preserves every exception type
(no caller changes) and is disable-able via `retry_attempts=0/1`. I5 is logging-only except the one
`groups.py:43` re-raise (test-pinned) and adds only a new `degradations.json` artifact and an optional
defaulted `RevisionLogRecord.degradations` field (old JSONL lines still validate). F-I is inert under
the `NullProgressBus` default; `--auto`, `--no-browser`, and every existing test reproduce today's
behavior byte-for-byte. F-J ships no production behavior change — only a spike, a checked-in fixture +
hermetic test, and an optional `get_models` prefetch seam. Order within the cluster: I5 and I2 pair
(retry WARNINGs feed the summary); F-I benefits from I5's `log` events; F-J is independent.

## Open Questions

- **I2** — Env knobs (`XLO_RETRY_ATTEMPTS`/`XLO_RETRY_BASE`) or constants-first? Leaning constants.
  Honor Anthropic's `retry-after` header (in `ModelHTTPError.body`) for 429s in v1, or defer until
  telemetry shows 429s occur? Should the generator retry budget differ during refine (fail-fast is
  current behavior — keep, revisit with I5)? Should `save_sequence` in best-effort blocks retry
  (inherit the mutation policy — connection-only — and measure)?
- **I5** — Merge with I1's collector into `runinfo.py`? (keep separate). Should attended checkpoints
  print degradations-so-far so a human can abort a stems-less run before paying for generation?
  (cheap once the collector exists; F-I is the eventual home). A third severity tier? (the capability
  key implies it — keep two). Promote `run.py:440` to re-raise after N observed `finalize:media`
  occurrences? (record the decision rule; the data collection has a purpose).
- **F-I** — Markdown rendering of checkpoint bodies (`<pre>` vs a ~40-line subset renderer vs link the
  on-disk `.md`; lean subset renderer, shared with the revlog tail). Embed the brief editor in the
  design checkpoint (defer — mutating `st` mid-checkpoint fights the instructions cache). Should
  `ProgressEvent` carry I5 degradation and I1 token payloads now or later (the `type`+`payload` shape
  is open-ended; let I1/I5 add theirs). Persist `bus._events` to `progress.jsonl` (deferred).
- **F-J** — Does REST `batchRender` render *saved* sequences without opening them, a lighter path than
  the CLI? Can `renderAll` be scoped to a time range / model set? Where does a Linux xLights write the
  `.fseq`? Is the targetability cache portable across platforms/installs? If option (a) lands, is REST
  the attended-mode default with headless opt-in, or the single path? Max CI fixture `.fseq` size
  before repo bloat (truncate frames / reduce channels / zstd)?

## Notes

Overflow bucket so no source-doc detail is dropped.

### I5 — full per-block target inventory (from the I5 doc §2.2)

`pipeline/run.py` (9): `:178` render flush before QA sampling — silent `pass` → **warning + collector
`qa:render-flush`**; `:227` `visual_critique` — warning → **keep + `visual:critique`**; `:264`
`_redesign` escalation — warning → **keep + `refine:redesign`** (section index in detail); `:367`
`fetch_lyrics`/`attach_lyrics` — info → **warning + `audio:lyrics`**; `:376` `refine_instrumental` —
info → warning+collector only when the song had no timed lines; `:383` `song_analysis` cache write —
info → **debug**; `:395` cached `MusicBrief` validate — silent → **debug** ("stale cache,
recomputing"); `:440` `get_show_folder` — silent → **warning + `finalize:media`** (re-raise candidate);
`:476` persist revised brief/instructions — warning → **keep + `cache:post-refine`**.

`pipeline/visual.py` (6): `:44` `_persist_bundle` — warning → **debug** (cosmetic); `:65`
`save_sequence`/`get_show_folder` in `_vc` — info → **warning + `visual:critique`**; `:75`
`PreviewRenderer(...)` init — warning → **keep + `visual:critique`**; `:151` `_ffprobe_duration` —
silent → **debug**; `:188` `RealRender.refresh` — info → **warning + `visual:real-render`**; `:198`
`_ff` frame/clip extraction — silent → **debug**.

`pipeline/groups.py` (5): `:43` `get_group_names` — warning → **re-raise** (§ decision 11); `:50`
`get_model_names` — silent → **debug**; `:57` cache read/parse — silent → **debug**; `:62`(+`:66`)
`_probe` setup / non-target errors — warning → **keep + `groups:probe`**; `:93` `close_sequence` of the
probe seq — silent → **debug**.

Remaining orchestrator: `revision_log.py:112` — keep (do NOT report to the collector — it must never
depend on the log path it feeds); `effect_emitter.py:84` default-view fallback — silent → **warning +
`emit:view`**; `lyrics.py:37` tag read — keep debug; `lyrics.py:69` Genius fetch — keep + `audio:
lyrics`; `qa/coverage.py:31` coverage neutralized to 100 — silent → **warning + `qa:coverage-blind`**
(once per run, guard with a flag — the sampler is called many times); `timing.py:185` — keep +
`finalize:timing-tracks`; `finalize.py:39` — keep + `finalize:xsq-patch`; `triggers.py:294` — keep;
collector only if ≥1 detector failed (`generate:triggers`, aggregated); `media.py:101` — keep +
`finalize:media`; `regen.py:128` — silent → **warning + `finalize:media`**; `weave.py:316` LTR
direction — silent → **debug**; `agents/guide.py:39` — keep debug; `brief_editor.py:200` — out of scope
(reports HTTP 400).

`xlights-core` (convention only, no collector): `audio/lyrics_align.py:129` — info → **warning**;
`audio/analyzer.py:110,124` cache writes — silent → **debug** ×2; `:142` section-instrumentation — silent
→ **debug**; `:180` stem not persisted — keep warning; `audio/extractors/stems.py:46` per-backend — keep
warning (orchestrator detects terminal all-backends case via `sa.stems` emptiness → `audio:stems`);
`:76` device detection → CPU fallback — silent → **debug**; `knowledge/layout_semantics.py:171,208`
`patch_view`/`patch_xsq_render_order` — keep warning ×2 (callers return `False`; finalize's collector
entry covers the run level). `xlights-mcp/server.py:205,209,220` — out of scope (re-raised as
`RuntimeError` tool errors).

End-of-run summary shape (rendered via `log.warning` when non-empty, `log.info` "no degradations"
otherwise):

```
== degradations (3) =====================================
  audio:stems          all separation backends failed: demucs-mlx: ... (×1, interpret)
  visual:real-render   real render unavailable: export_video_preview ... (×3, refine)
  qa:coverage-blind    no .fseq for 'MyShow' (×1, refine)
=========================================================
```

### F-I — progress emission map (from the F-I doc §3.1)

`stage` start/end bracketing each numbered stage of `run_pipeline`: analyze (run.py:350–353; payload
duration_s, stems, section count), groups probe (:386; group count, cache hit), interpret (:391–400;
cached bool), design (:409–418; sections, cached), apply (:446; placed/skipped from `st.applied`),
finalize (:483–485; then terminal `done`). `checkpoint`/`checkpoint_resolved` at the interpret gate
(:403–405, body=desc_md), design gate (:419–423, body=brief_md), and the refine checkpoint (:229–231).
`section` per generate iteration (generate.py:239–240; via a wrapper loop in run.py to leave
generate.py:234–261 untouched), per design escalation (:252–265; escalated=true, findings count), per
revision (:266–267; section=rev.section_index, issue). `score` on `report = await _report(...)`
(:223; objective/advisory + subscores + top findings — the sparkline feed) and at final report (:304).
`refine` for the skip-high-objective gate (:211–216), Judge verdict + decide (:229–231), plateau
(:238–242), revert/keep branch mirroring `RevisionLogRecord` (:275–296; cleanest tap: inside/alongside
`_record` at :201), stall stop (:297), finalize record (:304–305). Page regions: stage timeline,
per-section grid (count from the design stage-end payload; look as tooltip), SVG `<polyline>` QA
sparkline + subscore bar row rebuilt client-side, revlog tail (`refine` events + `GET /revlog`
catch-up), checkpoint panel (hidden until a `checkpoint` event). Checkpoint kinds/buttons: interpret/
design → Proceed/Stop; refine → Approve revisions/Stop/Keep as final (mirrors the `[A/s/k]` prompt at
run.py:96); final → Save/Discard.

### F-J — spike protocol, decision criteria, and fidelity option analysis (from the F-J doc)

**Spike steps.** S1 — measure the offline-vs-real fidelity gap on one finished, media-attached
fixture show: `RealRender.refresh()` → house-preview MP4; per section sample N=8 beat-aligned
timestamps + `brightest_frame_ms`; render each both ways (`PreviewRenderer.render_frame(t)` and
`RealRender.frame_png(t)`, offset-corrected); compute per-frame global + per-group deltas (per-group
masks from projecting each group's member-model pixels through the renderer's `_project()`): mean
brightness delta, lit-fraction agreement at the sampler's `>30` threshold, hue-histogram distance;
emit `fidelity_report.json` per fixture. S1 decision replay — re-run `qa.evaluate` with a sampler
backed by each render path over the fixture's iteration history; count objective-score and keep/revert
disagreements. S2 — re-grep `client.*` across the orchestrator + `editing.py`; diff against the
inventory (11 methods → 9 REST commands). S3 — prototype xLights batch/CLI render on macOS then Linux
(AppImage + Xvfb): discover the actual CLI flags, render the S1 fixture's `.xsq`, compare the `.fseq`
byte/channel-for-channel against the REST render, time it against `renderAll`+`saveSequence` (baseline
"~2s" for `renderAll`), and test whether it runs with no display at all.

**Decision table.** S3 headless render works on Linux (Xvfb ok) AND `.fseq` byte-identical or ≤1 LSB
per channel AND wall time ≤2× REST `renderAll` → **option (a)**: file-based emitter + `BatchRenderer`
behind the existing `emitter=` seam (`run_pipeline(..., emitter=...)`, run.py:328); live xLights only
for the once-per-layout probe (pre-seeded cache in CI). S1 per-group lit-fraction decisions agree ≥95%
and deltas small enough that keep/revert outcomes match → **hybrid viable** for inner iterations
(offline eval + batched renders, one real-render gate before finalize; shares I8 Tier-0 code). S3 fails
and S1 gap large → **fallback**: keep live xLights, batch the interactions (cache `get_models()` per
emit instead of per placement — halves emitter round-trips on ~270 placements; investigate
section-scoped renders).

**Option (b) rejected without a spike task:** reimplementing the xLights render engine (hundreds of
effect types, value-curve DSL, per-model vs per-preview buffer styles, layer blend modes, transitions,
group-canvas rendering, per-version C++ drift) — exact parity unattainable, approximate parity worse
than useless because the render *is* the ground truth the offline replay is measured against.

**Hybrid offline-support analysis** (`.fseq` is a flat `[frames, channels]` array with effects baked
in): QA/objective score, I8 Tier-0 metrics, offline critique stills/clips, judge/checkpoint decisions
— **yes** (pure reads). Muting/dimming a group or window — **partial** (zero/scale the channel range,
but layered effects on the same target are baked together). Time-shifting a section — **partial**
(frame-slice copy; motion discontinuities at boundaries). Retargeting a look to a different group —
**mostly no** (ignores geometry/buffer). New effects / changed knobs / palette / buffer-style /
section regeneration — **no** (all require the render engine, and section regen is exactly what
`_refine_loop`/`regenerate_section` does). The two cheap wins regardless of S3: check in one rendered
fixture (small — low channel count or truncated frames, optionally zstd) and run QA + Tier-0 metrics
+ judge hermetically over it; and the `get_models` prefetch batching seam (a one-line change passing a
prefetched name set through `apply_instructions`).

### I2 — other detail preserved

`with_retry` full signature and defaults (attempts=3, base_delay=1.0, factor=2.0, max_delay=20.0,
jitter=0.5). Predicate helper bodies: `xlights_transient(exc)` = `isinstance(exc,
(XLightsConnectionError, XLightsTimeout))`; `_TRANSIENT_HTTP = {408, 429, 500, 502, 503, 529}`,
`llm_transient(exc)` = `ModelHTTPError.status_code in _TRANSIENT_HTTP` else `isinstance(exc,
(httpx.TimeoutException, httpx.TransportError))`. Implementation plan order: (1) `retry.py` +
`xlights_transient` + export from `__init__`; (2) client `_request_with_retry`, route reads, mutation
connection-only predicate, exempt render/export, `retry_attempts` knob; (3) split the transport
mapping (`XLightsTransportError`); (4) `llm_transient` + `run_agent` + predicate unit tests; (5) route
the seven call sites (dovetails with I1's telemetry split); (6) panel §3.5; (7) docs. `lyrics.py`
stays untouched (double-retry avoidance; note the asymmetry in the module docstring). PydanticAI's
output-validation `retries` and best-effort `except Exception` blocks are untouched (the latter are
I5's subject).
