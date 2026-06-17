## Why

A revision-log analysis across 42 runs / 122 refine iterations shows the judging iterations are
**front-loaded and wasted on already-good drafts**. Runs whose first-pass objective is **≥ 88** gained
on average **+0.6** objective points over 2–3 iterations (only 5/18 improved at all, and 14 of the
loop's reverts happened there), while runs starting **< 88** gained **+19.2**. Each refine iteration
still pays for the planner-tier **Judge** call plus the multimodal **visual critique** plus per-section
regenerations plus a render — so on a draft that is already good, the loop spends the most expensive
calls in the pipeline to change essentially nothing. The team is actively trying to reduce AI cost.

## What Changes

- Add a **first-pass objective skip gate** to the refine loop: when the initial draft's deterministic
  objective score is at or above a threshold, the loop **accepts the draft and returns without running
  any Judge / visual-critique / regeneration iterations**. The gate uses only the cheap deterministic
  QA score that the loop already computes — it spends no LLM calls to decide.
- The threshold is a named constant, **tunable via `XLO_REFINE_SKIP_OBJECTIVE`** (set it to `101` to
  disable the skip and always iterate). Default **88**, from the data above.
- The skip is recorded in the revision log (a finalize record marked `skip-high-objective`) so the
  decision stays observable.
- Refinement remains correct and bounded: when the first pass is below the threshold the loop runs
  exactly as today; the iteration cap, plateau, and stall behaviors are unchanged.

## Capabilities

### New Capabilities
<!-- none — this refines existing refine-loop behavior -->

### Modified Capabilities
- `show-refinement`: the refine loop gains a deterministic early-exit — a draft whose first-pass
  objective score meets a tunable threshold is accepted without spending judging iterations.

## Impact

- `packages/xlights-orchestrator/src/xlights_orchestrator/pipeline/run.py`: a `REFINE_SKIP_OBJECTIVE`
  constant + `XLO_REFINE_SKIP_OBJECTIVE` env override, a `skip_objective` parameter on `_refine_loop`
  (default off so existing loop-mechanics tests are untouched), the early-exit before the iteration
  loop, and `run_pipeline` passing the resolved threshold.
- Tests: hermetic coverage that a high first-pass objective skips iterating (Judge/regen never called)
  and a low one iterates as before. No schema/CLI changes; default behavior tunable and disable-able.
