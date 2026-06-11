## 1. Contracts + curve primitives

- [x] 1.1 `show_plan.py`: `CellRecipe` + `SectionWeave` (all fields defaulted); `SectionEffects.weave: SectionWeave|None = None`
- [x] 1.2 `value_curves.py`: `motion_curve_setting(effect_type, curve, start, end)` with the corpus-verified `E_VALUECURVE_*` key map + per-param ranges; unknown pairs return `{}`

## 2. The weaver

- [x] 2.1 `pipeline/weave.py`: `expand_weave(section, weave, rhythm, intensity, available_groups)` — beat-snapped slots (`cell_beats`, partial-cell merge), alternation patterns (chase/pingpong/all/sparse), per-cell palette/render-style/speed/brightness via existing helpers, blend on upper layers only, transitions, `cell_budget` downsampling, layer cap, bed role as one section-spanning placement
- [x] 2.2 `fallback_weave(section, available_groups)`: SingleStrand-chase carrier on the rhythm pool + sparse texture from section effect_types
- [x] 2.3 Wire into `run.py` generate + `_refine_loop._regen`: expand weave (LLM's or fallback) after the section's LLM instructions; tag `section_index`; `clamp_hard_caps` over the combined stream

## 3. Rebalance + taxonomy + QA

- [x] 3.1 `place_beat_accents(..., carrier_covers=False)`: skip the every-beat chase when True (sparkle + hero onsets unchanged); run.py passes coverage from the section's weave
- [x] 3.2 `normalize_durations`: cell-able class (motion types >2 bars chopped to 2-bar cells; bed-role/bed-group exceptions); catalog §2.1 → v0.3
- [x] 3.3 `qa/rules.py`: per-section motion-share advisory (intensity ≥0.5, share <30%) — advisory only, objective unchanged

## 4. Generator prompt

- [x] 4.1 `render_input`: remove the dead duplicated scene-note block (the "blend modes are not settable" claim); add the WEAVE ask documenting recipe fields, carrier guidance (SingleStrand canonical; On/Twinkle → accent/bed), blend-mode correction

## 5. Tests & verification

- [x] 5.1 Hermetic: expansion (beat snap, alternation, cell_beats, partial merge), budget scaling (0.2 vs 1.0), blend/curve/transition keys present + value-curve round-trip, fallback weave, carrier dedup, cell-able chop, motion-share advisory, back-compat (weave=None → today's stream)
- [x] 5.2 Live: re-run candy cane lane → motion share ≥40% of placements, effects/min up at peaks, blends/curves/transitions visible in the saved .xsq, 0 skips, QA converges, sampler stills read as woven motion
