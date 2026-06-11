## Context
`qa.evaluate(instructions, analysis, plan, applied, groups)` → objective = mean(sync, placement); the Judge saw dark choruses but nothing objective measured them. The offline `PreviewRenderer` reads the `.fseq` (sandbox path, resolved by `pipeline/visual.py`); render styles now apply at placement so the in-loop `.fseq` is truthful (after a save).

## Goals / Non-Goals
**Goals:** pixel-based lit-coverage per high-energy section; objective gating; hermetic-safe (sampler injected, None → unchanged). **Non-Goals:** color correctness; per-prop attribution; visual-critique changes.

## Decisions
### `qa/coverage.py: evaluate(plan, sampler) -> (score, findings)`
`sampler(t_ms) -> int` (lit-pixel count). Per section: sample 25/50/75% through, take the MAX (effects pulse). Normalize by the song-wide peak across all samples. Only sections with `intensity ≥ 0.5` are scored (darkness below that is restraint). Section score = `min(1, observed_frac / (0.6 × intensity))` — a loud section should reach ~60% of the song's own peak lit count, scaled by its intensity. Sections under half their expectation get an `error` finding (`metric="coverage"`, `section_index` set, objective=True). Score = round(100 × mean(section scores)); no scorable sections or sampler=None → (100, []).
### Wiring
`qa.evaluate(..., sampler=None)`: objective = mean(sync, placement[, coverage if sampler]); subscores += coverage. `run.py`: build `sampler` next to the visual critique (same `_resolve_fseq` + rgbeffects/networks paths; lazy — construct the renderer per call so it reads the current `.fseq`); `_refine_loop(…, sampler, save_as)`: `await client.save_sequence(save_as)` before each evaluation when a sampler exists (fresh `.fseq`), pass sampler through.

## Risks / Trade-offs
- **Cost:** ~3 frames × scored sections per iteration (~1–3s) + a save — same order as the visual critique. Acceptable.
- **Peak normalization** is relative to this song's own brightest moment — robust across layouts, but a uniformly-dim show scores well; the brightness pass already pushes absolute levels.
- **Stale fseq** if save is skipped → sampler reads the previous iteration; the save-before-evaluate guard covers the loop path; the initial evaluation happens after the first apply+save.
## Open Questions
- The 0.6 expectation factor and the 0.5 intensity floor — tune against real runs.
