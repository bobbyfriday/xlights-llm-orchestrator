## 1. Plan model: the phrasing dial

- [x] 1.1 Add `phrasing: str = ""` to `SectionPlan` in `show_plan.py` with a doc comment stating the contract (`"legato" | "staccato" | ""`); confirm it is additive/defaulted and old cached plans still deserialize.
- [x] 1.2 Add a hermetic test that a `SectionPlan` round-trips with `phrasing` set and with it omitted (back-compat).

## 2. Weaver: resolve phrasing and synthesize fades

- [x] 2.1 In `weave.py`, add a pure helper `resolve_phrasing(phrasing, intensity) -> "legato"|"staccato"` (directed value wins; else `intensity < INTENSITY_THRESHOLD` → legato, else staccato). Define `INTENSITY_THRESHOLD = 0.5` as a named constant.
- [x] 2.2 Add a curated `effect_family → primitive` map (constant) classifying effect types as `"fade"` (line/chase/point: SingleStrand, Butterfly, On, Twinkle, Bars, …) or `"dissolve"` (textural fill/wash: Plasma, Fill, Color Wash, Shimmer, …); unknown families default to `"fade"` (the safe choice).
- [x] 2.3 Add a pure helper `soft_edge_settings(effect_type, cell_len_ms, phrasing) -> dict`: for staccato → `{}`; for legato → `fade` primitive emits `{"T_TEXTCTRL_Fadein": s, "T_TEXTCTRL_Fadeout": s}` (`s = round(min(MAX_FADE_S, FADE_FRACTION * cell_len_ms/1000), 2)`); `dissolve` primitive emits `{"T_CHOICE_In_Transition_Type": "Dissolve", "T_CHOICE_Out_Transition_Type": "Dissolve", "T_SLIDER_In_Transition_Adjust": a, "T_SLIDER_Out_Transition_Adjust": a}` (adjust `a` from `FADE_FRACTION`). Define `FADE_FRACTION` (~0.35) and `MAX_FADE_S` constants.
- [x] 2.4 Call `soft_edge_settings(...)` inside `_cell()` and merge into `extra`, BUT only when the recipe set no explicit `transition` (recipe transition wins — preserve the existing path); thread the resolved phrasing into `_cell()`.
- [x] 2.5 In `expand_weave()`, resolve the section's phrasing once and apply the legato `cell_beats` floor (`max(recipe.cell_beats, LEGATO_CELL_BEATS_FLOOR)`, floor = 2) only for legato; confirm density stays within the existing `cell_budget`.
- [x] 2.6 Decide and implement the bed cell's soft-edge behavior (gentle fade-in at section entry within the cap; no per-cell churn).

## 3. Director: choose phrasing per section

- [x] 3.1 Extend the Director prompt in `director.py` with a short instruction to set `phrasing` per section (legato for calm/introspective, staccato for energetic; omit to default by energy), tied to the existing look/intensity guidance.

## 4. Hermetic tests

- [x] 4.1 Test `resolve_phrasing`: directed legato/staccato override; intensity default below/above the threshold; boundary at exactly 0.5.
- [x] 4.2 Test the `effect_family → primitive` map: a line/chase effect → `fade`; a textural fill/wash → `dissolve`; an unknown effect → `fade` default.
- [x] 4.3 Test `soft_edge_settings`: legato fade scales to cell length and the `MAX_FADE_S` cap clamps long cells; legato dissolve emits the In/Out Dissolve type + adjust; staccato produces no keys; ms→s conversion is correct.
- [x] 4.4 Test `expand_weave`/`_cell` end-to-end on synthetic sections: a low-intensity line-effect section's cells carry Fadein/Fadeout; a legato textural section carries Dissolve; an energetic section carries none (matches pre-change); directed phrasing overrides intensity; a recipe with an explicit transition keeps it (not overwritten).
- [x] 4.5 Test the legato `cell_beats` floor and that cell count stays within budget.
- [x] 4.6 Run the full hermetic suite (`pytest`) and confirm no regressions.

## 5. Live verification

- [ ] 5.1 Run `xlo run --song "mp3/christmas canon.mp3" --refine --auto` and confirm verses 4 & 5 (legato) carry fades and no longer draw the "rapid erratic flashing" critique; confirm a peak section stays crisp (staccato).
- [ ] 5.2 Tune `FADE_FRACTION`, `MAX_FADE_S`, and the legato `cell_beats` floor against the live render if needed.

## 6. Land

- [x] 6.1 Update `xlights-layering-rendering-guide.md` (or the relevant guide) to mention phrasing-driven fades if it documents cell realization.
- [ ] 6.2 Open a PR per the project workflow; do not commit to `main` directly.
