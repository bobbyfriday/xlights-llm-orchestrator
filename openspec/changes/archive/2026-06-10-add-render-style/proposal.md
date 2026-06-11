## Why
The dark-chorus defect is render style: radial/movement effects on a *group* render as one sparse shape across a flat group-canvas → "almost completely dark." `B_CHOICE_BufferStyle` fixes it (`Per Model Default` = each prop runs the effect → fills). But render style is a **creative choice, not a fixed property of an effect** — the layering guide is explicit: group-canvas vs per-model are "different musical statements, neither is right." A Pinwheel can be one unified gesture (group canvas) OR every-prop-spins (per-model) depending on intent. So the **LLM should choose it and iterate on it**, not a hard-coded map.

## What Changes
- **`EffectInstruction.render_style`** — a buffer style the **Generator chooses per effect** (it's now injected with the layering guide, so it knows group-canvas vs per-model and the recipes). The Generator's output schema + prompt surface it.
- **`place_preset` applies it** via `extra_settings["B_CHOICE_BufferStyle"]` (universal Buffer setting; appended).
- **Iterable in refine** — the Visual Critic (also injected with the layering guide) can flag "this reads dark/sparse — wrong render style," and the Generator changes it on regen. Render style becomes a tunable the loop converges on, like effect/look choice.
- **Deterministic FALLBACK only** — when the LLM leaves it unset (or for the code-generated beat/hero/flash layers), a sensible default is applied so an effect is **never** left on the broken sparse group-canvas default. The LLM leads; code just prevents the dark default.

**Non-goals:** a fixed effect→style map as the primary mechanism (it's only the fallback); the coverage/brightness QA metric (companion change so the loop *gates* on darkness); value-curve On shaping.

## Capabilities
### Modified Capabilities
- `show-orchestration`: the Generator chooses each effect's render/buffer style (guided by the layering guide) and the refine loop iterates it; a deterministic fallback ensures no effect renders on the sparse default — so fill effects light the display when that's the intent.

## Impact
- **`xlights-orchestrator`**: `EffectInstruction.render_style` (additive); Generator schema + prompt set it; `place_preset` applies `B_CHOICE_BufferStyle`; a fallback for unset/code-layer effects.
- **Builds on** the layering-guide injection (the Generator/Critic now reason about render style), SEM_ groups, `extra_settings`. The LLM-owned, iterable dark-chorus fix.
