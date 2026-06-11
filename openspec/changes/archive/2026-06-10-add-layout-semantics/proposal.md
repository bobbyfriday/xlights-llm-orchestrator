## Why
We've been choreographing against an ad-hoc group taxonomy (`04_BEAT`, `08_HERO`, `02_GEO`), and it's the root of the dark-chorus problem: no clean role/ensemble target means "light the whole display on the chorus" isn't expressible. `xlights-layout-semantics-spec.md` defines a principled model: classify every model into a **role**, derive **capability + spatial** attributes, and create prefixed **`SEM_` groups** (role / ordered / band / side / ensemble) + a `layout_semantics.json` manifest the planner consumes. Per the user's decision, this also **removes the numbered taxonomy** (`01_`–`08_`, 47 groups) and keeps the plain hand-made groups.

## What Changes
- A **layout-semantics generator**: parse `rgbeffects.xml` → classify models (DisplayAs → role; tree node-count; name heuristics; existing-group hints; low-confidence → review) → spatial derivation (normalize world positions → bands ROOF/MID/GROUND, sides L/C/R, sweep order, focal flags) → build the `SEM_` groups → write `layout_semantics.json`.
- **Edit `rgbeffects.xml` offline** (xLights closed; backup first; atomic; idempotent — re-run replaces only `SEM_` groups): add the `SEM_` groups, remove the 47 numbered groups, leave the plain groups untouched.
- **Switch the orchestrator to `SEM_` targets** (coupled — removing numbered groups breaks the old references): rhythm → `SEM_ARCHES`/`SEM_ACCENTS`, hero → `SEM_FOCAL`, call-response → `SEM_SIDE_LEFT/RIGHT`, full display → `SEM_ALL`. The targetable-group probe + manifest feed the Director.

**Non-goals:** the LLM classification fallback (v1 is deterministic + a review list); submodel `SEM_OUTLINE_SEGMENTS`; the role-color/sweep validation render (manual); driving the xLights UI (we edit the XML).

## Capabilities
### Modified Capabilities
- `show-orchestration`: the planner targets semantic role/ensemble groups (`SEM_*`) derived from the layout, instead of an ad-hoc taxonomy — enabling whole-display ensembles (fixing sparse coverage), role-coherent effects, and ordered sweeps.

## Impact
- **`xlights-orchestrator`/`core`**: a layout-semantics module (classify + spatial + group build), an offline `rgbeffects.xml` patcher (backup + add SEM_ + remove numbered), a `layout_semantics.json` manifest; the beat/hero/choreography targeting switches to `SEM_`.
- **Destructive on `rgbeffects.xml`** (backed up; xLights must be closed). Builds on the offline-`.xsq`-patch pattern and `targetable_groups`.
