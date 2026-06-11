## Context

Closes the visual feedback loop opened by ⑧. The plumbing already exists: the visual critic appends advisory `Finding`s (`metric="visual:*"`, scoped by `section_index`, `objective=False`) to `report.findings` before the Judge runs (`run.py` test-phase), the loop re-critiques each iteration and writes a review bundle, and `generator_mod.render_input(section, revision)` already appends a revision's `suggested_fix`/`do_not_repeat`. This change makes the loop reliably *act* on what's seen — without changing the objective gate.

Live proof of the gap: the critic reported the chorus "renders completely dark" (effects placed, but no light — deterministic placement QA can't catch it), yet nothing guarantees a fix.

## Goals / Non-Goals

**Goals:** make the visual critique **music-aware** (judge visuals against each section's musical context + assess dynamics/variety/sync); the **Judge decides** revisions from it; the Generator receives the visual issue; a **narrow backstop** for critic-confirmed defects; the loop re-sees after regen; visual stays advisory to the objective gate. Hermetic tests + a live closed-loop check.

**Non-Goals:** deterministic "dark=revise" / "light-all-groups" rules (the Judge decides, the Generator regenerates); visual findings driving the objective revert gate; video/temporal generation changes; new model types.

## Decisions

### Music-aware critique (the headline fix — `agents/visual_critic.py::render_input`)
"Dark" / "static" / "low-energy" is not a defect by itself — a dark, quiet beat before a drop is intentional; the same mid-peak is wrong. So the critic must judge the visuals **against what the music is doing there**. `render_input(media, plan, brief)` is extended to give, **per section**, the musical context already on `brief.sections[i]` — the section's `intensity`, `label` (intro/verse/chorus/drop/outro…) and its **neighbor labels** (so "before a transition" is visible). It zips `media` with `brief.sections[:len(media)]` (the sampler builds `media` from `brief.sections` in order, so index `i` aligns) and guards the cap edge (missing next-neighbor at the last sampled section). No new `MusicBrief` math — reuse `intensity`/`label`, not a re-derived energy. The prompt asks the critic to: (a) judge whether the visuals fit the music *here* (is the darkness/staticness/energy appropriate or a defect for this moment?), and (b) assess **dynamics/variety** (dynamic and unique, not repetitive, not random) and **music-sync** (effects go with the energy/structure). It marks `severity=error` only for *contextual* defects — not darkness per se. **The contextual judgment itself (intentional-dark-not-flagged) is LLM behavior, verified LIVE, not hermetically** (TestModel ignores input — hermetic tests assert the context is *in the prompt*, not the verdict).

### The Judge decides revisions (`agents/judge.py`)
The Judge already receives `report.findings` (including the now music-aware `visual:*` entries) via `judge_mod.render_input`. The prompt is updated to treat them as first-class **judgment inputs** — weigh them against the musical intent and emit scoped `RevisionBrief`s for genuine problems, carrying a concrete visual fix. No deterministic "visual property → revision" mapping; the Judge arbitrates. No contract change.

### Carry the visual issue into the revision (so the Generator sees it)
When a `RevisionBrief` comes from a visual finding (Judge-made or backstop), its `issue`/`suggested_fix` carry the critic's **visual detail verbatim** (e.g. "dark mid-chorus — should be fully illuminated and active"). `generator_mod.render_input(section, revision)` already surfaces `issue`/`suggested_fix`/`do_not_repeat`, so the regenerated section is told what looked wrong — no generator-signature change.

### Section identity — add `section_index` to `Finding` (don't parse the scope string)
**Pre-mortem fix:** `refine.Finding` carries only `scope: str` (e.g. `"section 2 / G1"` from QA, `"section 2"` from visual), so recovering the int to target a `RevisionBrief` by regex is brittle. Add `section_index: int | None = None` to `Finding`; `visual_critic.to_findings` sets it from `VisualFinding.section_index` (QA findings leave it `None`). The backstop reads `finding.section_index` directly — robust, no parsing. Additive/back-compat (existing `Finding`s default `None`).

### Narrow backstop — critic-confirmed defects only (`refine.py` helper + loop)
A safety net so a *confirmed* defect the Judge overlooked isn't silently kept — **not** a "dark=bad" rule. `floor_visual_revisions(findings, existing) -> list[RevisionBrief]`: for each finding with `metric` startswith `"visual:"` and `severity=="error"` (the critic's *contextual* error judgment) and a non-`None` `section_index` **not** already covered by `existing` revisions, synthesize a `RevisionBrief(section_index, issue=<visual detail>, suggested_fix="visual defect for this musical moment — regenerate to fit the music here")`. In the loop (`pipeline/run.py:113`, after the decision, before regenerating), `revisions = list(decision.revisions or verdict.revisions); revisions += floor_visual_revisions(report.findings, revisions)`; record synthesized briefs in the anti-oscillation ledger; bounded by `max_iterations`. Because the trigger is the *music-aware critic's* `severity=error`, an intentional dark lull (marked `info`/`warn`) never floors. Pure + unit-testable.

### Re-critique already closes the loop (verify, don't rebuild)
⑧'s loop already calls `visual_critique(st)` each iteration after rebuild, writing the next review bundle — so after a visual revision regenerates + rebuilds a section, the next iteration's critique re-renders and re-judges it. Nothing new; the tests/live just confirm the closed loop (the dark section's later bundle frame is lit, or the loop terminates having attempted the fix).

### Advisory-to-objective invariant preserved
The floor and Judge-driven revisions add **`RevisionBrief`s**, never findings to `objective_score`. `_obj` still derives only from `qa_eval(...).objective_score` (sync+placement). So a visual revision changes *what gets regenerated*, not the objective revert/stall decision — taste never silently reverts; only objective regressions do (`show-refinement` invariant). A unit test asserts `objective_score` is unaffected.

## Risks / Trade-offs

- **Mislabeling intentional dark/quiet moments** (the whole reason for this change) → mitigated by music-awareness: the critic judges in context and only marks `severity=error` for *contextual* defects, so a dark pre-transition lull isn't flagged or floored. The backstop triggers on the critic's contextual error, not on darkness.
- **Music-context quality** → the per-section context comes from `MusicBrief` (intensity/label/energy). If the brief is weak the critique is weaker — but that's the same input the Director already plans from; no new failure mode.
- **Over-acting on subjective findings** → only `severity=error` floors; `warn`/`info` inform the Judge but don't force a revision. The Judge arbitrates the soft ones (dynamics/variety/sync) as judgment.
- **Oscillation / fix may not land** → the synthesized brief enters the anti-oscillation ledger; the hard `max_iterations` cap bounds it; a section that can't be fixed in budget is surfaced to the human at the checkpoint with the before/after review bundle, not looped forever. We don't hardcode a guaranteed fix.
- **Cost** → reuses the existing per-iteration critique + regen; no extra model calls beyond the loop's bound.

## Open Questions

- How much musical context to feed per section (just intensity/label vs a richer energy window) for the cost/signal tradeoff — start lean (intensity/label/energy + neighbors), tune live.
- Whether a persistent defect after N attempts should escalate more loudly to the human (a "could not fix visually" flag) — start by surfacing it in the bundle/checkpoint.
