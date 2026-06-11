## Why
The refine loop shipped dark choruses for days while scoring **objective 84–86 / advisory 100** — because no objective metric measures whether the display is actually LIT. The Judge's text described "completely black" climaxes, but darkness was advisory-only, so the loop never gated on it. Now that render styles apply at placement, the offline `.fseq` reflects the true show in-loop — the objective score can finally have eyes.

## What Changes
- A **coverage QA metric** (`qa/coverage.py`): per high-energy section, sample frames from the rendered `.fseq` (via an injected sampler) and score how lit the display is relative to the song's own peak and the section's intensity. Quiet sections are NOT penalized (restraint is intentional); a loud section rendering near-black is an **error finding** and drags the objective down.
- `qa.evaluate` gains an optional `sampler` — with it, objective = mean(sync, placement, **coverage**); without (hermetic tests, no preview), behavior is unchanged.
- The refine loop saves the sequence before evaluating (fresh `.fseq`) and wires the sampler from the same paths the visual critique uses. A dark chorus now **gates**: the loop keeps revising instead of accepting.

**Non-goals:** color/palette correctness scoring (visual critic's job); per-prop coverage attribution; changing the visual critique.

## Capabilities
### Modified Capabilities
- `show-orchestration`: the objective QA score includes rendered lit-coverage for high-energy sections, so the refine loop gates on dark sections instead of shipping them.

## Impact
- **`xlights-orchestrator`**: `qa/coverage.py` (pure given a sampler); `qa.evaluate(sampler=...)`; refine-loop wiring (save + sampler) in `run.py`.
- **Builds on** the offline preview renderer (visual critique paths) and the render-style fix (the `.fseq` is finally truthful in-loop).
