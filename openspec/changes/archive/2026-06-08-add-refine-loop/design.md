## Context

Turns one-shot generation into a bounded iterate loop. Lands the cheap, certain pieces first: deterministic QA computed from data already in hand (`EffectInstruction[]`, `SongAnalysis.beats`/`segments`, `MusicBrief`, the emitter's placed/skipped report), a single Judge agent, and scoped regen via rebuild. The heavy/uncertain critics (visual/vision, per-model render export) are deferred.

Grounded: `SongAnalysis.beats` carries beat times + downbeats (`bar_position==1`); `client.close_sequence(force, quiet)` exists; the emitter (`apply_instructions`) clean-slate-rebuilds from a full `EffectInstruction[]` and reports `placed`/`skipped`. `checkSequence` is banned (crashes, see [[xlights-automation-quirks]]). Live LLM on Gemini (`XLO_PROVIDER=gemini`).

## Goals / Non-Goals

**Goals:** deterministic QA (sync, variety/coverage, placement) → score; a Judge → score + scoped RevisionBriefs + verdict; bounded scoped-regen loop that **rebuilds from the canonical instruction list** (no `removeEffect`); anti-oscillation; opt-in; hermetic tests.

**Non-Goals:** Visual critic (preview frames + vision model, ffmpeg), Render QA (per-model render-data export — unverified API), multi-critic panel, human checkpoints — all ⑦b.

## Decisions

### Rebuild-from-instructions (dissolves the "no removeEffect" blocker)
The canonical state is the full `EffectInstruction[]`. A revision **replaces** the flagged section's instructions in that list; the sequence is then rebuilt by the existing emitter (clean-slate `new_sequence` + place all + `render_all`). No per-effect removal, no in-place mutation, idempotent and retryable. Between iterations the loop **closes the prior draft** (`client.close_sequence(force=True, quiet=True)`) so the emitter's clean-slate `new_sequence` succeeds (it refuses when a sequence is open). Save only at finalize.

### Section attribution (required — the flat list isn't section-keyed today)
`run.py`'s generate stage currently builds a **flat** `st.instructions` with no section grouping, so "replace only section *i*" is not expressible. Fix: **tag each `EffectInstruction` with `section_index: int`** (new optional field on the `show-orchestration` contract — additive, backward-compatible). The generate loop sets it; `replace_section(instructions, i, new)` swaps the slice whose `section_index == i`; per-section QA filters by it. The emitter passes `section_index` through into its `placed`/`skipped` report, and its **`skipped` entries gain `start_ms`/`end_ms`/`section_index`** (today they carry only target/effect/reason) so per-section placement QA is computable. Both touches are additive — existing behavior and the `refine=False` path are unchanged.

### Deterministic QA (`qa/`, pure functions — objective guardrails, not a quality oracle)
Each check returns `Finding{ scope, severity, metric, detail, objective: bool }` + a sub-score. **Two classes, kept distinct** (`QAReport.objective_score` vs `advisory_score`):
- **Objective** — `qa/sync.py` (distance from each `start_ms`/`end_ms` to the nearest beat/section boundary in `SongAnalysis.beats`/`segments`; fraction within tolerance — frame-based from `frame_ms`; worst offenders scoped). **Empty-beats guard:** if `SongAnalysis.beats` is empty, the sync sub-score is neutral (not 0) and does not gate — a beatless analysis must not tank the score or divide by zero. And `qa/placement.py` (per-section skip rate + zero-effect sections, keyed by the `section_index` now in the emitter report). "More on-beat / fewer empty sections" is unambiguously better.
- **Advisory** — `qa/variety.py` (per-group effect-type histogram, groups-used ratio, effects-per-section, intensity dynamic range from the ShowPlan → monotony/unused/overcrowded). Partly taste; **fed to the Judge, never auto-gated.**

`qa/__init__.py` `evaluate(...) -> QAReport` computes both scores. **Only `objective_score` drives the loop's revert/stop gate**; `advisory_score` + all findings inform the Judge and the human. Tolerances/weights are explicit module constants, surfaced in the checkpoint render. All unit-testable on synthetic instructions — this is where the loop's *objective* correctness lives, cheaply, and its assumptions are narrow on purpose (only timing+placement), so a bad assumption can at most cause a conservative revert, never a wrong creative verdict.

### Judge agent (`agents/judge.py`, planner tier)
`build_agent("judge", output_type=JudgeVerdict, ...)`. Input: the QA findings + sub-scores + a compact ShowPlan/MusicBrief summary + the anti-oscillation ledger. Output `JudgeVerdict{ score:int, verdict: accept|iterate|stop, revisions: list[RevisionBrief] }`. The Judge prioritizes/dedups findings into a small set of scoped `RevisionBrief{ section_index, groups, issue, suggested_fix, do_not_repeat }`. The deterministic score is advisory; the Judge's score is authoritative for the loop (but the loop also tracks the deterministic score to detect "no improvement" objectively).

### Refine loop (`pipeline/run.py`: test → decide → finalize)
Multiple **independent** stop conditions; the hard cap and stall detector are evaluated by the loop itself, never delegated to the Judge.
```
best, best_obj = instructions, qa(instructions, ...).objective_score
ledger, stall = [], 0
for i in range(max_iterations):                    # HARD cap (default 3) — cannot be exceeded
    report  = qa(instructions, analysis, brief, plan, applied)
    verdict = await judge.run(render(report, plan, brief, ledger))   # Judge owns quality
    decision = await checkpoint(report, verdict, ledger)             # HUMAN (attended) or auto
    if decision.action in ("accept", "stop"):     # human/Judge/auto says we're done
        break
    revisions = decision.revisions                # human may edit/drop/redirect; else verdict's
    for rev in revisions:
        new = await regenerate(rev)               # Generator(section[rev.section_index], rev)
        instructions = replace_section(instructions, rev.section_index, new)  # swap tagged slice
        ledger.append(rev)                                            # anti-oscillation
    await client.close_sequence(force=True, quiet=True)
    applied = await emitter(client, instructions, duration)           # rebuild + render
    obj = qa(instructions, analysis, brief, plan, applied).objective_score
    if obj < best_obj - MARGIN:                   # objective REGRESSION → revert this revision
        instructions, applied = best, best_applied
        stall += 1
    elif obj <= best_obj + MARGIN:                # no objective progress
        stall += 1
    else:
        best, best_obj, stall = instructions, obj, 0
    if stall >= STALL_LIMIT:                       # stall detector → terminate
        instructions = best; break
# finalize(best) + final human approval before save
```
- **`checkpoint(report, verdict, ledger) -> Decision`** is an injected callable. Default (attended) renders the score (objective + advisory), findings, and proposed revisions to the terminal and reads the human's choice (`approve` / edit-or-drop revisions / `redirect` with a note / `stop` / `accept`); the human's choice **overrides** the Judge. `--auto` and tests pass a non-interactive `checkpoint` that returns the Judge's verdict verbatim (and `accept` once the Judge accepts). A **final approval** gates `save_as`.
- **`regenerate(rev)`** maps `rev.section_index → st.show_plan.sections[i]` and calls the existing Generator via `generator_mod.render_input(section, revision=rev)` (its `render_input` gains an optional `revision` that appends `suggested_fix`/`do_not_repeat`) — one generation path; the returned instructions are tagged with `section_index=i`.
- The loop is fully **injectable** (`judge=`, `qa=`, `regenerate=`, `checkpoint=`) so tests drive it deterministically with stubs.

### Human-in-the-loop (`checkpoint`)
Attended is the **default** for `--refine`; `--auto` skips prompts (cap + objective gates only). The checkpoint is the primary safeguard against a wrong deterministic score *or* a wrong Judge: every iteration is shown to the human, who can halt or redirect. The checkpoint callable is the single interaction seam (CLI prompt today; could be a UI later) and is trivially stubbed in tests, keeping the loop hermetic.

### Contracts (`refine.py`)
`Finding`, `QAReport{ score:int, findings:list[Finding], subscores:dict }`, `RevisionBrief`, `JudgeVerdict`. Kept separate from `show_plan.py`.

### Opt-in
`run_pipeline(..., refine: bool = False, max_iterations: int = 3)`; CLI `xlo run --refine`. Off → today's behavior byte-for-byte (no test/decide stages run).

## Risks / Trade-offs

- **Judge cost/latency on free tier** — only when `--refine`; bounded by `MAX_ITERATIONS`; deterministic gates do the heavy lifting so the Judge sees pre-digested metrics.
- **Rebuild cost per iteration** — a full clean-slate + place-all + render each iteration (seconds); acceptable for ≤3 iterations; the alternative (in-place edit) needs the missing `removeEffect`, so rebuild is the robust path.
- **🔴 A wrong/badly-assumed deterministic score (the core risk)** — mitigated by three layers: (1) it gates only **objective** regressions (timing/placement), where assumptions are narrow and "better" is unambiguous — variety/taste is never auto-gated; (2) its worst failure is a *conservative revert*, never a wrong creative verdict; (3) the **human checkpoint** sees every iteration's score+findings and can override or stop, so even a mis-tuned score can't drive the result. Tolerances/weights are explicit constants, surfaced at the checkpoint and tunable.
- **Runaway loop** — three independent terminators (hard `max_iterations` cap, stall detector over `STALL_LIMIT`, human/Judge stop); the cap is enforced by the `for` bound, not the Judge.
- **Regen non-determinism** — a regenerated section may score worse; the best-result retention + revert-on-no-improvement guard against regressions.
- **Anti-oscillation completeness** — the ledger is passed to the Judge as "do not re-flag"; if the Judge ignores it, the iteration cap still bounds the loop.

## Open Questions

- Sync tolerance window (frames) and the score weighting across sync/variety/placement — tune against the real Baby Shark draft at build.
- Whether to also expose the deterministic QA standalone (`xlo score`) — nice-to-have, defer.
