## Context

Each agent is built with `build_agent(role, output_type=…, system_prompt=_PROMPT)` where `_PROMPT` is a frozen string (from `prompts/*.md` for Director/Generator; inline for Visual Critic/Judge). The guide is a ~5K-token `.md` the user maintains. The frozen system prompt is the cacheable, stable place for house rules.

## Goals / Non-Goals

**Goals:** load the guide once from a single configurable source; inject into the 4 decision/critique agents' system prompts; clean no-op when absent; hermetic-testable.

**Non-Goals:** interpretation agents; per-agent tailoring; deterministic-code encoding; packaging the guide.

## Decisions

### `agents/guide.py`
- `sequencing_guide() -> str`: resolve the path = `os.environ.get("XLO_SEQUENCING_GUIDE")` or the default `xlights-sequencing-guide.md` (CWD/repo-root). Read it best-effort inside try/except → return text, or `""` on any failure. **Cache** the result in a module-level variable (compute once); expose a way to reset for tests (or read the env each call but cache by path).
- `with_guide(prompt: str) -> str`: `g = sequencing_guide()`; if `g`, return `prompt + "\n\n## SEQUENCING BEST-PRACTICES (apply these unless the grounded song data says otherwise)\n\n" + g`; else return `prompt`.

To keep tests clean (env set per-test), read+cache **keyed by the resolved path** (a dict), so changing `XLO_SEQUENCING_GUIDE` between tests picks up the new file while still caching within a path.

### Wiring
Director (`director.py:16`), Generator (`generator.py:16`), Visual Critic (`visual_critic.py:45`), Judge (`judge.py:30`): change `system_prompt=_PROMPT` → `system_prompt=with_guide(_PROMPT)`. The guide lands AFTER the role's instructions/grounding, so role logic + grounding rules still lead. No change to the synthesizer/analyst factories.

### Caching / cost
The guide sits in the frozen system prompt → cacheable (Gemini implicit; Claude `cache_control`). ~5K tokens/call; the Generator runs ~14×/run + refine, so caching is what keeps this cheap — no code needed beyond placing it in the system prompt (the registry already handles provider caching).

## Risks / Trade-offs

- **Token cost without caching** — ~5K × every Director/Generator/critic call. Mitigated by system-prompt caching; if a provider lacks it, the cost is real but bounded. Could later tailor per agent.
- **Guide vs grounding conflict** — the guide is craft advice; the per-song grounded data must still win (the brief's palette, the analyzed intensities). The injected header says "apply unless the grounded song data says otherwise," and it's appended *after* the role's grounding rules.
- **Path resolution** — CWD-relative default is fragile if `xlo` runs elsewhere; the `XLO_SEQUENCING_GUIDE` env is the robust override. Missing → no-op, so worst case is "guide silently not applied" (logged at debug).
- **Stale module cache** — caching by resolved path means an edited guide is re-read only on a fresh process (fine for a CLI run; tests use distinct tmp paths).

## Open Questions

- Per-agent tailoring (Director gets strategy sections, Generator gets effect/mapping) to cut tokens — deferred; whole-guide first.
- Whether to log when the guide is/ isn't found (debug log) — yes, a one-line debug.
