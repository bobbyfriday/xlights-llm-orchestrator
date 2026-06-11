## Why

The pipeline produces a first-draft show and stops — it never checks whether the draft is any good or improves it. This change adds the **test → judge → refine** loop: score the draft against the music with cheap deterministic checks, have a Judge decide what's weak, regenerate just those sections, and repeat a bounded number of times. It turns one-shot generation into iterative quality.

**The long-standing blocker is resolved.** We feared the refine loop needed per-effect *remove/replace*, which the xLights API lacks (and `checkSequence` is banned — it crashes). It doesn't: the emitter already treats `EffectInstruction[]` as the canonical state and **clean-slate-rebuilds** the whole sequence. So "scoped regen" = swap the flagged sections' instructions in that list and rebuild from scratch. No `removeEffect`, no in-place mutation.

## What Changes

- **Deterministic QA — objective guardrails, NOT a quality oracle** (no xLights, no LLM; pure functions over `EffectInstruction[]` + `SongAnalysis` + `MusicBrief` + the emitter's placed/skipped report). Split deliberately:
  - **Hard/objective metrics** (unambiguous — "more correct" involves no taste): **Sync** (effect times vs the beat grid/sections — on-beat is objectively better), **Placement** (did effects survive; any empty section). These are the only thing the loop is allowed to auto-gate on.
  - **Soft/advisory metrics**: **Variety/coverage** (monotony, unused groups, intensity range). These are *inputs to the Judge*, never an automatic verdict.
  The deterministic score is used **only to detect objective regressions** (a revision that made more effects fall off-beat or emptied a section → conservative revert). Its worst failure mode is being over-cautious; it never renders a creative verdict. Tolerances/weights are transparent and surfaced at the checkpoint.
- A **Judge agent** (planner tier) reads all QA findings + a compact ShowPlan/MusicBrief summary → a **score (0–100)**, a prioritized list of **scoped RevisionBriefs** `(section, groups, issue, suggested_fix, do_not_repeat)`, and a **verdict** (accept / iterate / stop). The Judge owns *quality*; the human owns the *final* call.
- A **bounded refine loop with multiple independent stop conditions** — it terminates on **any** of: a **hard `MAX_ITERATIONS` cap** (default 3) it cannot exceed, a **stall detector** (K iterations with no objective progress), the Judge saying stop/accept, or the **human** saying stop. It never relies on the Judge to stop itself. Regenerate only flagged sections (existing Generator + the RevisionBrief), rebuild + re-render via the emitter, keep the best-scoring instruction set; an **anti-oscillation ledger** prevents re-flagging a deliberate change.
- **Human-in-the-loop checkpoints** (attended by default; `--auto` for headless): at each **decide** step the loop pauses and presents the score + findings + proposed revisions; the human can **approve / edit or drop revisions / redirect with a note / stop now / accept-as-final**, and a **final approval** precedes save. The human verdict overrides the Judge. This is the primary safeguard — every iteration is reviewable, so a bad score or Judge can't run away.
- New pipeline stages **test → decide → (loop to generate) → finalize**; refinement is **opt-in** (`--refine` / `refine=True`) and always leaves a valid, rendered sequence.

**Non-goals (later ⑦b):** the **Visual critic** (preview-frame export + a vision model) and **Render QA** (per-model render-data export — needs API verification); a multi-critic panel. The deterministic gates land first; LLM judgment is spent only on what passes them.

## Capabilities

### New Capabilities
- `show-refinement`: Evaluate a draft sequence with deterministic checks, judge it into a score + scoped revisions, and iterate — regenerating weak sections and rebuilding — bounded, anti-oscillating, and leaving a valid sequence at every step.

## Impact

- **`xlights-orchestrator`** gains `qa/` (sync/variety/placement, pure, hard-vs-soft), an `agents/judge.py`, refine contracts (`Finding`/`RevisionBrief`/`QAReport`/`JudgeVerdict`), a `judge` registry role, a **human-checkpoint callback** (interactive default, auto-accept in tests/`--auto`), and `test → decide → finalize` stages in `pipeline/run.py`.
- **Reuses** the existing Generator (one generation path; `render_input` gains an optional `revision`) and emitter (rebuild = call it again on the updated instruction list); the refine loop closes the prior draft before each rebuild (`client.close_sequence`).
- **Additive `show-orchestration` touches** (backward-compatible, `refine=False` unchanged): `EffectInstruction` gains an optional `section_index` (so scoped regen can replace one section's slice), and the emitter's `skipped` report entries gain `start_ms`/`end_ms`/`section_index` (so per-section placement QA is computable).
- **More LLM calls** only when `--refine` is on: 1 Judge + the regenerated sections per iteration, bounded by `MAX_ITERATIONS`; deterministic QA is free.
- **No new external deps.** Builds on `audio-analysis` (beats/segments), `music-interpretation` (MusicBrief), `show-orchestration` (ShowPlan/Generator/emitter).
