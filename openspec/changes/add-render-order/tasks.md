## 1. Ordering + view
- [x] 1.1 `canonical_order(names)` in layout_semantics: beds → bands/sides → frame (OUTLINE/WINDOWS/ICICLES/PATH) → rhythm (ARCHES/CANES/MINITREES + LTR) → plain groups → models → FOCAL/matrices → accents (SNOWFLAKES/SPINNERS/stars) last; nulls excluded
- [x] 1.2 Layout patcher writes/updates `<view name="SEM Master" models="...">` with the canonical order (idempotent)
## 2. Use + finalize
- [x] 2.1 Emitter `new_sequence(view="SEM Master")` with graceful fallback when the view isn't loaded
- [x] 2.2 `patch_xsq_render_order(xsq)` at finalize: reorder model rows canonically in DisplayElements+ElementEffects (timing rows preserved; atomic; best-effort)
## 3. Tests & verification
- [x] 3.1 canonical_order precedence (bed < frame < rhythm < focal < accents); nulls dropped
- [x] 3.2 view authored idempotently; xsq reorder sorts model rows, keeps timing, re-parses valid
- [ ] 3.3 Live: after next restart, new sequences inherit the view order; finalized .xsq rows are canonical
