## Context

A flight-recorder for the refine loop so we can tune prompts with real data instead of vibes. Everything it records is already computed in `pipeline/run.py` (the QAReport, the appended `visual:*` findings, the JudgeVerdict, the `decision`/`verdict` revisions, the `floor_visual_revisions` backstop output, `obj` before/after + the revert branch, the human `Decision`, the registry models, and the ⑧ visual-review-bundle dir). This change adds a typed record + an append-only JSONL writer and emits one record per iteration — strictly write-only.

## Goals / Non-Goals

**Goals:** a durable, append-only, per-iteration record (findings-by-source, Judge verdict, revisions tagged Judge-vs-backstop, objective before/after/reverted, human decision, model snapshot, review-bundle pointer); injectable + disable-able; pure observability; hermetic tests.

**Non-Goals:** analytics/dashboards/query/aggregation, fine-tuning/eval harnesses; Logfire/operational telemetry; changing refine behavior; logging analyze/interpret/design phases.

## Decisions

### `RevisionLogRecord` (pydantic) + append-only JSONL
A small model in `revision_log.py`:
```
RevisionLogRecord{
  run_id: str; iteration: int; song_key: str; ts: str; kind: "iteration"|"finalize"
  objective_score: int; advisory_score: int
  findings: list[{source: str, severity: str, scope: str, section_index: int|None, detail: str}]
  judge: {score: int, verdict: str} | None
  revisions: list[{section_index: int, issue: str, origin: "judge"|"backstop"}]
  regenerated_sections: list[int]
  obj_before: int|None; obj_after: int|None; obj_delta: int|None; reverted: bool
  human_decision: str|None            # approve/redirect/stop/accept when attended
  models: dict[str,str]               # role -> "provider:model" snapshot
  review_bundle: str|None             # path to that iteration's visual_review/<iter>/
}
```
`source` is derived from `Finding.metric` (e.g. `visual:coverage` → `visual`; `sync`/`placement`/`variety` stay as-is). Serialized one-per-line via `model_dump_json()` to `data/orchestrator/<song_key>/revision_log.jsonl` (append mode). Append-only JSONL (not a single JSON array) so a crashed/long run never corrupts prior records and the file is greppable/streamable.

### Injectable `RevisionLog` writer — JSONL (canonical) + Markdown (human view)
```
class RevisionLog:        # default — file-backed, writes BOTH
    def __init__(self, jsonl_path, md_path): ...
    def write(self, record: RevisionLogRecord) -> None:
        append record.model_dump_json()+"\n"  to jsonl_path        # canonical
        append _render_md(record)             to md_path           # human view
class NullRevisionLog:     # no-op (tests, --no-log)
    def write(self, record): pass
```
Passed into the refine loop like `visual_critique` (keeps the loop hermetic). `run_pipeline` builds the default `RevisionLog(<key>/revision_log.jsonl, <key>/revision_log.md)` when refine + logging are on, else `NullRevisionLog`. A `--no-log` CLI flag selects the null writer. The JSONL is canonical; the `.md` is a convenience rendering of the **same** record (a crash mid-run leaves the `.md` possibly short but the JSONL intact — JSONL is source of truth).

### Human-readable rendering (`_render_md(record)`)
A pure function record→Markdown so it's unit-testable and consistent with the JSONL. One section per iteration, appended under a run header:
```
## Run <run_id> · iteration N · <ts>
**Scores:** objective 72 → 78 (+6, kept) · advisory 60
**Flagged:**
- [error · visual:coverage] section 2 — chorus dark despite 0.9 intensity
- [warn · sync] section 3 — builds rather than fades
**Judge (78, iterate):**
- section 2 (judge) — light the chorus to match the peak; brighter/fuller/dynamic
- section 1 (backstop) — visual defect for this moment; regenerate to fit the music
**Regenerated:** 2, 1  →  objective +6 (kept)
**Human:** approve   ·   **Frames:** visual_review/iter1/   ·   **Models:** judge=anthropic:claude-opus-4-8, …
```
Origin (`judge`/`backstop`) is shown inline so a reader sees *why* each change happened and whether the safety net fired. The finalize record renders a short "Run summary" footer (final scores, iterations, converged/stopped).

### Wiring into the loop (`pipeline/run.py`) — pure observability
Build a `RevisionLogRecord` from values already in scope and call `revlog.write(record)` — once per iteration, **including the accept/stop iteration**. Two write points (pre-mortem fix):
- **Accept/stop path:** the loop currently does `if decision.action in ("accept","stop"): break` *before* any work — so the most decision-relevant moment (Judge accepted / human approved) would be lost. Write a record here first (scores, findings, `verdict`, `human_decision=decision.action`, no revisions, no regen) **then** break.
- **Iterate path:** after `obj`/revert is decided, write the iteration record (revisions, regenerated sections, outcome).

Details:
- **Origin tagging:** split the revision build into named lists — `judge_revs = list(decision.revisions or verdict.revisions)`; `floored = floor_visual_revisions(report.findings, judge_revs)`; `revisions = judge_revs + floored` (identical result/order to today). Record `origin="judge"` for `judge_revs`, `"backstop"` for `floored`.
- **Outcome:** snapshot `obj_before = best_obj` at the **top of the iteration** (before the keep/revert branch mutates it); `obj_after = obj`; `reverted = obj < best_obj - REGRESS_MARGIN`.
- **`review_bundle`:** `<base>/iter{i}` (loop's 0-based index `i`) **only if that dir exists**, else `None` — the ⑧ bundle counter and the loop index align in the common case but can desync if a critique iteration is skipped; the existence guard keeps the pointer from dangling.
- **`human_decision = decision.action`** (approve/redirect/stop/accept).
- A **finalize** record (`kind="finalize"`) after the loop with the final best scores + iteration count.

The writer is the only new call — no existing value is read back; logging cannot alter control flow (`write` is wrapped in try/except → warn-only, so a logging failure never breaks a run).

### Helpers — caller-stamped ids/time + registry snapshot
`run_id` and per-record `ts` are stamped by `run_pipeline` and passed down (a `clock: Callable[[], str]` defaulting to `datetime.now(UTC).isoformat()`, pinned in tests; `run_id` stable per run). `model_snapshot() -> dict[str,str]` builds `{role: model_string(role)}` over `_cfg()["roles"]` (no such accessor exists yet — add it; `model_string` already yields `provider:model`).

### run_id + timestamps passed in (not generated in the loop)
`run_id` and per-record `ts` are **stamped by the caller** (`run_pipeline`/CLI) and passed down — keeps the loop deterministic/testable and avoids generating time/uuid in restricted contexts. `run_id` is stable for the whole run (groups its iteration records); tests pass a fixed `run_id`/`ts`.

### Model snapshot from the registry
`models: dict[role, "provider:model"]` is captured once (passed in from `run_pipeline`, read from `models/registry.py`) so a record explains *which models produced this decision* — essential when comparing prompt/model changes across runs.

## Risks / Trade-offs

- **Record drift vs the loop** — if the loop later changes shape, the record must keep up. Mitigated by building it from the same in-scope values and a round-trip test; `RevisionLogRecord` is additive-friendly (optional fields).
- **Disk growth** — JSONL per song per run; tiny (a few KB/iteration, no media — it *points* to the review bundle). Acceptable; pruning is a later concern.
- **PII/secrets** — records contain show data + model IDs only, no keys; same trust domain as the existing bundles.
- **Logging failure** — wrapped in try/except → a write error degrades to a warning, never breaks refinement (pure-observability invariant).

## Open Questions

- Whether to also emit a top-level per-run summary file (best score, iterations, converged?) — defer; derivable from the JSONL.
- Eventual analysis tooling (the payoff) is intentionally out of scope here — this change only lays down the substrate.
