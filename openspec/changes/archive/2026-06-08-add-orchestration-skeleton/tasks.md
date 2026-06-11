> **Build result:** orchestrator package built; **50 hermetic tests pass** (registry routing + no-sampling settings, placeable filtering, full TestModel flow, cache resume, emitter skip/layer-bump/clean-slate). Live `xlo run` ran end-to-end — loaded .env, resolved the key, called claude-opus-4-8 — but the Anthropic **account has no API credits** (400). Code verified to the model call; live placement pending credits or a Gemini re-route. pydantic-graph dropped (deprecated) for plain async stages.

## 1. Package scaffold + model routing

- [x] 1.1 Create `packages/xlights-orchestrator` (pyproject: deps `xlights-core`, `pydantic-ai`; extras `[anthropic]`/`[google]`; optional `logfire`); `src/xlights_orchestrator/`
- [x] 1.2 `models/registry.py` + `models/config.yaml`: role → model spec; defaults (bare IDs) planner=`anthropic:claude-opus-4-8`, worker=`anthropic:claude-sonnet-4-6`, Gemini alternates `google-gla:gemini-2.5-pro`/`gemini-2.5-flash`. Set `AnthropicModelSettings(anthropic_thinking={"type":"adaptive"})`; **never** temperature/top_p/top_k; `effort` only if the settings type exposes it (optional)
- [x] 1.5 CLI/runtime loads `.env` (python-dotenv) for `ANTHROPIC_API_KEY`/`GEMINI_API_KEY`/`XLIGHTS_BASE_URL`
- [x] 1.3 `build_agent(role, output_type, system_prompt)` → a `pydantic_ai.Agent` wired to the routed model
- [x] 1.4 Verify `pip install -e` resolves; `pydantic_ai` + `pydantic_graph` import

## 2. Contracts (pydantic)

- [x] 2.1 `show_plan.py`: `SectionPlan` (time range, target_groups[], effect_family, intensity), `ShowPlan` (sections[]), `EffectInstruction` (effect_type, look_id, knob_values, palette_id, target, layer, start_ms, end_ms)

## 3. Agents

- [x] 3.1 Director agent (planner): compact SongAnalysis summary + group names + placeable effect types + palette tags → `ShowPlan`; system prompt in `prompts/director.md`
- [x] 3.2 Generator agent (worker): one `SectionPlan` + candidate looks (`preset_library.get_looks`) + palettes → `EffectInstruction[]`; system prompt in `prompts/generator.md`
- [x] 3.3 Placeable-effect-type set: catalog types minus a known-rejected set (e.g. `Color Wash`); offer only these to the Director

## 4. Pipeline + effect_emitter

- [x] 4.1 `pipeline/state.py`: `State` dataclass (song_path, song_analysis, available_groups, placeable_types, show_plan, instructions, applied)
- [x] 4.2 `pipeline/run.py`: plain async stages in order — analyze (load cached SongAnalysis; read groups) → design → generate → apply → render → finalize. (No pydantic-graph — its BaseNode/Graph is deprecated in 1.106; revisit a graph engine at ⑦.)
- [x] 4.3 Per-stage artifact caching (keyed by song hash + stage) so a re-run resumes by skipping completed stages
- [x] 4.4 `effect_emitter.py`: clean-slate fresh sequence (no force; settle); apply `EffectInstruction[]` serially via `editing.place_preset`; groups only; track per-`(target,layer)` occupancy → non-overlapping ranges or bump layer; skip rejected/missing; report placed; then `render_all`

## 5. CLI

- [x] 5.1 `cli.py` `xlo run --song <path> [--provider claude|gemini] [--no-save]`: build State, run the Graph, print what was placed, leave sequence open
- [x] 5.2 Refuse clearly if a user sequence is already open (no force)

## 6. Tests & verification

- [x] 6.1 Hermetic flow test with PydanticAI `TestModel`/`FunctionModel`: stub Director→ShowPlan and Generator→EffectInstruction[]; run the graph with a fake/mock client; assert order Analyze→…→Render and that instructions target groups and assemble valid settings
- [x] 6.2 Unit: `effect_emitter` skips rejected effect types / `PresetPlacementError` and continues; placements are non-overlapping per target/layer
- [x] 6.3 Unit: model registry routes a role to Claude vs Gemini purely from config (no code change); `build_agent` returns the right model
- [x] 6.4 Unit: resumability — a re-run reuses cached stage artifacts (skips completed stages) rather than recomputing
- [x] 6.5 Live end-to-end PASSED on **Gemini** (`XLO_PROVIDER=gemini`, gemini-2.5-flash): `xlo run` on a real song → Director produced a 4-section ShowPlan whose boundaries match the audio's Segmentino segments; Generator + emitter placed **9 effects** across prop groups (3 skipped), rendered, saved `LLM_ORCH_SHOW`, left open. (Anthropic path verified to the model call but the account has no credits; Gemini free tier used instead — proving the provider-agnostic routing.)
