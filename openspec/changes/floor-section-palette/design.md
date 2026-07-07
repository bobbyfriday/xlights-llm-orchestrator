# Design: floor-section-palette

## Context

Today the 60° LED-legibility floor lives in `xlights_core.knowledge.colors`:
`ensure_contrast(colors)` appends the complement of the dominant hue when the palette's
*chromatic* hues cluster below `MIN_HUE_SPREAD = 60.0`, and it is invoked only by
`contrast_anchors()` (the beat/weave/trigger alternation pair) and by the color script's
bridge move. The wash path — `effect_palette(section.palette, …)` → `expand_palette` →
`palette_from_colors` — never sees it. Separately, `contrast_anchors()` on a palette with
zero chromatic colors falls back to `(first resolvable, "#FFFFFF")`, which for a warm-white
palette is white-on-white.

The show-level color script (`pipeline/color_script.py`, `apply_color_script`) is a
deterministic post-pass that already rewrites `SectionPlan.palette` in place at exactly the
right moment: after the Director on a fresh plan (`pipeline/run.py`) and after section
redesigns (`pipeline/refine_loop.py`). It is idempotent, and it already injects a raw-hex
complement into a section palette (the bridge move), so "the section palette may contain a
synthesized hex" is an established pattern.

## Goals / Non-Goals

**Goals:**

- Every realized section palette with at least one chromatic color spans ≥60° of hue by the
  time effects are generated — the wash and multi-color effects, not just the rhythm layer.
- All-achromatic (white-dominant) sections keep their aesthetic: no hue is injected.
- Beat anchors never degenerate to white-on-white: on all-achromatic palettes they contrast
  by *value* instead of hue.
- The floor is deterministic and idempotent (safe under cache reuse, regen, and re-runs).

**Non-Goals:**

- No flooring of `CellRecipe.palette` / `CompositeLayer.palette` overrides or
  Generator-pinned `EffectInstruction.palette_colors` — single-color layer accents are
  deliberate design, not a legibility bug.
- No change to the Director prompt, the show-palette realization (§5 #2), the occasion
  library (§5 #3), or the QA advisory (§5 #5) — separate changes.
- No raise of the 60° threshold toward the 90–120° design target (§5 #8) — this change is
  the *legibility* floor only.

## Decisions

### 1. The floor runs as the final move of `apply_color_script`

Alternatives: (a) a separate `floor_section_palettes(plan)` wired at both call sites;
(b) flooring inside `effect_palette` at consumption time.

Chosen: extend `apply_color_script` with a fourth, final move — for each section,
`sec.palette = floored(sec.palette)`. Rationale: both existing call sites (fresh plan,
refine-loop redesign) inherit the floor with zero new wiring, ordering after the
anchor/signature/bridge moves is guaranteed by construction (the floor must see final
palettes — the anchor thread can change what the dominant hue is), and idempotence carries
over naturally (a floored palette already spans ≥60°, so a second pass is a no-op).
Option (b) was rejected because `effect_palette` runs per-effect — the injected complement
would exist only in expanded hexes, invisible to the brief, to `contrast_anchors` (which
floors independently), and to any future QA rule reading `section.palette`.

### 2. Injected complement is snapped to the nearest LED-safe named color

`ensure_contrast` emits a raw hex (s=0.9, v=1.0 complement). For anchor pairs that never
surface to humans this is fine, but the section palette is shown in the creative brief and
the editable brief. The floor therefore snaps the injected complement to the nearest
`NAMED_COLORS` entry by hue (chromatic entries only), falling back to the raw hex when
nothing is within ~25°. Rationale: briefs stay human-readable ("teal", not "#00BFFF"), and
the palette stays (approximately) within the Director's closed vocabulary. `ensure_contrast`
itself is left untouched — the snap lives in the color-script floor only, keeping the
blast radius small.

### 3. Achromatic anchor fallback contrasts by value, not hue

In `contrast_anchors()`, when the floored palette has fewer than two chromatic colors
(i.e. the palette is all-achromatic — a single chromatic color is already handled, since
`ensure_contrast` gives it a complement): pick the two resolvable colors with the largest
*value* separation. If that separation is still small (all near-white, e.g. white + warm
white), synthesize a dimmed variant of the first color (same hue/sat, value scaled to
~0.35) as the second anchor. Rationale: §2.4 of the color design doc — value contrast is
the legitimate tool for white-dominant looks; injecting a hue onto the beats of a deliberate
all-white section would break the aesthetic the exemption in Decision 1 protects.

### 4. No config flag

The floor is unconditional, like the color script itself. A near-monochrome wash is a
legibility bug, not a style; the all-achromatic exemption already covers the one legitimate
"don't add contrast" aesthetic. (If a future show needs a deliberate 40°-spread palette,
that belongs with the §5 #8 advisory work, not a flag here.)

## Risks / Trade-offs

- [Cached plans change on re-run] → The floor mutates `section.palette` the same way the
  color script already does; a cached plan that predates the floor gets floored on load-path
  re-script (refine loop) or stays as-is until regenerated. Acceptable: same story as the
  color script's own rollout.
- [The complement may fight the Director's mood] → The complement of a warm-cluster palette
  is a cool hue by construction, appended (not prepended), so it lands in the wash rotation
  and depth slots rather than leading the section. Simple effects take the first two colors,
  which stay Director-chosen (or signature-pair) colors.
- [Existing tests assume unfloored palettes] → `test_color_script.py` /
  `test_led_readability.py` expectations for all-warm fixtures will now include an injected
  color; tests updated as part of the change, and the assertions become *stronger*
  (spread ≥60° everywhere).
- [Snap-to-named could collide with a color already in the palette] → Snap candidates that
  resolve to a hue within 60° of the existing cluster are skipped in favor of the raw hex,
  so the floor can never inject a color that fails its own spread check.

## Open Questions

(none — scoped tightly to §5 #1; the 90–120° advisory target and any QA-side check are
explicitly deferred to §5 #8 / #5.)
