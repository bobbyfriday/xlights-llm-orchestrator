## Context

Third change. The read client + typed error taxonomy exist (`xlights-read-access`); the preset library + `preset_library.assemble` exist (`effect-presets`). This adds mutation, reusing both.

Grounded in xLights source (`xLightsAutomations.cpp`):
- `addEffect` → requires `CurrentSeqXmlFile != null` (else `503 "Sequence not open."`); target element must exist; params `target, effect, settings, palette, layer, startTime, endTime`; returns `{"worked": bool}`.
- `newSequence` → `503 "Sequence already open."` unless `force`; params `mediaFile, durationSecs, frameMS, view`. **`force` discards open work.**
- `saveSequence` → requires open; `503` if unnamed and no `seq` name given (else SaveAs).
- `closeSequence` → `504 "unsaved changes"` unless `force`; `quiet` for no-op when none open.
- `renderAll` → requires open; returns `{"msg":"Rendered."}` (≈2s on a scratch). **Confirmed live.**
- `checkSequence` → **NOT an open-sequence check.** It takes a `seq` *file name*, `OpenAndCheckSequence(seq)` opens+lints it, returns a report **file path** (`{"output": "..."}`). Called without a valid `seq` it **blocked** (HTTP 000 @ 60s). → **Out of scope** for this change; validation uses `worked` + `renderAll` instead.
- **Element question resolved live:** a fresh `newSequence` includes layout models as elements (`addEffect target=Tree` → `worked:true` immediately), so `get_models` targets are usable on a scratch sequence.

## Goals / Non-Goals

**Goals:**
- Typed client write methods + a mutation lock; preset-backed and gated-raw effect placement.
- Live preset validation that closes `effect-presets` 6.6 without endangering user work.

**Non-Goals:**
- Orchestration/agents, audio, video preview, batch render, uploads, value-curve synthesis.

## Decisions

### Single async write-lock in `core.client`
All mutating methods acquire one `asyncio.Lock` before issuing their request; reads bypass it. xLights has exactly one open sequence, so serialization is correctness, not just safety. The lock lives in the client so both MCP tools and any future in-process caller share it. **Alternative:** lock per tool — rejected; the shared sequence is the resource, not the tool.

### Error taxonomy: disambiguate the overloaded `504` in `_handle`
`addEffect`/`saveSequence` on no open sequence → `503` → already `XLightsResponseError` (message "Sequence not open."). The catch: `504` is **overloaded** — it means *both* "not implemented" (e.g. `prepareAudio`) *and* `closeSequence`'s "Sequence has unsaved changes." The ①-era client maps **all** `504 → XLightsNotImplemented` (client.py), which would mis-classify the unsaved case. **Fix (modifies the read-client `_handle`):** branch `504` on message — body containing "unsaved" → `XLightsUnsavedChanges` (subclass of `XLightsResponseError`); otherwise `XLightsNotImplemented`. This is the one place we deliberately message-parse (unavoidable: `504` has two real meanings). Also add a distinct `XLightsTargetMissing` for `addEffect`'s `503 "target element doesn't exists."`. **Alternative:** treat all `504` as not-implemented — rejected; misclassifies unsaved-changes.

### Preset-backed `add_effect` assembles via the library
The high-level tool takes `(effect_type, look_id, knob_values, palette_id, target, start_ms, end_ms, layer)`. It resolves the look + palette from `preset_library` (needs new **by-id getters** `get_look(type, look_id)` / `get_palette(palette_id)` — today only list getters exist), calls `assemble()` (validates knobs), then `add_effect(...)`. Raw path (`xl_add_effect_raw`) skips assembly. **Validation layers and what they can/can't guarantee:**
- `target ∈ get_models()` is a **cheap pre-filter only** — the real gate is that the target is an *element of the open sequence* (`addEffect` resolves `_sequenceElements.GetElement(target)`, returning `503 "target element doesn't exists."` otherwise → `XLightsTargetMissing`). Layout membership ≠ sequence element.
- timing ≥ 0 (and within sequence bounds).
- **`worked` flag**: `addEffect` returns HTTP `200` with `{"worked":"true|false"}`. `worked=false` is a *silent failure* (unknown effect, bad layer, or an **overlapping effect on the layer**). `add_effect` returns it; `place_preset` and `validate_preset` MUST treat `worked=false` as failure, not success.
**Alternative:** let agents pass settings strings — rejected; reintroduces the hallucination risk the preset library removes.

### Overlap and layering
`addEffect` rejects (`worked=false`) an effect that overlaps an existing one on the same layer. Callers must use non-overlapping time ranges per layer, or distinct layers (`addEffect` auto-creates layers up to the requested index). Encoded as a caller constraint; the future refine loop must account for it.

### Lifecycle ops are mutations → all take the write-lock
`new_sequence`, `open_sequence`, `load_sequence`, `save_sequence`, `close_sequence`, `add_effect`, `render_all` all change shared xLights state (`CurrentSeqXmlFile` / the open sequence) and go through `_mutate` (the single lock). Only the read commands stay lock-free.

### Safety: never discard open work implicitly
`new_sequence` exposes `force` only via an explicit boolean the caller must set; default refuses when a sequence is open. `close_sequence` defaults to non-force (so unsaved changes block); `force`/`quiet` are explicit. Live validation requires a **clean slate** (no user sequence open) and **never forces** over user work; it creates a disposable, unsaved scratch sequence (a new sequence is unnamed until saved — we never save it), and discards it with `close_sequence(force=True)` after capturing results (the scratch's own changes are disposable). **Alternative:** validate on whatever is open, or force it closed — rejected; clobbers user work.

### Live preset validation flow (closes effect-presets 6.6)
`validate_preset(look, knob_values, palette, target)`:
1. Refuse if a user sequence is open (clean slate required; never force).
2. `new_sequence` (scratch, short duration, default frameMS).
3. Resolve a usable `target` — it must be an *element* of the scratch sequence. Whether `new_sequence` populates elements is the key live unknown (see Open Questions); the flow treats `XLightsTargetMissing` as "no usable target" rather than a hard crash.
4. preset-backed `add_effect` on `target` over a small window; **`worked=false` → not accepted**.
5. `render_all` (must succeed).
6. Report `{accepted, worked, rendered}` (accepted = worked && rendered); `close_sequence(force=True)` the scratch.
This confirms mined presets — and *novel* knob combinations — are accepted and renderable by the running xLights, and exercises the key-order assumption from `effect-presets`. (Deeper lint via the file-based `checkSequence` is deferred to a later QA change.)

## Risks / Trade-offs

- **Clobbering user work** (highest) → `force` gated; scratch-sequence isolation; refuse-by-default when a sequence is open.
- **`504` overload** (not-implemented vs unsaved-changes) → disambiguate by message; dedicated `XLightsUnsavedChanges`.
- **Scratch sequence needs a real target model** → use a model returned by `get_models`; if the layout is empty, validation reports "no target available" rather than failing opaquely.
- **Knob-independence (from `effect-presets`)** → this change is precisely the live check that catches an invalid novel combination via `check_sequence`.
- **Render time** → `render_all` on a tiny scratch sequence is fast, but on the user's *real* open sequence it can exceed the read client's 30s default; give the write client a generous (configurable) timeout for render/check.
- **No remove/replace in the write set (forward risk)** → the automation API exposes effect *add* and `setEffectSettings`/`getEffectIDs` (modify existing), but no obvious *delete/clear*. Re-running `add_effect` to redo a region would append and overlap (→ worked=false). This change's scope is place + validate, so it's not a blocker here, but the **orchestrator's scoped-refine loop needs replace/clear** — flag it prominently for that change (it may require `setEffectSettings` on existing effect IDs, or a different clearing strategy). Captured here so the iterate loop isn't designed assuming clean re-placement.

## Open Questions

- Exact `newSequence` behavior with empty `mediaFile` and minimal params (confirm a no-media scratch sequence is accepted) — verify live during implementation.
- Whether `checkSequence` returns machine-parseable structure or text to be parsed — capture a real response and shape the result accordingly (capture-first, as in change ①).
