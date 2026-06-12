## Context

Two perceptual failures survive a 95-objective run: direction exists in the settings but not to the eye (per-model rendering confines each chase to its own prop for half a second), and the color system optimizes for tasteful depth (tint/shade families) when the medium punishes it — pixels make subtle tints identical. The metrics can't see either; the user's eyes are the gate.

## Goals / Non-Goals

**Goals:** sweeps that visibly travel across whole groups and dwell long enough to track; a deterministic hue-contrast floor so beat-to-beat color change is always LED-legible; no regression to the dark-chorus fixes.

**Non-Goals:** changing wash/texture palette behavior (depth variants are right there); Director palette redesign beyond a prompt note; vertical (up/down) render changes — that motion lives within each prop and already reads per-model; gamma/calibration.

## Decisions

**D1 — Group canvas ONLY for directional chase cells.** The dark-chorus lesson was about FILL effects spread thin over a big canvas; a chase is a bright moving head, and cross-group chases on the group buffer are core community practice. Scope: direction ∈ {ltr, rtl, bounce, center_out, center_in} AND effect ∈ {SingleStrand, Garlands, Marquee, Wave, Bars} → default render_style "Default" (explicit recipe style still wins). Everything else keeps "Per Model Default". The live clip is the risk gate.

**D2 — Sweep cells dwell: `cell_beats` floored at 2 for directional chases** (~0.9s at 133bpm), prompt recommends 4 (a bar). A 0.5s sweep is sub-perceptual regardless of buffer.

**D3 — Contrast is a deterministic FLOOR, not an LLM hope.** `colors.py` gains: `hue_spread(colors)` (max pairwise hue distance in HSV, achromatic colors excluded); `ensure_contrast(colors, min_spread=60°)` (injects the complement of the dominant hue when spread is below the floor); `contrast_anchors(colors)` (the two most hue-distant resolvable colors after the floor). White/warm-white count as achromatic — a gold+white palette is still one hue.

**D4 — Anchor alternation per slot for rhythm-carrying roles.** Carrier and accent cells color as `anchors[slot % 2]` — beat-to-beat contrast, the signal LEDs render best. Texture and bed cells keep `effect_palette`'s expanded family (washes want depth). The beat-accent layer's color becomes the anchor hue-distant from the wash instead of brightened-same-hue (keeps the existing chord-stepping when chords are present, applied over the anchor pair).

**D5 — Prompt and catalog carry the principle, code carries the guarantee.** Director prompt: LED COLOR REALITY note (≥1 cool vs warm anchor; subtle tints read as one color). Catalog placement rule: contrast-over-subtlety for automated palettes. But even a four-warm-golds brief renders legibly because of D3.

## Risks / Trade-offs

- [Group-canvas chase on a sparse group reads dim (the old failure)] → confined to chase effects with bright heads; live clip gates; per-model remains the default for everything else.
- [Injected complements fight the Director's mood (a cool cyan in a "warm nostalgia" section)] → the complement is an ACCENT anchor on rhythm cells, not a wash recolor; the wash family is untouched. If a section truly wants monochrome, the Director can say so in `look` — future escape hatch if it ever matters.
- [Anchor alternation reads as blinking on very fast songs] → anchors alternate per CELL (≥2 beats now), not per frame; bounded by cell duration.
- [Floored cell_beats reduces cell counts → density dip] → sweeps cover more props per cell on the group buffer; net coverage holds.

## Migration Plan

Additive defaults; explicit recipe fields always win. Branch `change/add-led-readability` → PR → user merges. Rollback = revert PR.

## Open Questions

- Whether the visual critic should be prompted to grade "would this read on real LEDs" (contrast/motion legibility) — deferred; this change makes the deterministic floor, the critic note can follow if needed.
