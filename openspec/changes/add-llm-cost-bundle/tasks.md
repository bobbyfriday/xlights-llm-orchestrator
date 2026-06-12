## 1. Guide extracts (the big lever)

- [x] 1.1 `agents/guide_extracts.py`: heading-slice `_cut` (level-1 titles excluded, trailing hr stripped) + `catalog_essentials` / `layering_essentials` / `sequencing_essentials` (≤3KB) / `scene_recipe(scene_id)`; all degrade to ""
- [x] 1.2 `agents/generator.py`: system prompt = `_PROMPT` + extracts (no full guides, no cookbook); `render_input` inlines `scene_recipe(section.scene_id)`; Director untouched

## 2. Refine plateau stop

- [x] 2.1 `pipeline/run.py` `_refine_loop`: per-iteration signature (objective, advisory, frozenset of (section_index, issue[:64])); equal to previous → log "plateau", `_record(human_decision="plateau")`, break before applying revisions; REGRESS_MARGIN/STALL_LIMIT/revert untouched

## 3. Routing

- [x] 3.1 `models/config.yaml`: gemini generator+analyst → `gemini-3.1-flash-lite`; gemini judge → `gemini-3.5-flash`; anthropic + gemini director/synthesizer/visual_critic untouched

## 4. Tests & verification

- [x] 4.1 `tests/test_guide_extracts.py`: sentinel + bound checks per extract; scene isolation (SC-01 without SC-02/09/14); bogus `XLO_EFFECTS_CATALOG` → ""; composed prompt <15KB; `render_input` scene-recipe inclusion/exclusion
- [x] 4.2 `tests/test_refine.py`: identical fakes stop after 2 iterations (1 regen) with an approving checkpoint; moving scores run all iterations. `tests/test_guide_injection.py` scene-routing assertion updated; `tests/test_design_escalation.py` repeat-offender test given a moving score (flat + identical revision is now a plateau)
- [x] 4.3 Full hermetic suite green from worktree root; composed generator prompt measured (99,091 → 15,204 bytes)
- [ ] 4.4 Live: A/B a full run (flash-lite generator + slim prompt) — section quality holds (rules score, skips, user verdict) and per-run token spend drops as projected
