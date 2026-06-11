## 1. Classification + spatial
- [x] 1.1 Parse `rgbeffects.xml` models (name, DisplayAs, parm1-3, WorldPos, StringType, subModels)
- [x] 1.2 Classify roles: DisplayAs map (Arches→ARCH, Matrix→MATRIX, Star→STAR, Tree→MEGA/MINI by node count, Single Line/Custom→name heuristics + group hints); low-confidence → review
- [x] 1.3 Capability tags (2D_SURFACE/2D_RADIAL/LINEAR_HIGH/LINEAR_LOW/POINT/SPECIAL) from role+geometry
- [x] 1.4 Spatial: normalize WorldPos → x,y in [0,1]; bands ROOF/MID/GROUND; sides L/C/R; sweep order per multi-role; focal flags; exclude far-outliers (>2x bbox) → review
## 2. SEM_ groups + manifest
- [x] 2.1 Build SEM_ groups: role, ordered `_LTR`, band, side, ensemble (SEM_ALL/FOCAL/ACCENTS/HOUSE/YARD) per spec membership rules
- [x] 2.2 Emit `layout_semantics.json` (props + groups + review)
## 3. rgbeffects.xml edit (offline, xLights CLOSED)
- [x] 3.1 Backup `rgbeffects.xml` (timestamped); atomic write
- [x] 3.2 Add SEM_ `<modelGroup>` elements; remove the 47 numbered (`0[1-8]_`) groups; leave plain groups; idempotent (replace SEM_ on re-run)
## 4. Orchestrator switch to SEM_
- [x] 4.1 Beat layer rhythm groups: `04_BEAT_*` → `SEM_ARCHES`/`SEM_ACCENTS`; hero `08_HERO_*` → `SEM_FOCAL`; call-response → `SEM_SIDE_*`; ensemble/full → `SEM_ALL`
- [x] 4.2 targetable_groups + Director available_groups use the SEM_ set (+ manifest roles)
## 5. Tests & verification
- [x] 5.1 Classification on synthetic models (DisplayAs + heuristics → roles; tree node-count split; outliers → review)
- [x] 5.2 Spatial: normalization, bands, sides, sweep order, focal
- [x] 5.3 rgbeffects patch: SEM_ added, numbered removed, plain kept, idempotent, backup made, re-parses valid
- [x] 5.4 manifest schema; low-confidence in review
- [ ] 5.5 Live (gated, xLights CLOSED): run generator → reopen xLights → SEM_ groups present + correct; numbered gone; role-color test frame
