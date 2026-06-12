## 1. Contrast machinery (xlights-core)

- [x] 1.1 Branch `change/add-led-readability`; `colors.py`: `hue_spread`, `ensure_contrast(colors, min_spread)` (complement injection; achromatics excluded), `contrast_anchors(colors)`

## 2. Weaver + accents

- [x] 2.1 `weave.py`: directional chase cells default render_style "Default" + cell_beats floor 2 (explicit style wins; non-directional unchanged); carrier/accent roles color as `anchors[slot % 2]`; texture/bed keep the family
- [x] 2.2 `beats.py`: beat-accent color = the anchor hue-distant from the wash (chord stepping preserved over the anchor pair)
- [x] 2.3 Director prompt LED-color-reality note; generator prompt sweep note (cell_beats 4 for sweeps); catalog placement-rule contrast note

## 3. Tests & verification

- [x] 3.1 Hermetic: style/beats defaults per (direction, effect); hue spread + injection (warm-only gains cool; contrasting palette untouched; achromatics excluded); anchor alternation per slot (carrier yes, texture no); accent anchor distance; back-compat
- [x] 3.2 Live: re-run carol → clip shows a chase head traveling the arch line with per-bar reversal AND beat-to-beat color contrast; objective holds; no skip regression; user verdict is the gate
- [x] 3.3 PR: push branch, `gh pr create` (user merges)
