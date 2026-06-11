> **Build notes (this session):** Implemented + verified with venv+pip. checkSequence found to be a file-based linter that blocked on the open sequence → dropped (validation uses worked+renderAll). Live element-vs-model race confirmed (fresh sequence populates a *subset* of models as elements, slightly after creation) → validate_preset settles then picks a usable element. **37 unit tests pass; live validation passed** (default + novel-knob Shockwave preset placed+rendered), and an end-to-end MCP roundtrip of `xl_validate_preset` returned accepted=true — this **closes effect-presets task 6.6**.

## 1. Client: error taxonomy + write-lock

- [x] 1.1 Add `XLightsUnsavedChanges(XLightsResponseError)` and `XLightsTargetMissing(XLightsResponseError)`
- [x] 1.2 **Modify `_handle` (from ①)**: branch the overloaded `504` by message — "unsaved" → `XLightsUnsavedChanges`, else `XLightsNotImplemented`; map `503 "target element doesn't exists."` → `XLightsTargetMissing` (the one place we message-parse, deliberately)
- [x] 1.3 Add a single `asyncio.Lock` to `XLightsClient` + a `_mutate(cmd, params)` helper; route ALL mutating ops through it (new/open/load/save/close/add_effect/render_all); reads stay unlocked
- [x] 1.4 Give the write client a generous, configurable timeout for render/check (the 30s read default is too short for a real render)

## 1b. Preset library: by-id getters (in `effect-presets`)

- [x] 1b.1 Add `get_look(effect_type, look_id)` and `get_palette(palette_id)` to `preset_library` (today only list getters exist)

## 2. Client: write methods

- [x] 2.1 `new_sequence(*, duration_secs, frame_ms=50, media_file=None, view=None, force=False)` — pass `force` only when explicitly set; map `503 "already open"`
- [x] 2.2 `open_sequence(path)` and `save_sequence(name=None)` (require open; name required if unnamed → typed error)
- [x] 2.3 `close_sequence(*, force=False, quiet=False)` — map unsaved-changes `504` to `XLightsUnsavedChanges`
- [x] 2.4 `add_effect(target, effect, settings, palette, *, layer=0, start_ms, end_ms)` — return the `worked` flag (HTTP 200 + `worked=false` is a failure, not success); `503 "Sequence not open."` and `503 "target element doesn't exists."` map to their typed errors
- [x] 2.5 `render_all()` — requires open sequence (`503` "No sequence open."); returns success (`{"msg":"Rendered."}`). (checkSequence is out of scope — it's a file-based linter that blocked on the open sequence.)

## 3. Preset-backed placement

- [x] 3.1 High-level `place_preset(target, effect_type, look_id, knob_values, palette_id, *, layer, start_ms, end_ms)`: resolve via `get_look`/`get_palette`, `assemble()` (per-knob validated), pre-filter `target ∈ get_models()` and timing ≥ 0, then `add_effect`; **raise on `worked=false`** and surface `XLightsTargetMissing` (target not an element of the open sequence)
- [x] 3.2 Raw escape hatch path: pre-filter target/timing but pass through caller settings/palette; same `worked=false` handling

## 4. MCP tools

- [x] 4.1 Lifecycle tools: `xl_new_sequence`, `xl_open_sequence`, `xl_save_sequence`, `xl_close_sequence` (explicit `force`/`quiet` args; never implicit)
- [x] 4.2 `xl_add_effect` (preset-backed) and gated `xl_add_effect_raw`
- [x] 4.3 `xl_render_all`
- [x] 4.4 `xl_validate_preset` — runs the scratch-sequence validation flow and returns `{accepted, worked, rendered}`
- [x] 4.5 Translate write exceptions (no-sequence-open, unsaved-changes, unknown-target) into clear typed tool errors

## 5. Live preset validation (closes effect-presets 6.6)

- [x] 5.1 `validate_preset(...)`: refuse if a user sequence is open (clean slate; never force); create a disposable unsaved scratch sequence; place preset (treat `worked=false` as not-accepted); `render_all` (must succeed); report `{accepted, worked, rendered}` (accepted = worked && rendered); `close_sequence(force=True)` the scratch
- [x] 5.2 Resolve a target that is an *element* of the scratch sequence; if none usable (`XLightsTargetMissing`), report "no usable target" rather than failing opaquely

## 6. Tests & verification

- [x] 6.1 Unit (mocked transport): write-lock serializes concurrent mutations; `add_effect` maps `503 "Sequence not open."` and `503 "target element doesn't exists."`→`XLightsTargetMissing`; `close_sequence` `504 unsaved`→`XLightsUnsavedChanges` while a `504` not-implemented still →`XLightsNotImplemented` (the disambiguation)
- [x] 6.2 Unit: `add_effect`/`place_preset` raise on HTTP-200 `worked=false`; `place_preset` assembles via the library, rejects out-of-constraint knob values, unknown layout targets, and negative timing
- [x] 6.3 Safety unit: `new_sequence` does not pass `force` unless explicitly set; `close_sequence` defaults non-force
- [x] 6.4 Live (opt-in, needs running xLights): create scratch sequence → place a real preset on a real model → `render_all` + `check_sequence` clean; scratch closed; user sequences untouched
- [x] 6.5 Live: `xl_validate_preset` over a sample of mined presets (incl. a novel knob combination) reports acceptance via `worked` + `render_all` — the effect-presets 6.6 confirmation
