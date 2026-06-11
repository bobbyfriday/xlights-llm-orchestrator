## 1. Vocabulary + brief
- [x] 1.1 Extend NAMED_COLORS (~15: copper, midnight blue, sunburst orange, burgundy, forest/emerald green, champagne, bronze, ruby, sapphire, frost, snow white, candy red, lime green, royal purple, peach)
- [x] 1.2 Director prompt: 3-5 colors per section incl. a contrast/accent; name colors from the known vocabulary (list it)
## 2. Expansion + per-effect assignment
- [x] 2.1 `expand_palette(colors, n=5) -> hex list`: resolved bases first, then light/dark/hue-shift variants (colorsys), deduped, deterministic
- [x] 2.2 run.py wash pass (both sites): MULTI_COLOR effects (everything except On/Off/Strobe/Lightning/Fill) → full expanded palette; simple → 2 colors; rotate the starting color by the effect's index so concurrent effects differ
## 3. Tests
- [x] 3.1 expand_palette: 2 bases → 5 distinct valid hexes anchored on the bases; ≥n bases → first n; unknowns skipped
- [x] 3.2 Plasma gets ≥3 colors from a 2-color section; On gets ≤2; two effects in one section differ; new names resolve
- [x] 3.3 Suite passes
