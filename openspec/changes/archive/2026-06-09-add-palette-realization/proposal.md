## Why

The creative brief already chooses **grounded, intentional colors** — *"Warm White/Gold = the acoustic/piano warmth + G major; Deep Blue = the E-minor melancholy; Crimson = the bluesy C7 tension."* But those colors **never reach the lights**: at generation the Generator just picks a `palette_id` from a fixed menu of 12 corpus-mined palettes (by tag), so the show renders in default-ish colors that may or may not match the intent. The color *intent* is right (Stage 2, grounded in the song's harmony/mood); the **realization** is missing.

This change closes that gap: **build a real effect palette from the brief's named colors** and apply it deterministically, so the warm-white piano intro actually glows warm white and the melancholy sections actually go deep blue.

## What Changes

- A **`palette_from_colors(colors)`** in the palette/knowledge layer: maps named colors (a curated name→hex dictionary of common show colors) and `#RRGGBB` hex into a valid `C_BUTTON_Palette` settings string (color slots + active checkboxes — the same format the mined palettes use). Unknown/empty → graceful (`None`).
- The generated effects in a section **use that section's brief palette** — its instructions carry the brief's colors, and placement renders a palette built from them, **deterministically in code** (not left to the model).
- **Falls back to the mined palettes** when a section has no brief palette or its colors can't be realized — so nothing regresses; mined palettes also still cover any effect the brief doesn't color.

**Non-goals:** re-mining/curating the palette corpus; gradient/transition/multi-palette-over-time effects; how the brief *chooses* colors (Stage 2 already does that, grounded); the beats work; per-stem color reactivity.

## Capabilities

### Modified Capabilities
- `effect-presets`: the system can build a valid effect palette from a list of named or hex colors, degrading gracefully on unknown/empty input.
- `show-orchestration`: generated effects use the creative brief's section palette when specified, falling back to a mined palette otherwise — so the show's colors are intentional rather than default.

## Impact

- **`xlights-core`**: a `palette_from_colors` helper + a named-color→hex map in `knowledge/` (it's preset knowledge); `place_preset` realizes a built palette from colors.
- **`xlights-orchestrator`**: `EffectInstruction` gains optional `palette_colors`; the generate step applies the section's brief palette to its instructions (deterministic code pass); the Generator's mined `palette_menu` remains as the fallback.
- **Builds on** Stage 2's grounded `SectionPlan.palette` and the mined-palette format (`palettes.json`). Realizes color intent; doesn't touch look/effect selection.
