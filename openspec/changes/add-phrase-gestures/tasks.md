## 1. Weave rebalance (small, independent)

- [x] 1.1 In `pipeline/weave.py` (~line 167): `CARRIER_ROTATION = ("SingleStrand", "Bars", "SingleStrand", "Wave")`; update the comment (Garlands dropped — 4× community share from rotation; SingleStrand double-weighted — community 28.5% workhorse).
- [x] 1.2 In `fallback_weave` (~line 216): when no cellable texture comes from `section.effect_types` but `tex_groups` is non-empty, use `"Ripple"` as the texture recipe's effect_type (community 3.1%, 55 mined looks). Keep `cell_beats=4, alternation="sparse"` as-is.
- [x] 1.3 Update/extend weave unit tests: rotation contents (SingleStrand ×2, no Garlands across 4 consecutive seeds); fallback texture is Ripple when effect_types has no cellable member; still NO texture when tex_groups is empty.

## 2. Phrase-gesture layer

- [x] 2.1 Implement `place_phrase_gesture` in `pipeline/beats.py` directly after `place_vu_meter` (~line 650), per design.md D1: `PHRASE_ROTATION = ("Morph", "Curtain", "Fill")`; seed-keyed member with energy-band step-over (reuse `ENERGY_BAND`, same ±1 tolerance idea as QA rule #3 — skip a member ≥2 bands from the section band); hero-else-broad target from the vocab; 4-bar span starting at the section's 2nd bar (`_bar_ms(rhythm)` is in this module), clipped to section end; skip when section < 6 bars or intensity < 0.4; render styles per design (Fill/Curtain "Per Preview", Morph "Per Model Default"); speed + palette via existing helpers. Do NOT import from weave.py (cycle — weave imports beats): the caller passes the seed.
- [x] 2.2 In `pipeline/generate.py`: add `"phrase"` to each `_TREATMENT_LAYERS` row (`full`/`pulse` True, others False); call `place_phrase_gesture` in `realize_section` after the weave block, seed `label_seed(_label) if _label else si` (both already in scope), tag `source="phrase"`, `setdefault("T_CHOICE_LayerMethod", "Max")` when the target is in the section's based targets (mirror the accents' blend guard).
- [x] 2.3 Add `"phrase"` to `SOURCE_TAGS` in `scripts/measure_fabric.py` (~line 84).
- [x] 2.4 Unit tests: pulse-treatment 8-bar section → exactly one phrase instruction, ~4 bars, source "phrase"; two sections with the same label → same effect type; `rest` section → none; 4-bar section → none; a section band far from Curtain's (2,3) band steps to the next rotation member.

## 3. VU Meter in pulse sections

- [x] 3.1 In `realize_section` (`pipeline/generate.py` ~line 352–371): move the `place_vu_meter` call out of the `if _layers["extras"]:` block to its own condition `if _layers["extras"] or _treatment == "pulse":` (composites stay extras-only). Keep tagging identical.
- [x] 3.2 Unit/integration test: a pulse-treatment energetic section receives a VU instruction; a `feature` section still does not.

## 4. Regen + verify

- [x] 4.1 Full suite; golden regen (`XLO_REGEN_GOLDEN=1 uv run pytest tests/test_golden_pipeline.py`). Expected diff: carriers reshuffle (Garlands→SingleStrand/Wave), a `phrase`-source Morph/Curtain/Fill row in full/pulse sections, VU rows in pulse sections. Check the emit/skip report for new "layer budget" drops at peaks (design.md risk) — if present, note counts in the PR.
- [x] 4.2 Re-measure a fresh cache (`uv run python scripts/measure_fabric.py <cache>/instructions.json`) and confirm Morph/Curtain/Ripple/VU shares moved toward community (Morph+Curtain from ~0.7% toward several %); include BEFORE/AFTER in the PR description. PR to `main` (branch `feat/phrase-gestures`).
