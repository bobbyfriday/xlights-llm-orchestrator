> **Build result:** `revision_log.py` (RevisionLogRecord + file-backed `RevisionLog` writing BOTH `revision_log.jsonl` (canonical) and `revision_log.md` (human narrative) + `NullRevisionLog` + pure `_render_md`); `model_snapshot()` in the registry; refine loop emits a record per iteration INCLUDING the accept/stop iteration (pre-mortem fix) + a finalize record, with revisions tagged judge-vs-backstop, obj before/after/reverted, human decision, model snapshot, and an existence-guarded review-bundle pointer; `run_pipeline`/CLI thread run_id + clock + models + `--no-log`. Pure observability (write wrapped, NullRevisionLog default). **97 hermetic tests pass** (7 new): per-iteration + accept-logged + backstop-tagged + JSONL round-trip + Markdown render + no-op + swallow-write-failure. 3.6 (gated full `xlo run --refine --auto`) not executed this session — heavy multi-iteration run; plumbing fully covered hermetically + the file writer is disk-verified.

## 1. Record + writer

- [x] 1.1 `revision_log.py`: `RevisionLogRecord` pydantic model (run_id, iteration, song_key, ts, kind, objective/advisory_score, findings[{source,severity,scope,section_index,detail}], judge{score,verdict}|None, revisions[{section_index,issue,origin}], regenerated_sections, obj_before/after/delta, reverted, human_decision, models{role→provider:model}, review_bundle)
- [x] 1.2 `RevisionLog` (file-backed: appends `model_dump_json()+"\n"` to `revision_log.jsonl` AND `_render_md(record)` to `revision_log.md`) + `NullRevisionLog` (no-op); `source_of(metric)` helper (`visual:*`→`visual`, else the metric)
- [x] 1.3 `_render_md(record) -> str`: pure record→Markdown (one section per iteration — scores, flagged-by-source, Judge verdict + revisions with inline `judge`/`backstop` origin, regenerated + outcome, human decision, frames + models; finalize → run-summary footer)

## 2. Loop wiring (pure observability)

- [x] 2.1 `pipeline/run.py` `_refine_loop`: accept injectable `revlog` (default `NullRevisionLog`) + `run_id` + `models` + `clock`; snapshot `obj_before = best_obj` at the top of each iteration; build + `revlog.write(...)` a record per iteration (wrapped in try/except → warn-only, never breaks the run)
- [x] 2.2 **Record the accept/stop iteration too:** write a record (scores, findings, verdict, `human_decision`, no revisions) BEFORE `break` on accept/stop — the final decision must be logged
- [x] 2.3 Origin tagging via named lists: `judge_revs = list(decision.revisions or verdict.revisions)`; `floored = floor_visual_revisions(report.findings, judge_revs)`; `revisions = judge_revs + floored` (same result/order as today) → `origin` judge vs backstop; capture `obj_after`, `reverted = obj < best_obj - REGRESS_MARGIN`, regenerated sections, `human_decision = decision.action`
- [x] 2.4 `review_bundle = <base>/iter{i}` only if the dir EXISTS, else `None` (guard against counter/index desync)
- [x] 2.5 Write a `kind="finalize"` record after the loop with final best scores + iteration count
- [x] 2.6 `models/registry.py` `model_snapshot() -> dict[str,str]` over `_cfg()["roles"]`; `run_pipeline`/CLI stamp `run_id` + a `clock`, snapshot models, build the default `RevisionLog(<key>/revision_log.jsonl, <key>/revision_log.md)` when refine + logging on (else `NullRevisionLog`); add a `--no-log` flag

## 3. Tests & verification

- [x] 3.1 Hermetic: a 1-iteration loop writes exactly one iteration record + one finalize record with the expected fields (scores, findings-by-source, judge verdict, regenerated sections, obj_before/after)
- [x] 3.2 Hermetic: a backstop-synthesized revision is recorded with `origin="backstop"`; a Judge revision with `origin="judge"`
- [x] 3.3 Hermetic: each JSONL line round-trips back into `RevisionLogRecord`; `_render_md` renders a record to Markdown that names the flagged sections, the verdict, and each revision's `judge`/`backstop` origin; `revision_log.md` is written alongside the `.jsonl`
- [x] 3.4 Hermetic: `NullRevisionLog` / `--no-log` writes nothing; `refine=False` writes nothing
- [x] 3.4a Hermetic: a loop that ACCEPTS immediately still writes a record capturing the verdict + `human_decision` (the accept iteration is logged); `review_bundle` is `None` when no bundle dir exists
- [x] 3.5 Hermetic: **pure observability** — same final loop state with logging on vs off; a writer that raises is swallowed (run still completes)
- [ ] 3.6 Live (gated): `xlo run --refine --auto` produces a non-empty `revision_log.jsonl` alongside the `visual_review/` bundles, each line parseable
