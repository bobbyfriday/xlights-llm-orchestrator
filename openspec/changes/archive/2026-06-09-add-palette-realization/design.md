## Context

Palettes are mined from the user's `.xsq` corpus into `palettes.json` — each `Palette{palette_id, palette_string, colors, tags}`, where `palette_string` is the xLights settings form:
`C_BUTTON_Palette1=#000080,…,C_BUTTON_Palette8=#AAFFFF,C_CHECKBOX_Palette4=1,C_CHECKBOX_Palette5=1,…` (8 color slots + `C_CHECKBOX_PaletteN=1` flags for the *active* slots). `place_preset(palette_id=…)` looks up that string. The Generator picks a `palette_id` from `palette_menu(limit=12)`; the brief's grounded colors (`SectionPlan.palette: list[str]`) are never used. This change builds a `palette_string` from those colors and applies it.

## Goals / Non-Goals

**Goals:** build a valid palette from named/hex colors; apply the section's brief palette deterministically; fall back to mined palettes; graceful on unknown/empty. Hermetic tests.

**Non-Goals:** re-mining the corpus; gradients/multi-palette-over-time; how the brief chooses colors; beats; per-stem color.

## Decisions

### `palette_from_colors(colors) -> str | None` (knowledge/palette layer)
A curated **name→hex** dictionary of common show colors (warm white `#FFF1D0`, cool white `#FFFFFF`, amber `#FFBF00`, gold `#FFD700`, red `#FF0000`, crimson `#DC143C`, deep blue `#00008B`, blue `#0000FF`, ice blue `#AADAFF`, green `#00FF00`, teal `#008080`, purple `#800080`, magenta `#FF00FF`, orange `#FF8C00`, pink `#FF69B4`, white `#FFFFFF`, black `#000000`, … extensible). Resolve each input: a `#RRGGBB` passes through; a name (case/space-insensitive) maps via the dict; unknown → skipped. From the resolved hexes (cap 8, dedupe), assemble:
`C_BUTTON_Palette{i}=<hex>` for i=1..8 (fill unused slots with `#000000`) + `C_CHECKBOX_Palette{i}=1` for i=1..N (the N realized colors are the *active* slots). Return `None` if N==0. Lives in `xlights-core/knowledge` (it's preset knowledge, like `palettes.py`); validate the output parses back via the existing `_palette_colors` regex.

### Apply the brief palette deterministically (code, not the model)
`EffectInstruction` gains `palette_colors: list[str] = []`. After the Generator returns a section's instructions, a **code pass** sets `ins.palette_colors = list(section.palette)` for each (when `section.palette` is non-empty) — same pattern as the deterministic intensity/stem passes. Done at both generate call sites (initial `run.py:282` and refine `_regen` at `run.py:111`). The model still picks looks/effects/`palette_id`; **code owns the color**, so the brief's intent reliably lands.

### `place_preset` realizes colors → palette string
`place_preset` (and the `EffectInstruction` → addEffect path) prefers `palette_colors`: if present and `palette_from_colors(palette_colors)` returns a string, use it as the effect's palette; else if `palette_id` is set, use the mined palette; else default. So a section with brief colors renders them; a section without (or with unrealizable colors) falls back to the mined `palette_id` the model chose. No change to look/settings assembly.

### Keep the mined menu as fallback
`generator.render_input` still offers `palette_menu()` so the model picks a sensible `palette_id` — which now serves as the **fallback** when the brief has no usable palette for that section. Belt-and-suspenders.

## Risks / Trade-offs

- **Color vocabulary coverage** — the brief may name a color outside the dict ("bittersweet amber"); the resolver skips unknowns and uses what it can, or falls back to mined. The dict is easily extended; a fuzzy/nearest match is a possible later refinement.
- **Active-slot semantics** — mined palettes mark arbitrary slots active; we make slots 1..N active (the realized colors). Equivalent and valid; verified by round-tripping through `_palette_colors`.
- **8-slot cap** — >8 brief colors are truncated to 8 (xLights' max). Fine.
- **Determinism vs model intent** — code overrides the model's `palette_id` when brief colors exist. Intended (the brief is the source of truth); the model's pick remains the fallback.
- **No effect-settings change** — only the palette portion; look/knob assembly untouched, so existing preset tests stand.

## Open Questions

- Nearest-color fallback for unknown names vs skip — start with skip (simple, predictable); add nearest later if the brief routinely names off-dict colors.
- Whether to also realize the GLOBAL `ShowPalette` as a default for sections that don't set their own — defer; per-section palette is the lever.
