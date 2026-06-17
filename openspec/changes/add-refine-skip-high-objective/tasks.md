## 1. Threshold config

- [x] 1.1 In `pipeline/run.py`, add `REFINE_SKIP_OBJECTIVE = 88` (named constant near `REGRESS_MARGIN`/
  `STALL_LIMIT`) with a comment citing the revision-log analysis.
- [x] 1.2 Add `_refine_skip_objective() -> int` reading `XLO_REFINE_SKIP_OBJECTIVE` (int; falls back to
  the constant on a missing/invalid value). Add `import os` if absent.

## 2. Early-exit in the refine loop

- [x] 2.1 Add a `skip_objective: int | None = None` parameter to `_refine_loop` (default `None` = off, so
  existing direct-call tests are unaffected).
- [x] 2.2 After `best_obj` is computed and `_report`/`_record` are defined (before the `for i in
  range(max_iterations)` loop), add: if `skip_objective is not None and best_obj >= skip_objective`,
  log it, write a finalize revision-log record (`kind="finalize"`, `obj_after=best_obj`,
  `human_decision="skip-high-objective"`), and `return`. Do not call the Judge, visual critique, or
  regenerate.
- [x] 2.3 In `run_pipeline`, pass `skip_objective=_refine_skip_objective()` to `_refine_loop`.

## 3. Hermetic tests

- [x] 3.1 Test: a high first-pass objective (≥ threshold) with an explicit `skip_objective` skips the
  loop — assert the injected Judge and `regenerate` hooks are NEVER called and the instructions are
  unchanged.
- [x] 3.2 Test: a below-threshold first-pass objective still iterates (Judge/regen invoked) — confirms
  the gate doesn't fire spuriously.
- [x] 3.3 Test: the skip writes a `skip-high-objective` finalize record to the revision log.
- [x] 3.4 Test `_refine_skip_objective()`: default = constant; `XLO_REFINE_SKIP_OBJECTIVE` override
  (valid int); invalid value falls back to the constant; `101` disables (loop iterates).
- [x] 3.5 Run the full hermetic suite (`pytest`) — confirm existing refine/visual/revision-log tests
  still pass (default-off keeps them unchanged).

## 4. Land

- [x] 4.1 Note the `XLO_REFINE_SKIP_OBJECTIVE` knob where refine/cost behavior is documented (README or
  docs/usage.md) — what it does and that `101` disables it.
- [ ] 4.2 Open a PR per the project workflow; do not commit to `main` directly.
