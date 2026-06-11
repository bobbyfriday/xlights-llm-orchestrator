## Why
Sections render monochromatic: 802 of 978 effects carry a SINGLE color, section palettes are 2-3 same-family colors, and every effect in a section gets the identical stamp — while multi-color effects (Plasma, Butterfly, Spirals, Bars) need 3+ colors to look like anything. Compounding it, the Director invents color names outside our vocabulary (Copper, Sunburst Orange, Midnight Blue) that are silently DROPPED at realization, starving palettes further.

## What Changes
- **Vocabulary**: extend `NAMED_COLORS` (~15 common show colors incl. copper, midnight blue, sunburst orange, burgundy, forest green, champagne…) and tell the Director the known vocabulary so its names resolve.
- **Richer briefs**: the Director is asked for 3–5 colors per section (an accent/contrast color included, not one warm family).
- **`expand_palette(colors, n)`**: deterministically grow a section's resolved colors to ~5 by deriving light/dark/hue-shifted variants — so even a thin brief yields a usable palette.
- **Effect-aware coloring**: multi-color effects get the FULL expanded palette; simple effects (On/Strobe/Lightning/Off) keep 1–2; concurrent effects in a section get ROTATED starts so they differ instead of being identical.

**Non-goals:** per-stem color reactivity; color-over-time within an effect (chord-cycling already exists on accents); changing the accent/chord-color logic.

## Capabilities
### Modified Capabilities
- `show-orchestration`: section palettes are richer (3–5 resolvable colors), multi-color effects receive enough colors to render properly, and concurrent effects vary within the section's palette instead of being identical.
