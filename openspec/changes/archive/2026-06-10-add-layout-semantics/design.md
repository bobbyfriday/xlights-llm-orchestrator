## Context
81 models in `rgbeffects.xml` (single-line `<model DisplayAs name parm1-3 WorldPosX/Y/Z StringType>`), 88 groups (47 numbered `0[1-8]_` to remove, ~41 plain to keep), all with world positions (X −907..430, Y −53..1083). `<modelGroup name="X" models="a,b,c"/>`. Reuse the offline-XML-patch pattern (backup + atomic ET write) from timing tracks.

## Goals / Non-Goals
**Goals:** deterministic role/capability/spatial classification → SEM_ groups + manifest; safe idempotent rgbeffects edit (backup, xLights closed); orchestrator targets SEM_. **Non-Goals:** LLM fallback (v1 deterministic + review); submodel segments; UI-driven creation; validation render (manual).

## Decisions
### Classification (deterministic; spec §3 order)
DisplayAs map: Arches→ARCH, Matrix/Vert Matrix/Horiz Matrix→MATRIX, Star→STAR, Icicles→ICICLES, Candy Canes→CANE, Spinner→SPINNER, Window Frame→WINDOW. Tree 180/360/Flat → node count (parm1×parm2×parm3 estimate or `parm2`): ≥600→MEGA_TREE else MINI_TREE (or sole largest→MEGA). Single Line/Custom → name heuristics (roof/gutter/eave/column/garage→OUTLINE; window/door→WINDOW; flood/wash→FLOOD; flake→SNOWFLAKE; face/sing→SINGING_FACE; sign/tune→SIGN; drive/walk/path/fence→PATH) → existing-group-name hints → else CUSTOM_PROP at confidence<0.8 → review. Capability from role (MATRIX→2D_SURFACE; MEGA_TREE/SPINNER/STAR→2D_RADIAL; OUTLINE/PATH→LINEAR_HIGH; ARCH/CANE/ICICLES→LINEAR_LOW; FLOOD→POINT; SINGING_FACE→SPECIAL).
### Spatial
bbox over models EXCLUDING far-outliers (|pos| > 2× bbox span → review/parked). Normalize x,y∈[0,1] (audience view; y ground→top). Bands by y (cuts 0.33/0.66). Sides by x (<0.45 L, ≤0.55 C, >0.55 R). Sweep order = sort by x within each multi-instance role. Focal = MEGA_TREE/MATRIX/large-area.
### SEM_ groups (spec §5)
role groups (multi-instance only), `_LTR` ordered (members in sweep order), `SEM_BAND_*`, `SEM_SIDE_*`, ensembles (`SEM_ALL`=all except SINGING_FACE/SIGN; `SEM_FOCAL`; `SEM_ACCENTS`=non-focal non-outline; `SEM_HOUSE`=OUTLINE+WINDOW+ICICLES; `SEM_YARD`=GROUND minus FLOODS). `<modelGroup name="SEM_X" models="...">`.
### rgbeffects edit
Backup `rgbeffects.<ts>.bak`; ET parse; remove `<modelGroup>` where name matches `^0[1-8]_` OR `^SEM_` (idempotent); append the new SEM_ groups; atomic temp+replace. **xLights MUST be closed** (it rewrites the file from memory on exit) — guard: warn/abort if the orchestrator detects xLights is running.
### Orchestrator switch
`beats.py` BEAT_GROUP_PREFIX `04_BEAT`→ rhythm = `SEM_ARCHES`/`SEM_ACCENTS`; HERO_PREFIX `08_HERO`→`SEM_FOCAL`; GEO left/right→`SEM_SIDE_LEFT/RIGHT`; key-moment flashes + Director "full display" → `SEM_ALL`. `targetable_groups` still probes live groups (now SEM_ + plain).

## Risks / Trade-offs
- **xLights clobbers the edit if open** → must be closed; abort if running.
- **Destructive** → timestamped backup + atomic write; numbered removal is the user's explicit choice.
- **Classification errors** → low-confidence → review list (spec §7); the 33 Custom models are the risk; name/group heuristics + a manual review.
- **Coupling** → orchestrator SEM_ switch lands in the SAME change so generation doesn't break.
- **Normalization outliers** (X=−907) → exclude far-parked models from bbox + flag in review.
## Open Questions
- Node-count for Custom (CustomModel grid) vs parm estimate — approximate for the tree mega/mini + focal; refine if misclassified.
- Exact SEM_ rhythm group for the beat chase (SEM_ARCHES the canonical "drummer" per the guide) vs SEM_ACCENTS — start SEM_ARCHES, fall back SEM_ACCENTS.
