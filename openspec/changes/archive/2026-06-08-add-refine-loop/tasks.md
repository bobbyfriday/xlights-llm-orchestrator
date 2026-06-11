> **Build result (verified live on Gemini, unattended):** deterministic QA (sync/placement objective + variety advisory), Judge agent, rebuild-from-instructions refine loop with section-tagged `EffectInstruction`, objective-regression-only revert + stall/cap termination + injectable human checkpoint. **76 hermetic tests pass** (9 new; a hermetic test caught a revert-policy bug pre-ship). Live `xlo run --refine --auto` on 'Baby Shark' terminated within the cap and improved the draft to 15 placed / 0 skipped (from 12 placed w/ skips pre-refine). Note: the interactive checkpoint implements approve/stop/accept; edit/drop/redirect are a thin future add on the same `Decision` seam. `refine=False` path unchanged.

## 1. Contracts + role

- [x] 1.1 `refine.py`: `Finding` (scope, severity, metric, detail, **objective: bool**), `QAReport` (**objective_score**, **advisory_score**, findings[], subscores{}), `RevisionBrief` (section_index, groups[], issue, suggested_fix, do_not_repeat), `JudgeVerdict` (score, verdict: accept|iterate|stop, revisions[]), `Decision` (action: approve|redirect|stop|accept, revisions[])
- [x] 1.2 Add `judge` role (planner tier) to `models/config.yaml` for both providers
- [x] 1.3 **Section attribution (additive):** add optional `section_index: int | None` to `EffectInstruction` (`show_plan.py`); the generate loop in `run.py` tags each instruction with its section; emitter passes it through to `placed`/`skipped`, and `skipped` entries gain `start_ms`/`end_ms`/`section_index`. `replace_section(instructions, i, new)` helper swaps the tagged slice

## 2. Deterministic QA (pure)

- [x] 2.1 `qa/sync.py` (**objective**): per-instruction distance to nearest beat/section boundary (`SongAnalysis.beats`/`segments`); fraction within tolerance (frame-based, explicit constant) + worst offenders scoped → objective findings + subscore. **Empty-`beats` guard:** neutral sub-score, no gating (no divide-by-zero)
- [x] 2.2 `qa/variety.py` (**advisory**): per-group effect-type histogram, groups-used ratio, effects-per-section, intensity dynamic range (from ShowPlan) → advisory monotony/unused/overcrowded findings + subscore
- [x] 2.3 `qa/placement.py` (**objective**): per-section skip rate + zero-effect sections, keyed by `section_index` in the enriched emitter report → objective findings + subscore
- [x] 2.4 `qa/__init__.py` `evaluate(...) -> QAReport`: compute **objective_score** (sync+placement) and **advisory_score** (variety) separately; only objective_score feeds the loop's revert/stall gate; tolerances/weights are explicit constants surfaced for the checkpoint render

## 3. Judge

- [x] 3.1 `agents/judge.py`: `judge_agent()` (role `judge`, output_type `JudgeVerdict`) + `render_input(report, plan, brief, ledger)`; prompt prioritizes/dedups findings into a few scoped RevisionBriefs and honors the ledger (do-not-repeat)

## 4. Refine loop

- [x] 4.1 `pipeline/run.py`: add `refine: bool = False`, `max_iterations: int = 3`, `checkpoint=<default>`; after the first apply run **test → decide → finalize**: QA → Judge → checkpoint → if iterating, regenerate flagged sections, rebuild, re-score; keep best-scoring instruction set
- [x] 4.2 **Termination (independent):** hard `for i in range(max_iterations)` cap (cannot be exceeded) + stall detector (`STALL_LIMIT` consecutive no-objective-progress) + Judge accept/stop + human stop — never delegated to the Judge
- [x] 4.3 **Objective regression gate:** after each rebuild, compare `objective_score` to best; `< best - MARGIN` → revert this revision to best (count stall); only a real objective gain updates best. Advisory score never gates. Anti-oscillation ledger passed to the Judge
- [x] 4.4 Scoped regen: `regenerate(rev)` maps `rev.section_index → show_plan.sections[i]`, calls `generator_mod.render_input(section, revision=rev)` (render gains an optional `revision` appending `suggested_fix`/`do_not_repeat`), tags returned instructions `section_index=i`, and `replace_section` swaps only that slice; rebuild = `close_sequence(force,quiet)` then `emitter(...)`
- [x] 4.5 **Human checkpoint** callable `checkpoint(report, verdict, ledger) -> Decision`: default attended (render objective+advisory score, findings, proposed revisions; read approve/edit/redirect/stop/accept; human overrides Judge); final approval before `save_as`. `--auto`/tests pass a non-interactive checkpoint returning the Judge verdict
- [x] 4.6 Injectable (`judge=`, `qa=`, `regenerate=`, `checkpoint=`) for tests; `refine=False` leaves today's behavior unchanged
- [x] 4.7 CLI: `xlo run --refine [--auto] [--max-iterations N]` (attended default; `--auto` unattended)

## 5. Tests & verification

- [x] 5.1 Pure: `qa/sync` flags an off-beat instruction and passes an on-beat one; objective scores differ; findings marked `objective=True`
- [x] 5.2 Pure: `qa/variety` (advisory) flags a monotone draft; `qa/placement` (objective) flags a high-skip/empty section; `evaluate` returns distinct objective_score vs advisory_score
- [x] 5.3 Hermetic loop: stub Judge `iterate`→`accept`, non-interactive checkpoint, stub regenerate → flagged section changed, **unflagged sections byte-identical** (scoped-replace correctness), sequence rebuilt, loop stopped, ledger recorded
- [x] 5.3b Pure: empty-`beats` → `qa/sync` returns neutral sub-score (no gating, no error); per-section placement QA attributes a skip to the right `section_index`
- [x] 5.4 Hermetic: **objective regression → revert to best**; advisory-only change does NOT trigger revert
- [x] 5.5 Hermetic: **termination is independent of the Judge** — a Judge that always says `iterate` still stops at the hard cap; stall detector stops on repeated no-progress
- [x] 5.6 Hermetic: **checkpoint** — a checkpoint returning `stop` ends the loop; one returning `accept` overrides a Judge `iterate`; edited revisions are the ones regenerated
- [x] 5.7 Hermetic: `refine=False` path identical to pre-change (no QA/Judge/checkpoint calls)
- [x] 5.8 Live (gated, Gemini + xLights): `xlo run --refine --auto` on a real song holds/improves objective_score across ≤3 iterations and leaves a valid rendered sequence; `--refine` (attended) prompts at each decide
