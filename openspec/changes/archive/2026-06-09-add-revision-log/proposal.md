## Why

The refine loop is non-deterministic LLM judgment — critics flag, the Judge decides, generators regenerate. Right now every run is ephemeral, so we tune those prompts blind. A revision log turns each run into **data**: *critic flagged X → Judge did (or didn't) act → section regenerated → did the objective score improve?* That's exactly the signal needed to answer "the Judge ignores visual errors N/M times — tighten its prompt" or "dark-section revisions improve the score 60% of the time." We already **compute** all of it (QA scores, findings by source, Judge verdicts, RevisionBriefs, the visual review bundle) — this change just **captures** it durably and structured. Deliberately lean: a flight-recorder, not an analytics pipeline.

## What Changes

- A **`RevisionLogRecord`** (pydantic) + an append-only **JSONL** writer at `data/orchestrator/<song_key>/revision_log.jsonl` — one record per refine iteration, plus a finalize record. The JSONL is the **canonical/programmatic** source.
- Alongside it, a **human-readable `revision_log.md`** that narrates each iteration — what was flagged (by source), what the Judge decided and *why*, which revisions ran and whether the **Judge or the backstop** drove them, what got regenerated, whether the objective score improved or was reverted, and the human decision — with links into that iteration's visual frames. So a person can read the story of a run, not just parse it.
- Each record captures, per iteration: `run_id`, iteration index, `song_key`, timestamp (stamped by the caller), `objective_score` + `advisory_score`, the **findings by source** (metric, severity, scope, section_index, detail), the **Judge verdict** (score, verdict) + its revisions, **which revisions were backstop-synthesized vs Judge-made**, the sections regenerated, the **objective outcome** (`obj_before`, `obj_after`, delta, `reverted?`), the **human checkpoint decision** when attended (approve/redirect/stop/accept), a **per-role model snapshot** (role → provider:model), and a **pointer to that iteration's visual review bundle**.
- Wired into the refine loop as **pure observability** — emitted at the end of each iteration (and a finalize record). It never reads back into or changes any decision.
- The writer is **injectable and disable-able** (default file-backed; a no-op for tests and `--no-log`), created lazily so hermetic tests stay clean.

**Non-goals:** analytics/dashboards/query tooling, cross-run aggregation, fine-tuning/eval harnesses (the JSONL is the substrate — analysis is a separate later effort); Pydantic Logfire / operational telemetry (tokens/latency/calls — an orthogonal concern); changing any refine behavior; logging the non-refine phases (analyze/interpret/design).

## Capabilities

### New Capabilities
- `revision-log`: append a structured, durable record of each refine iteration — findings (by source), the Judge verdict, the revisions applied (distinguishing backstop-synthesized from Judge-made), the objective outcome (before/after/reverted), and the human decision — in **both** a programmatic JSONL form and a human-readable Markdown narrative, as a flight-recorder for tuning prompts, with logging strictly pure observability that degrades to no-op.

## Impact

- **`xlights-orchestrator`**: new `revision_log.py` (`RevisionLogRecord` + injectable `RevisionLog` writer); the refine loop in `pipeline/run.py` emits a record per iteration + finalize; `run_pipeline`/CLI thread a `run_id` + timestamps and a `--no-log` switch.
- **Builds on** `show-refinement` (⑦/⑨, the loop + findings + Judge + backstop) and `visual-critique` (⑧, the review bundle it points to). Reads only data the loop already produces.
- **No new deps**; writes alongside the existing `data/orchestrator/<song_key>/visual_review/` bundles.
