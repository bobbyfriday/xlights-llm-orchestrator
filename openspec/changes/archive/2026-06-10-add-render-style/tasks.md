> **Build result (verified live, CORRECTED after a second pass):** render style is LLM-chosen (`EffectInstruction.render_style`, Generator prompted per the layering guide) with a deterministic fallback, applied at PLACEMENT via `extra_settings[B_CHOICE_BufferStyle]`. The initial 'API normalizes per-model away' diagnosis was WRONG — the client's `+`-for-space GET encoding corrupted every spaced value (`Per+Model+Default` → enum miss → `Default`; `Rotate 180` stored as `Rotate+180`). Fixed: (1) `client._request` encodes GET params with %20; (2) `place_preset` extra_settings now OVERRIDE duplicate keys (xLights honors the first occurrence, and mined looks already carry BufferStyle). Read-back verified: `Per Model Default` sticks via the production path. The interim offline `.xsq` patch + reopen/renderAll machinery was REMOVED (redundant); the refine critic now sees true renders automatically. **189 tests pass.** Display-fill verified (8,583 lit px mid-Plasma).

## 1. Schema + Generator choice
- [x] 1.1 `EffectInstruction.render_style: str = ""` (additive); validate against the known buffer styles
- [x] 1.2 `generator.render_input` + `SectionEffects` schema: ask the Generator to choose `render_style` per effect (per the injected layering guide — group-canvas vs per-model)
## 2. Apply + fallback
- [x] 2.1 `_fallback(effect_type)` map (fill→"Per Model Default", sweep→"Per Preview", On/simple→"Default", unknown→"Per Model Default")
- [x] 2.2 Apply `extra_settings["B_CHOICE_BufferStyle"] = ins.render_style or _fallback(ins.effect_type)` so NO effect is left on the sparse default; code layers (beat/hero/flash) → "Default"
## 3. Tests & verification
- [x] 3.1 LLM-set render_style → applied as B_CHOICE_BufferStyle; unset → fallback (never empty/sparse); invalid → fallback
- [x] 3.2 fallback map sanity (fill→Per Model Default etc.); existing tests pass
- [x] 3.3 Live (gated): re-gen → Generator sets render styles; chorus/peak FILL (per-model where intended); refine can change a dark section's style; Judge stops flagging "completely dark"
