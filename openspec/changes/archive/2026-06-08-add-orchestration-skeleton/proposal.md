## Why

The foundation is complete — we can read the rig, mine valid presets, place + validate effects, and analyze a song. Nothing yet *connects* them with LLM agents. This change stands up the orchestration harness: an LLM-driven pipeline that turns a real `SongAnalysis` into a placed, rendered xLights sequence. It's deliberately a **skeleton** — one Director + one Generator, sequential — to prove the PydanticAI + pydantic-graph machinery and per-role model routing end-to-end before adding the parallel analysis panel, critics, and refine loop.

## What Changes

- New **`xlights-orchestrator`** package (the project's third package).
- **Per-role model routing** (`models/registry.py` + config): each agent role → a provider model with the right settings; Claude defaults (planner `claude-opus-4-8`, worker `claude-sonnet-4-6`), Gemini alternates — swappable via config, no code change.
- **Two PydanticAI agents** (structured output): a **Director** (SongAnalysis → ShowPlan: per-section intent over chosen prop *groups*) and a **Generator** (a SectionPlan → preset-backed `EffectInstruction`s).
- A **pydantic-graph** pipeline with typed State and sequential nodes: Analyze (load cached SongAnalysis) → Design → Generate → Apply → Render → Finalize, with sqlite persistence for resumability.
- **`effect_emitter`**: serialize placement through the client write-lock, place onto groups with non-overlapping time ranges, and skip effect types xLights won't place.
- A CLI **`xlo run --song <path>`** that runs the pipeline and leaves a generated sequence open in xLights.

**Honors the hard-won constraints:** target **groups** (a fresh sequence has groups as elements, not models); **skip rejected effect types** (e.g. "Color Wash"); **never call `checkSequence`** (it crashes xLights); **clean-slate + paced + no force** (never discard the user's open work); **add-only** placement (non-overlapping, distinct layers).

**Non-goals (later changes):** the parallel analysis panel (analysts + synthesizer) → ⑥; critics + Judge + scoped iterate/refine loop (needs effect remove/replace, which the API lacks) → ⑦; human checkpoints; `exportVideoPreview` visual critique; value-curve synthesis / audio-derived curves; the enrichment audio extractors (④b).

## Capabilities

### New Capabilities
- `show-orchestration`: Drive an LLM pipeline that turns a `SongAnalysis` into a `ShowPlan` and then into validated effect instructions placed onto xLights sequence targets and rendered — with agent roles routable to different model providers, placing only effects xLights accepts, and never discarding the user's open work.

### Modified Capabilities
<!-- None. Consumes audio-analysis, effect-presets, and xlights-sequence-editing without changing their requirements. -->

## Impact

- **New package `xlights-orchestrator`** (deps: `xlights-core`, `pydantic-ai`; provider extras `[anthropic]`/`[google]`; optional `logfire`). Modules: `models/`, `graph/`, `agents/`, `effect_emitter.py`, `show_plan.py`, `cli.py`.
- **Runtime:** the live pipeline needs an LLM API key (`ANTHROPIC_API_KEY` or `GEMINI_API_KEY`) and a running xLights with no sequence open; graph/flow tests are hermetic (PydanticAI `TestModel`, no key).
- **Consumes:** `audio-analysis` (cached SongAnalysis), `effect-presets` (`preset_library`), `xlights-sequence-editing` (write client + `place_preset`).
- **Forward:** the add-only write path means the iterate/refine loop (replace/clear a section) is deferred to ⑦; this skeleton generates once.
