## Context

`_refine_loop` (`pipeline/run.py`) already computes the draft's deterministic objective score before
the iteration loop: `best, best_applied, best_obj = ..., await _obj(st.applied)`, where `_obj` →
`_report` → `qa_pkg.evaluate` (sync + placement; no LLM). The **expensive** work — the Judge agent and
the multimodal visual critique — runs *inside* the per-iteration loop body, never in that initial
scoring. So the information needed to skip is already in hand for free.

The revision-log analysis (42 runs) is unambiguous: the knee is at iteration 1 (median), and drafts
with a first-pass objective ≥ 88 gain ≈ 0 over the full loop while paying for every Judge + critic +
regen + render. Skipping the loop for those drafts is the highest-value, lowest-risk cost lever.

## Goals / Non-Goals

**Goals:**
- Spend zero LLM calls deciding to skip — gate on the already-computed deterministic objective.
- Tunable and fully disable-able without a code change.
- Zero behavior change when the first pass is below the threshold (and in existing tests).

**Non-Goals:**
- No change to the iteration cap, plateau, or stall logic (that's the separate "cap 3→2" lever).
- No new visual/quality signal — the gate is intentionally the cheap objective score only; running the
  critic to decide whether to skip the critic would defeat the purpose.
- No CLI flag in this change (env var is enough; a flag can come later).

## Decisions

**1. Gate on the initial deterministic objective, before the loop.**
After `best_obj` is computed and the `_record`/`_report` closures are defined, add: if
`skip_objective is not None and best_obj >= skip_objective`, log it, write a finalize revision-log
record marked `human_decision="skip-high-objective"`, and `return`. `st.instructions` / `st.applied`
are already the draft, so returning leaves the correct "best" state in place.

**2. `_refine_loop`'s `skip_objective` defaults to `None` (off); `run_pipeline` turns it on.**
This is the key design choice for safety: every existing test that drives `_refine_loop` directly (to
exercise plateau/stall/iteration mechanics, some with objective 92) keeps its behavior because the
default is off. Production goes through `run_pipeline`, which passes the resolved threshold. New tests
opt in by passing an explicit `skip_objective`.

*Alternative considered:* default the parameter to the production threshold. Rejected — it would
silently change `test_loop_stops_on_plateau` (objective 92) and any qa=None test whose synthetic draft
happens to score ≥ 88, coupling an orthogonal feature to those tests.

**3. Threshold = named constant + env override.**
`REFINE_SKIP_OBJECTIVE = 88` with `_refine_skip_objective()` reading `XLO_REFINE_SKIP_OBJECTIVE`
(int; falls back to the constant on a bad value). `run_pipeline` calls it once and passes the result.
Setting `XLO_REFINE_SKIP_OBJECTIVE=101` makes the gate unreachable (objective is 0–100) → always
iterate, i.e. today's behavior.

## Risks / Trade-offs

- [A high objective but poor *visual* quality slips through, since the critic never runs] → Accepted by
  design and supported by the data (advisory/variety barely moves on ≥88 runs; reverts cluster there).
  The threshold is conservative (88) and tunable; lower it toward 100 to make the skip rarer, or set
  101 to disable. Document the trade-off.
- [Threshold mis-tuned for a different show/layout] → It's an env var; no redeploy needed to adjust.
- [Observability lost] → Mitigated: the skip writes a finalize record (`skip-high-objective`) so the
  revision log still shows what happened and why.

## Open Questions

- Whether to also lower the default iteration cap (3→2) — tracked separately as lever #2; out of scope
  here.
