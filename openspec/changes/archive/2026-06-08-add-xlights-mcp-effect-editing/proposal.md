## Why

The read path (change `add-xlights-mcp-readonly`) lets us inspect xLights; the preset library (`add-effect-presets`) gives us valid effects to place — but nothing can yet *write* to a sequence. This change adds the write path: create/edit sequences and place effects. It also **closes the one deferred guarantee** from the preset work — live validation — by replaying presets into a running xLights and confirming `checkSequence` accepts them. It is the prerequisite for any agent that builds a sequence.

## What Changes

- Extend the `xlights-core` client with write methods: `new_sequence`, `open_sequence`, `save_sequence`, `close_sequence`, `add_effect`, `render_all`, `check_sequence`.
- Add a single async **write-lock** in the client that serializes all mutations (xLights has one shared open sequence). Reads stay lock-free.
- Add MCP tools: `xl_new_sequence`, `xl_open_sequence`, `xl_save_sequence`, `xl_close_sequence`, `xl_render_all`, and a **preset-backed `xl_add_effect`** that takes `effect_type + look_id + knob_values + palette_id + target + start_ms/end_ms/layer`, assembles the settings via the `effect-presets` library (per-knob validated), validates the target against the live layout, then places the effect. A gated `xl_add_effect_raw` is the escape hatch.
- Add **live preset validation** (closes `effect-presets` task 6.6): on a disposable scratch sequence, place a preset and `render_all`, reporting acceptance — where accepted = the effect was added (`worked`) and the sequence rendered. Confirmed by live probe: a fresh `newSequence` includes layout models as elements, and `renderAll` returns `{"msg":"Rendered."}` in ~2s.
- Map the write-path error states (`503` "Sequence not open." / "target element doesn't exists.", `504` "unsaved changes") through the existing typed error taxonomy.

**Non-goals (deferred):** the file-based `checkSequence` linter (it opens a *saved* sequence file and returns a report-file path, and blocked when called on the open sequence — defer to a later sequence-QA change); orchestration/agents and the generation pipeline; audio/lyrics; `exportVideoPreview`/visual-critic loop; `batchRender`; controller uploads; parameterized value-curve synthesis and audio-derived curves (this change *live-validates* them later, but does not generate them).

## Capabilities

### New Capabilities
- `xlights-sequence-editing`: Create and edit xLights sequences and place effects via the automation API — serializing mutations, placing preset-backed (and gated raw) effects onto validated targets, and validating presets against a running instance — without silently discarding the user's open work.

### Modified Capabilities
<!-- None. Builds on `xlights-read-access` (reused for target validation) and `effect-presets` (assembly), but changes neither's requirements. -->

## Impact

- **`xlights-core`**: client gains write methods + the async write-lock; new typed handling for "no sequence open" / "unsaved changes".
- **`xlights-mcp`**: new lifecycle + render/check + preset-backed `xl_add_effect` tools; depends on `effect-presets` (`preset_library`) and reuses `get_models` for target validation.
- **Safety:** writes mutate the single open sequence. `new_sequence`'s `force` (which discards open work) is gated behind explicit opt-in; live validation uses a named scratch sequence; destructive operations are surfaced, never implicit.
- **Live xLights required** for the write tools and validation; offline unit tests cover assembly/validation/error-mapping with mocked transport.
- **Closes** `effect-presets` deferred task 6.6 (live replay validation).
