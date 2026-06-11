## 1. Base/accent color split

- [x] 1.1 `split_palette(colors) -> (base, accent)` in `knowledge/colors.py`: resolve to hex; luminance rank. ≥2 colors → `accent=[brightest]`, `base=rest`. 1 color → `base=[c]`, `accent=[_brighten(c)]` (~65% toward white). None → `([],[])`
- [x] 1.2 `_brighten(hex)` helper (blend toward white); returns a valid `#RRGGBB`

## 2. Apply split + every-beat chase + downbeat

- [x] 2.1 run.py wash code-pass: `base,_ = split_palette(section.palette)`; `ins.palette_colors = base or section.palette` (both generate sites)
- [x] 2.2 `place_beat_accents`: color accents with `accent = split_palette(section.palette)[1] or section.palette`
- [x] 2.3 Every-beat density: use the section's beats (no downsample); raise `MAX_ACCENTS_PER_SECTION` to ~80 as a hard upper bound; downsample OFF-beats first if exceeded (downbeats survive)
- [x] 2.4 Downbeat emphasis: bar start (`i % BEATS_PER_BAR == 0`) → an accent on EVERY `pulse_group`; off-beat → one accent on the rotating group `pulse_groups[i % len]`

## 3. Tests & verification

- [x] 3.1 `split_palette(["Gold","Deep Blue"])` → accent=[Gold] (brightest), base=[Deep Blue], disjoint; `split_palette(["Warm White"])` → accent ≠ base, both non-empty; `split_palette([])` → ([],[])
- [x] 3.2 `place_beat_accents`: accent palette ≠ wash palette for a 2-color section; a 32-beat section → ~32+ accents (not 24); a huge section capped at ~80; downbeat beats hit ALL pulse_groups, off-beats rotate one; existing beat tests updated
- [x] 3.3 run.py wash applies `base` (assert wash palette = base, beat palette = accent for a 2-color section)
- [x] 3.4 Live (gated): re-generate mad russian → per-section accents ≈ beat count (not 24), beat color CONTRASTS the wash (palette-string / offline preview), downbeats hit harder; total effect count bounded, no new skips

> **Final color model (user choice):** wash keeps the FULL bright palette; beats are a BRIGHTENED tint of the palette (contrast by luminance, staying colorful) — NOT the original base/accent split. Verified live: sec 3 wash=[Gold,Deep Blue], beats={#FFF1A6,#A6A6D6}; every-beat chase + downbeat all-groups; 162 tests pass; placed 1268/2. Peak frame shows bright beat pops on a colored wash. NOTE: the WASH renders dim (effect brightness/coverage, a SEPARATE lever from palette) — candidate follow-up if a brighter overall show is wanted.
