## Why

The user maintains a ~5K-token `xlights-sequencing-guide.md` — core philosophy, music→effect→prop mapping, per-prop effect notes, color strategy, a song-structure playbook, and common mistakes. It's directive craft guidance the agents currently never see, so the show only follows it by luck. Putting it in front of the design, generation, and critique agents makes the whole pipeline follow the house style — and the guide already speaks to our open questions (e.g. *"deep blues are dimmer on pixels; pair with white sparkle"*).

## What Changes

- A shared **`sequencing_guide()`** loader: reads the guide once from a configurable path (`XLO_SEQUENCING_GUIDE` env, else the repo-root `xlights-sequencing-guide.md`), best-effort — a missing file returns `""` (clean no-op).
- A **`with_guide(prompt)`** helper: appends a clearly delimited "## SEQUENCING BEST-PRACTICES — apply unless the grounded song data says otherwise" section when a guide exists; returns the prompt unchanged otherwise.
- Wire it into the **Director, Generator, Visual Critic, and Judge** system prompts (after each role's own instructions, so it complements rather than overwrites). The analysis panel / synthesizer (which interpret *music*, not lights) do **not** get it.
- Single user-editable source: edit the `.md`, all four agents update.

**Non-goals:** the music-interpretation agents; per-agent tailoring/splitting of the guide; encoding the guide's principles into deterministic code; packaging the guide into the wheel.

## Capabilities

### Modified Capabilities
- `show-orchestration`: the design, generation, and critique agents apply a user-maintained sequencing best-practices guide (when configured), from a single editable source, with a missing guide as a clean no-op — so the show follows the house style and the critics judge against it.

## Impact

- **`xlights-orchestrator`**: a small `agents/guide.py` (loader + `with_guide`); the Director/Generator/Visual-Critic/Judge factories wrap their system prompt with `with_guide(...)`. The guide goes in the **frozen system prompt** → prompt-cacheable (~5K/call mitigated by caching; the Generator runs ~14×/run).
- **Builds on** the existing `build_agent(role, system_prompt=…)` seam. Complements the grounded prompts and the deterministic palette/beat code; doesn't replace them.
