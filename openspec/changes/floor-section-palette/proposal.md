# Proposal: floor-section-palette

## Why

The Director prompt asks every section palette to span hues ("≥1 cool vs warm anchor"), but
nothing downstream checks it: the 60° LED-legibility floor (`ensure_contrast`) runs only inside
`contrast_anchors()`, which feeds the beat/weave/trigger alternation pair. The section **wash and
multi-color effect palettes render the Director's raw colors with no floor** — an all-warm palette
(gold + amber + warm white) becomes one warm smear on real pixels. A second, rarer hole: an
all-achromatic palette (whites/grays only) degenerates the beat anchor pair to
`(first color, white)` — e.g. warm white vs white, which barely contrasts. `docs/color-design.md`
§5 #1 identifies this as the highest-leverage color fix: it makes "every section spans hues"
true at render instead of prompt-only.

## What Changes

- **Floor every section palette at realization.** After the show-level color script runs
  (`apply_color_script` — so the floor sees the final, coherence-threaded palettes), an
  `ensure_contrast`-style pass injects a complementary anchor into any `SectionPlan.palette`
  whose chromatic hues cluster below `MIN_HUE_SPREAD` (60°). Washes and multi-color effects then
  span hues, not just the rhythm layer.
- **Preserve the white-dominant aesthetic.** All-achromatic section palettes are exempt from hue
  injection (`ensure_contrast` already passes them through) — a deliberate warm-white show stays
  warm-white, per the doc's §2.4.
- **Close the achromatic anchor hole.** For all-achromatic palettes, `contrast_anchors()` falls
  back to **value contrast** — the pair maximizes value separation, synthesizing a darker variant
  when every color is near-white — instead of the degenerate `(first color, white)`.
- Layer/cell palette overrides (`CellRecipe.palette`, `CompositeLayer.palette`) and
  Generator-pinned `EffectInstruction.palette_colors` are deliberate accents and stay unfloored.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `show-orchestration`: new requirement — section palettes are contrast-floored at realization
  (complement injected when chromatic hues cluster; all-achromatic palettes exempt). Modified
  requirement — "Beat accents contrast the wash" gains an achromatic-section scenario: anchors
  contrast by value when no hue is available, never white-on-white.

## Impact

- `packages/xlights-orchestrator/src/xlights_orchestrator/pipeline/color_script.py` — the floor
  pass runs as the final move of `apply_color_script` (both call sites — fresh plan in
  `pipeline/run.py`, redesigned sections in `pipeline/refine_loop.py` — get it for free;
  idempotence is preserved).
- `packages/xlights-core/src/xlights_core/knowledge/colors.py` — `contrast_anchors()` achromatic
  fallback; possibly a small value-variant helper.
- Tests: `tests/test_color_script.py`, `tests/test_led_readability.py` (new floor + fallback
  cases; existing expectations for all-warm plans will change — palettes gain an injected
  complement).
- Docs: `docs/color-design.md` §1.3/§1.6/§5 #1 status flips once shipped.
