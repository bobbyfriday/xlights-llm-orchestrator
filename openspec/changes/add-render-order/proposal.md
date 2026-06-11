## Why
Render precedence (which row wins where props overlap) is currently legacy accident: the master view inherited an arbitrary order — old groups at the top, a null placeholder near the bottom (the winning position). The cookbook's stack tables and the layering guide §7 treat master-view order as a deliberate instrument (beds painted over, features/accents winning). With beds (SEM_ALL/LESS_*) now under features routinely, precedence must be intentional.

## What Changes
- **Canonical precedence** (`canonical_order`): beds (ALL/LESS/bands/sides) at the TOP (render first, get painted over) → frame/rhythm/role groups → plain groups/models → FOCAL + matrices → accents (snowflakes/spinners/stars) at the BOTTOM (win overlaps). Nulls excluded.
- **A `SEM Master` view** authored into `rgbeffects.xml` by the layout patcher with that order; `new_sequence` uses it when available (fallback to default if the view isn't loaded yet — it activates on the next xLights restart).
- **Finalize `.xsq` reorder**: the saved sequence's element rows are reordered canonically (timing rows preserved), so the final file is correct even before the view is active.

**Non-goals:** per-section dynamic reordering; strobe-overlay groups (no dedicated strobe props yet).

## Capabilities
### Modified Capabilities
- `show-orchestration`: sequences carry a deliberate render precedence — beds under, features and accents over — via a canonical master view and a finalize reorder.
