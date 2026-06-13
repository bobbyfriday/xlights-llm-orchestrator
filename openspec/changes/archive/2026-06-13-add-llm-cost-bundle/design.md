## Context

The generator runs once per section (~21 calls/run) and again per refine revision; its `with_guides(_PROMPT, "sequencing", "effects", "layering", "scenes")` system prompt is ~99KB. The audit attributes ~60% of run cost to re-sending that corpus. Separately, the refine loop's stall counter only moves on regressions, so identical-iteration plateaus spend a full pro-tier cycle, and the gemini routing was provisioned before flash-lite was validated on real section generation.

## Goals / Non-Goals

**Goals:** cut the generator's per-call prompt ~7x with deterministic, heading-based extracts; stop the refine loop the moment an iteration provably re-bought the previous answer; route gemini worker-tier roles to flash-lite/flash.

**Non-Goals:** changing the Director/synthesizer/critic prompts or models (1 call/run, planner tier — full guides stay); summarizing guides with an LLM (deterministic slices only — no new spend, reproducible); touching anthropic routing; prompt caching (provider-dependent, orthogonal).

## Decisions

**D1 — Heading-sliced extracts, never raising.** `guide_extracts._cut(text, want)` parses `#{1,4}` headings; a matched section runs to the next same-or-higher-level heading; level-1 headings are document titles, never sections (the layering guide's H1 contains "Render Styles" and would swallow the whole file). Every public function degrades to `""` — a thinner prompt is a valid state, exactly like `load_guide`.

**D2 — What the generator actually needs.** `catalog_essentials()` = Quick Reference Table (incl. 2.1 Duration Classes) + Placement Decision Rules — the choose/place tables; per-effect prose is Director material. `layering_essentials()` = the "Render Styles" section (preferring "Render Style" in the heading; a bare "Render"/"Buffer" match drags in ~3 extra sections; fallback = first 4KB). `sequencing_essentials()` = Core Philosophy + rhythm/call sections, bounded to ~3KB total (the raw first-3KB is ToC + version boilerplate, and unbounded extras blow the budget — see D4). `scene_recipe(id)` = only the heading block containing the id; `""` for empty/unknown.

**D3 — Scene recipes are per-call input, not system prompt.** The cookbook's value to the generator is the ONE scene the section realizes; `render_input` appends `scene_recipe(section.scene_id)` after the existing scene note. The system prompt carries no cookbook at all.

**D4 — Hard prompt budget <15KB, enforced by test.** Composed = `_PROMPT` (1.1KB) + catalog (7.8KB) + render styles (3.1KB) + sequencing (≤3KB) + terse headers ≈ 15.2KB (measured; was 99,091 bytes). The test gate `len(_system_prompt()) < 15*1024` catches guide growth.

**D5 — Plateau signature = scores + flagged work.** `(objective_score, advisory_score, frozenset((r.section_index, issue[:64]) for r in verdict.revisions))`. Equal to the previous iteration's → log, `_record(human_decision="plateau")`, break before applying revisions. Checked after the accept/stop checkpoint branch so a human/auto accept still records as accept. Issue text truncated to 64 chars so judge phrasing jitter doesn't defeat the match while distinct issues still differ. Side effect (intended): a repeat-offender escalation now requires *something* to have moved; a totally frozen iteration is a stop, not a redesign.

**D6 — Routing only where validated.** flash-lite was live A/B'd on a real section generation (valid structured output, rules 92) → generator + analyst. The judge consumes a structured QA report — flash, not pro. Director/synthesizer/visual_critic stay pro-preview; anthropic untouched.

## Risks / Trade-offs

- [Extract misses guidance the generator silently used] → the named sections are the decision tables the prompts reference; the Director's full-corpus plan and the QA rules backstop placement quality; live A/B before/after is the real gate (left as the unchecked live task).
- [Guide restructuring silently shrinks an extract] → tests pin sentinels ("Quick Reference Table", "Placement Decision Rules", "Core Philosophy") and non-empty bounds; fallbacks (first-4KB / first-3KB) keep a degraded-but-present prompt.
- [Plateau stop fires on a coincidental same-score iteration] → the signature also requires the identical flagged section/issue set; one changed digit or one different revision keeps iterating.
- [flash-lite quality dip across many sections] → config-only change, one-line revert; QA rules + refine loop catch structural regressions.

## Migration Plan

Code + config only; caches unaffected (instruction cache keys don't include prompts). Revert = `git revert` of the single commit; routing alone can be reverted by editing config.yaml.

## Open Questions

- Should refine-loop regens reuse a cheaper "revision-only" prompt (no guides at all, just the violated rule)? Deferred — measure the new baseline first.
