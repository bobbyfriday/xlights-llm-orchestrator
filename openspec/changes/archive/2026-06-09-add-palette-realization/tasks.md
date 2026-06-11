> **Build result (verified live):** `knowledge/colors.py` `palette_from_colors` (39 named colors + hex passthrough → exact mined `C_BUTTON_Palette` format, round-trips through `_palette_colors`); `place_preset` prefers built palette, falls back cleanly to mined `palette_id`; `EffectInstruction.palette_colors` (additive); a deterministic code pass stamps `section.palette` onto its instructions at both generate sites. **140 hermetic tests pass** (8 new). LIVE: re-generated mad russian → 27/27 instructions carry the brief's colors; built palettes PLACE (26 placed / 1 overlap skip — NOT a palette rejection); the saved .xsq carries the brief's exact hexes on effects (#FFF1D0 WarmWhite, #FFBF00 Amber, #FFD700 Gold, #00008B DeepBlue) with ZERO mined defaults (#000080); offline render shows the verse glowing amber/gold and the intro appropriately dim (0.0 intensity). (Mean-RGB over a whole frame is a poor color metric — multi-color animating effects average to mud; the .xsq is authoritative.)

## 1. Build a palette from colors (knowledge layer)

- [x] 1.1 A curated `NAMED_COLORS` dict (name→`#RRGGBB`) of common show colors (warm/cool white, amber, gold, red, crimson, deep/ice blue, green, teal, purple, magenta, orange, pink, white, black, …), case/space-insensitive lookup
- [x] 1.2 `palette_from_colors(colors: list[str]) -> str | None`: resolve each (hex passthrough; name via dict; unknown→skip); from the realized hexes (dedupe, cap 8) assemble `C_BUTTON_Palette{1..8}=<hex>` (unused→`#000000`) + `C_CHECKBOX_Palette{1..N}=1`; `None` if N==0. Output round-trips through `_palette_colors`

## 2. Apply the brief palette + realize it at placement

- [x] 2.1 `EffectInstruction`: add `palette_colors: list[str] = []` (additive/back-compat)
- [x] 2.2 Generate code pass: after the Generator returns a section's instructions, set `ins.palette_colors = list(section.palette)` when `section.palette` is non-empty — at BOTH call sites (`run.py:282` initial, `run.py:111` refine `_regen`)
- [x] 2.3 `place_preset(+palette_colors)`: `palette = palette_from_colors(palette_colors) or (get_palette(palette_id).palette_string if palette_id else "")` — built palette takes precedence, but **`None` (unrealizable) falls back cleanly to the mined `palette_id`** so placement NEVER breaks; emitter passes `ins.palette_colors`. No change to look/settings assembly

## 3. Tests & verification

- [x] 3.1 `palette_from_colors(["warm white","deep blue","#DC143C"])` → valid string; `_palette_colors` parses back those 3 hexes; `C_CHECKBOX_Palette1/2/3=1` active; slots filled to 8
- [x] 3.2 hex passthrough (`["#FF0000","#00FF00"]`); unknown name skipped (no raise); `[]`/all-unknown → `None`
- [x] 3.3 Generate pass: a section with `palette=["amber","gold"]` → its instructions carry `palette_colors`; a section without → empty (falls back)
- [x] 3.4 `place_preset`: with `palette_colors` → the effect's palette reflects them; without → uses `palette_id` (mined) fallback; existing preset/palette tests still pass
- [x] 3.5 Live (gated, MANDATORY — only place that proves xLights accepts a *built* palette): bust `instructions.json`, re-generate mad russian → assert (a) **NO new skips** (built palettes actually place — `worked=True`, no regression) AND (b) the warm-white/amber intro + deep-blue sections render the BRIEF's colors (palette-string / offline-preview check), not a default mined palette
