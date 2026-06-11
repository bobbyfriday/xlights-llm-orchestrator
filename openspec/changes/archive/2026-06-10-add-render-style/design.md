## Context
`B_CHOICE_BufferStyle` (`Per Model Default`/`Per Preview`/`Default`/…) is a universal Buffer-tab setting → appendable via `extra_settings`. Render style is intent-dependent (layering guide §6: group-canvas vs per-model are different musical statements). The Generator + Visual Critic are now injected with the layering guide, so the LLM can reason about it. Code-owns-facts / LLM-owns-judgment → render style is judgment.

## Goals / Non-Goals
**Goals:** LLM chooses render style per effect; applied via B_CHOICE_BufferStyle; iterable in refine; a fallback so never the sparse default. **Non-Goals:** a fixed map as primary; coverage QA metric (companion); value-curve On.

## Decisions
### `EffectInstruction.render_style: str = ""`
A free-ish buffer-style string the Generator sets ("Per Model Default" | "Per Preview" | "Default" | "Per Model Per Preview" | "Single Line" | …). Validated against the known set; unknown/empty → fallback.
### Generator chooses it
`SectionEffects`/`EffectInstruction` schema carries `render_style`; `generator.render_input` asks the Generator to set it per effect per the layering guide (group-canvas for unified gestures/sweeps; per-model when each prop should render the effect). The guide injection already gives it the knowledge.
### Apply + fallback
`place_preset` (or the emitter) sets `extra_settings["B_CHOICE_BufferStyle"] = render_style or _fallback(effect_type)`. `_fallback`: a light map (fill effects → "Per Model Default"; sweeps → "Per Preview"; simple/On → "Default"; unknown → "Per Model Default") used ONLY when the LLM didn't choose — so it's never the sparse default. Code-generated layers (beat/hero/flash, all `On`) → "Default".
### Refine
The refine loop already regenerates flagged sections; the Generator (seeing the critic's "dark/sparse" finding + the layering guide) can pick a different render_style. No new loop machinery.

## Risks / Trade-offs
- **LLM picks a poor style** → the critic + refine catch it (the whole point); the fallback covers silence.
- **Schema/prompt churn** on the Generator → additive field + a prompt line; low risk.
- **Validation** → constrain to the known buffer styles; unknown → fallback (don't emit an invalid B_CHOICE).
## Open Questions
- Whether the Director should set a section-level render-style hint vs the Generator per-effect — start per-effect (Generator); the Director's effect_types already imply intent.
