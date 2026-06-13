## Why

Watching carol's arches (user): two stacked chase layers run Left-Right and Right-Left *constantly* — heads perpetually crossing. It would read better as a woven figure: layer 1 goes right while layer 2 goes left, then they **swap each bar** — cross, bounce off the ends, cross back. Today a recipe's static direction is frozen for the whole section; only `bounce` flips, and paired recipes can't counter-phase.

## What Changes

- **Auto counter-phase**: when a weave contains two chase-family recipes with opposite static horizontal directions (`ltr` + `rtl`) on the same group set, the weaver upgrades both to per-bar alternation in opposite phase — layer 1 (L→R, R→L, L→R…), layer 2 (R→L, L→R, R→L…). The LLM's existing crossing-chase habit becomes the woven figure with no prompt dependence.
- **Explicit `alternate` direction value**: per-bar L-R/R-L value flip for any chase-family effect (including ones with native bounce types), phase-staggered by recipe order among same-group `alternate` recipes — so the LLM can also ask for the figure directly.
- Generator prompt note documenting both.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `show-orchestration`: WHEN two beat cells' recipes run opposite horizontal sweeps on the same groups, their directions SHALL counter-phase per bar (swap at bar boundaries) rather than remain statically opposed; an explicit alternate direction SHALL be available per recipe with deterministic phase staggering.

## Impact

- `pipeline/weave.py` only (direction phase in `_valid_recipes`/`direction_setting` call path) + generator prompt line + tests.
- Back-compat: single static-direction recipes unchanged; `bounce` unchanged; the upgrade only fires on the exact opposite-pair pattern.
