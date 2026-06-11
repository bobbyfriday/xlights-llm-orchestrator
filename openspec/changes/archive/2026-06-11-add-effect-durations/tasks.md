> **Build result:** DURATION_HIT/PHRASE classes (qa/rules.py) + normalize_durations (beats.py: hit >1.5 bars → per-bar ≤1.2s cells preserving look/colors/settings; phrase clamped to 8 bars; bar from tempo/beat-spacing) wired at both generate sites; catalog 0.2 (§2.1 + rule #13); generator prompt. Evidence basis: an 88.6s Shockwave wash in the candy run. 221 tests.

## 1. Taxonomy + conversion
- [x] 1.1 `DURATION_CLASS` map (HIT/PHRASE/SUSTAINED) for the placeable effects, in qa/rules.py beside ENERGY_BAND
- [x] 1.2 `normalize_durations(instructions, rhythm, section)` in beats.py: HIT >1.5 bars → per-bar cells (≤1.2s, bar starts, same look/colors/settings); PHRASE → end ≤ start+8 bars; bar from tempo (fallback beat spacing ×4, else 2s×4)
- [x] 1.3 Wired at both generate sites (rhythm computed once, shared with the accent layer)
## 2. Knowledge surfaces
- [x] 2.1 Catalog .md: §2.1 duration-class table + placement rule #13 + changelog 0.2 (the LLM sees it via injection)
- [x] 2.2 Generator prompt: hit = punctuation never washes; prefer several short effects over one long static wash
## 3. Tests & verification
- [x] 3.1 88s Shockwave → ~bars-count cells ≤1.2s each at bar starts, look/colors preserved; 20-bar Curtain → 8 bars; 88s Spirals untouched
- [x] 3.2 Suite passes; live: re-run shows no hit-class effect >2 bars
