## Why
The effects catalog's §11 Placement Decision Rules are explicitly **"normative for automated sequencing"** — yet today they're only prompt advice the Generator can ignore. The catalog's own language makes several of them defects, not choices: texture on linear props, a 5-energy Strobe in a 2-energy verse, two showpiece features at once, sustained strobing. These should be detected (and the hard caps enforced) deterministically.

## What Changes
- **Hard caps (rule #7)** enforced at the deterministic layer: Strobe instructions clamped to ≤1s; Shimmer clamped to ≤2 bars (from tempo, fallback 4s).
- **A `rules` objective QA metric** (`qa/rules.py`) detecting the judgment-adjacent violations as findings that gate the refine loop — the *Generator* fixes them on regeneration (it stays the author):
  - **#2 affinity**: texture effects (Plasma, Fire, Liquid, Life) targeting linear props (arches/outline/canes/icicles/path groups).
  - **#3 energy band**: an effect whose catalog energy band is ≥2 away from the section's energy (e.g. Strobe/Fireworks in a quiet verse, Candle in a drop).
  - **#4 feature exclusivity**: >1 high-attention effect (Kaleidoscope, Shader, Shockwave, Fireworks) overlapping in time.

**Non-goals:** rewriting the Generator's choices in code (the LLM authors, the loop revises); media-resolution checks (#2's <50px clause — no Text/Pictures presets exist yet); direction-follows-music (#8, needs melody contour — parked); layer ceiling (#10 — the emitter already manages layers).

## Capabilities
### Modified Capabilities
- `show-orchestration`: the catalog's normative placement rules are enforced — hard duration caps applied deterministically, and affinity/energy-band/feature-exclusivity violations surfaced as objective findings that gate the refine loop.

## Impact
- **`xlights-orchestrator`**: `qa/rules.py` (+ folded into `qa.evaluate`'s objective); a duration-clamp pass at the generate sites; a small effect→energy-band table from the catalog §2.
- **Builds on** the catalog injection (the Generator knows the rules), the SEM_ role groups (linear-prop identification), and the refine loop (scoped regeneration fixes violations).
