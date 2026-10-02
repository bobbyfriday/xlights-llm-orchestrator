## 1. Measurement first (BEFORE numbers)

- [x] 1.1 In `scripts/measure_fabric.py`: change `_Row.blend: bool` to `blend_value: str` (empty = no blend); update `_row_from_instruction` and `_row_from_xsq_effect` to store the actual `T_CHOICE_LayerMethod` value; keep `blend_mode_share` computed as before (`bool(blend_value)`); add `FabricStats.blend_value_share: dict[str, float]` bucketed per design.md D3 (Max / Brightness / mask family — any value containing "Mask", "Unmask", or "reveals" — / other), shares among blended rows only; print one line in `render_report`; add `blend_value_brightness_share=0.36` and `blend_value_mask_share=0.27` to `CommunityAggregates` with a provenance comment. Fix any `.blend` call sites (`rg "\.blend\b" scripts tests`).
- [x] 1.2 Capture the BEFORE report for the PR: `uv run python scripts/measure_fabric.py data/analyses/orchestrator/e1a6805bc78a0643/instructions.json` (save output).
- [x] 1.3 Update `tests/test_fabric_stats.py`: existing assertions still pass; add a loose canary that will assert golden blended rows are NOT ~all-Max after task 2 lands (write it xfail/skip-marked now if needed, enable in task 4.1).

## 2. Role-aware blend default

- [x] 2.1 In `pipeline/weave.py::_cell` (~line 336), replace the constant `recipe.blend or "Max"` with the role-aware default per design.md D1 (texture → Brightness; carrier/accent → Max; explicit recipe.blend always wins). Keep the existing comment block, extend it with the corpus numbers.
- [x] 2.2 Unit tests (existing weave cell tests): texture-over-bed cell → Brightness; carrier → Max; explicit blend honored; texture on an UNbased target (blended=False) → no LayerMethod key at all.
- [x] 2.3 Add the one-sentence generator prompt note per design.md (texture cells over a bed default to Brightness; only specify `blend` to override).

## 3. Reveal composite

- [x] 3.1 Add the `reveal` entry to `CURATED_COMPOSITES` in `pipeline/weave.py` per design.md D2 (Spirals base, Shape upper with `"1 is Mask"`). NOTE: `add-counter-rotation` edits the same dict — if it hasn't merged yet, coordinate/rebase; this change only ADDS a key.
- [x] 3.2 Add `"reveal"` to `_PEAK_COMPOSITES` in `pipeline/generate.py` (~line 62).
- [x] 3.3 Unit test: `curated_composite("reveal", ["SEM_FOCAL"])` expands to 2 instructions — base Spirals (no LayerMethod) and upper Shape with a mask-family LayerMethod; both `render_style="Per Model Default"`, ascending `layer`.
- [ ] 3.4 Live polarity check per design.md D2: render a peak section containing the reveal (golden .xsq in xLights, or a scratch sequence). If the texture shows OUTSIDE the shape, flip the blend string to `"1 is Unmask"` and record the winning polarity in the composite's comment. If a live check is impossible in this session, leave `"1 is Mask"`, and note the unverified polarity in the PR description as a follow-up watch item.

## 4. Regen + report

- [x] 4.1 Full suite; golden regen (`XLO_REGEN_GOLDEN=1 uv run pytest tests/test_golden_pipeline.py`); enable the blend canary from 1.3. Expected golden diff: texture-cell LayerMethod values Max→Brightness, plus the reveal composite at peaks if the fixture has one.
- [x] 4.2 Capture the AFTER measurement (same command as 1.2); PR to `main` (branch `feat/blend-vocabulary`) with BEFORE/AFTER blend-value lines in the description and the design.md risk note about Brightness-over-dim-beds (what to watch for live: textures reading dark → the intensity-gated fallback described in design.md Risks).
