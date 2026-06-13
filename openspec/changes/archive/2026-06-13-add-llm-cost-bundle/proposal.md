## Why

A cost audit of a full refine run found three independent money leaks. The generator's system prompt carries all four guides (~98KB of markdown) on EVERY call — ~25K tokens × 21 calls/run ≈ 60% of run cost — when each per-section call actually decides with a few KB of it. The refine loop only counts objective REGRESSIONS toward its stall limit, so a plateau (92→92→92 with the judge re-flagging the same sections) burns a full iteration of pro-tier judge + vision critic + several regens for an answer we already have. And the gemini routing uses flash/pro where a live A/B showed flash-lite suffices for worker-tier section generation (valid structured output, rules score 92).

## What Changes

- **Guide extracts for the generator (the big lever):** new `agents/guide_extracts.py` slices the loaded guides deterministically by markdown headings — catalog quick-reference + placement rules, the layering guide's render-style section, sequencing philosophy + rhythm sections, and a per-scene cookbook recipe. The generator's system prompt composes `_PROMPT` + those extracts (<15KB vs ~100KB); the section's named scene recipe moves into `render_input` so each call carries ONLY its own scene. The Director keeps the full guides (1 call/run, planner tier).
- **Plateau stop in the refine loop:** each iteration builds a signature of (objective_score, advisory_score, flagged section/issue set); when it matches the previous iteration's, the loop logs, records `human_decision="plateau"`, and stops BEFORE re-applying revisions. REGRESS_MARGIN / STALL_LIMIT / revert logic untouched.
- **Gemini worker-tier routing:** generator + analyst → `gemini-3.1-flash-lite`; judge → `gemini-3.5-flash`. Anthropic entries and gemini director/synthesizer/visual_critic (pro-preview) untouched.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `show-orchestration`: the per-section generator SHALL be prompted with bounded guide extracts (plus only its own scene's recipe) instead of the full guide corpus; the refine loop SHALL terminate when an iteration's scores and flagged revisions are unchanged from the previous iteration.

## Impact

- `xlights-orchestrator`: `agents/guide_extracts.py` (new), `agents/generator.py` (extract-composed system prompt; per-section scene recipe in `render_input`), `pipeline/run.py` (plateau signature + stop), `models/config.yaml` (gemini worker-tier routing).
- Tests: `tests/test_guide_extracts.py` (new), plateau cases in `tests/test_refine.py`, rewired scene-routing assertion in `tests/test_guide_injection.py`, moving-score fix in `tests/test_design_escalation.py` (a flat score + identical revision is now, correctly, a plateau stop).
- Back-compat: Director/critic/judge prompts unchanged; anthropic routing unchanged; missing guides still degrade to "".
