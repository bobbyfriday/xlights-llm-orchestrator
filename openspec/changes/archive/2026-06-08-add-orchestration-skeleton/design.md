## Context

The harness that ties the foundation together. Third package, `xlights-orchestrator`. Consumes `audio-analysis` (SongAnalysis), `effect-presets` (`preset_library`), `xlights-sequence-editing` (write client + `editing.place_preset`). Deliberately a **skeleton**: one Director + one Generator, sequential — prove PydanticAI + pydantic-graph + model routing end-to-end; defer the parallel panel, critics, and refine loop.

Grounded this session: `pydantic-ai`/`pydantic-graph` **1.106** installed (`Agent`/`TestModel`/`FunctionModel`/`AnthropicModelSettings` present; `BaseNode`-`Graph` deprecated); Claude model IDs/params confirmed via the `claude-api` skill (see [[llm-auth]] — orchestrator needs its own key; an `ANTHROPIC_API_KEY` is now in `.env`).

Constraints carried from project memory (`xlights-automation-quirks`, `preset-corpus`):
- Generate onto **groups** (fresh sequence has groups as elements, not models).
- **Skip effect types xLights rejects** (Color Wash → worked=false).
- **Never `checkSequence`** (modal + re-entrant HTTP → crash). Feedback = worked-flag + renderAll.
- **Clean-slate, paced, no force**; element population is racy (settle/retry — reuse `editing.place_preset`/`validate_preset` patterns).
- **Add-only** placement → non-overlapping times / distinct layers; no replace/clear (refine loop is ⑦).

## Goals / Non-Goals

**Goals:** an `xlo run --song` that produces a placed, rendered sequence from a real SongAnalysis; provider-agnostic role routing; hermetic flow tests without an API key.

**Non-Goals:** parallel analysis panel (⑥), critics/Judge/refine loop (⑦), checkpoints, video critique, value-curve synthesis, enrichment extractors.

## Decisions

### PydanticAI agents with structured output, model from a registry
Each agent is a `pydantic_ai.Agent(model, output_type=<pydantic>, system_prompt=...)`. `models/registry.py` maps a **role** → a model spec (provider + id + `ModelSettings`) from `models/config.yaml`; `build_agent(role, output_type, prompt)` wires it. **Defaults (confirmed via the claude-api skill — bare IDs, no date suffix):** planner `anthropic:claude-opus-4-8`, worker `anthropic:claude-sonnet-4-6`; Gemini alternates `google-gla:gemini-2.5-pro`/`gemini-2.5-flash` (verify IDs at build). **Claude settings:** `AnthropicModelSettings(anthropic_thinking={"type":"adaptive"})`; **never** set `temperature`/`top_p`/`top_k` (removed → 400). `effort`/`output_config` passthrough in PydanticAI 1.106 is **unverified** — set thinking now; treat `effort` as an optional tuning knob (default behavior is fine), wire it only if the settings type exposes it. Re-routing a role = editing config. **Alternative:** hardcode models — rejected (provider-agnosticism is a project requirement).

### Load `.env`
The CLI loads `.env` (python-dotenv) so `ANTHROPIC_API_KEY`/`GEMINI_API_KEY` and `XLIGHTS_BASE_URL` are available without manual `export`. Hermetic tests need no key (TestModel).

### Two agents (skeleton)
- **Director** (planner): input = a compact view of `SongAnalysis` (sections, tempo, key, energy) + the available **group** names (from `get_models` groups) + the **placeable effect types** + palette tags. Output = `ShowPlan` (sections each with target groups, effect family, intensity). Keep the input compact (don't dump every beat/onset — summarize) to control tokens.
- **Generator** (worker): input = one `SectionPlan` + candidate looks for the chosen effect family (`preset_library.get_looks`) + palette options. Output = `EffectInstruction[]` (effect_type, look_id, knob_values, palette_id, target group, start/end ms, layer).

### Pipeline: plain async stages + typed State (no graph engine yet)
**Grounded:** `pydantic-graph`'s `BaseNode`/`Graph`/`StatePersistence` are **deprecated in 1.106** (removed/repurposed in v2). A graph engine is also YAGNI for a *sequential* skeleton. So the pipeline is plain async functions over a typed `State` dataclass — `State{ song_path, song_analysis, show_plan, instructions, applied, available_groups, placeable_types }` — run in order: **analyze** (load cached SongAnalysis via `AudioAnalyzer`; read groups) → **design** (Director) → **generate** (Generator per section) → **apply** (`effect_emitter`) → **render** (`client.render_all`) → **finalize** (leave open; optional save). **Resume** = each stage's output is cached to disk (keyed by song hash + stage), so a re-run skips completed stages. The parallel fan-out (⑥) and refine cycle (⑦) slot in without reshaping `State`; adopt a graph engine (PydanticAI's `GraphBuilder`, or successor) **then**, when cycles actually justify it. **Alternative:** use `GraphBuilder` now — rejected (immature for a linear flow; avoid building on a just-deprecated API mid-churn).

### `effect_emitter` — safe additive placement
Creates a fresh sequence (clean-slate, no force; settle), then applies `EffectInstruction[]` **serially** via `editing.place_preset` (which validates target ∈ layout, assembles settings, checks worked-flag). Targets **groups**; tracks per-`(target, layer)` time occupancy and assigns **non-overlapping ranges or bumps to a new layer** so nothing needs removal (two effects on one group → distinct layers); on `PresetPlacementError`/`XLightsTargetMissing`/rejected type → **skip and continue**, recording what was placed. Then `render_all`. Reuses the write-lock in `core.client` (serialized mutations).

### Placeable-effect-type filtering
Before planning, derive the set of placeable effect types (catalog types minus a known-rejected set, e.g. `Color Wash`; can be confirmed via `editing.validate_preset` once per type in a later pass). The Director is only offered placeable types, so it can't plan an unplaceable effect.

### Testing with PydanticAI TestModel (hermetic)
PydanticAI's `TestModel`/`FunctionModel` let agents return canned structured outputs with no network. Flow tests run the whole graph with stubbed Director/Generator outputs and a mocked/!live client (or a fake emitter) to assert: graph order, instructions are well-formed and target groups, rejected types are skipped. The **live** end-to-end (`xlo run`) needs a real key + xLights and is opt-in.

### CLI
`xlo run --song <path> [--provider claude|gemini] [--no-save]` builds the State, runs the Graph, prints what was placed, leaves the sequence open.

## Risks / Trade-offs

- **Token bloat** feeding SongAnalysis to the Director → pass a *summary* (sections + tempo/key/energy envelope), not raw beats/onsets/chords lists.
- **Agent emits an unplaceable/oversized plan** → Generator output validated by `preset_library`; emitter skips rejected placements; non-overlapping scheduling prevents add-only conflicts.
- **Element-population race** on the fresh sequence → reuse the proven settle/retry from `validate_preset`; target groups (reliably elements).
- **No refine loop yet** → a bad section can't be redone in-place (add-only); acceptable for a skeleton; ⑦ adds replace/clear + iterate.
- **Live run cost/safety** → one Director + N small Generator calls; clean-slate + no `checkSequence` keeps xLights stable.

## Open Questions

- ShowPlan granularity: one effect per (section × group), or allow layered motifs per group? Start with one effect per (section, group); revisit in ⑥.
- How to schedule non-overlapping times across sections vs layers — default: one section = one time window; multiple groups in a section = same window on their own elements (distinct targets, so no overlap). Confirm during build.
- Whether to confirm placeable effect types live (via `validate_preset`) at startup or ship a static known-rejected set — start static, make it a cached probe later.
