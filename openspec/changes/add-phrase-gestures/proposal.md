# add-phrase-gestures

## Why

Several community staple effects are near-absent from our shows (2026-07-07 corpus comparison, memory: `corpus-alignment-2026-07`; community share → ours): **Morph 6.2% → 0.7%** (their #5 effect, and the top-3 effect in four of the 17 community shows), **Curtain 2.7% → 0.0%**, **Ripple 3.1% → 0.4%**, **VU Meter 6.2% → 0.2%** — while we over-place **Garlands 1.9% vs 0.5%** and **Marquee 1.9% vs 0.3%**. The structural causes:

1. Morph/Curtain/Fill are phrase-class (`duration_class="phrase"`), so the cell weaver cannot place them — they appear only when the per-section Generator volunteers them, which it rarely does. There is no deterministic layer for bounded phrase gestures (reveals, sweeps, builds), unlike beds/cells/accents/composites which all have one.
2. `CARRIER_ROTATION = ("SingleStrand", "Bars", "Garlands", "Wave")` gives Garlands 25% of sections — 4× its community share — while the community's actual workhorse (SingleStrand, 28.5% of their entire corpus) gets only 25% of our rotation.
3. `place_vu_meter` is gated to `full`-treatment sections only (the "extras" layer), so the community's music-reactive texture almost never appears.

## What Changes

- **New deterministic phrase-gesture layer**: one bounded phrase effect (rotating Morph/Curtain/Fill, keyed to section identity like the carrier rotation, filtered by energy band) spanning ~4 bars on the hero/broad group, placed in `full`/`pulse` treatment sections. Withholding treatments (`feature`/`gesture`/`rest`) are untouched.
- **Carrier rotation rebalanced**: Garlands dropped; SingleStrand double-weighted — `("SingleStrand", "Bars", "SingleStrand", "Wave")` — matching the community's chase-dominant fabric while keeping variety.
- **Fallback weave texture**: when a section's own effect vocabulary yields no cellable texture, default the texture recipe to Ripple on the section's broad groups (community 3.1%, cell-able, currently near-zero for us) instead of omitting it.
- **VU Meter loosened one notch**: placed in `pulse` treatment sections as well as `full` (still at most one per section, same seeding).
- Golden regen once.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `show-orchestration`: a deterministic phrase-gesture layer exists (treatment-gated, identity-rhymed); the carrier rotation and fallback texture reflect community shares; VU Meter placement extends to pulse sections.

## Impact

- `packages/xlights-orchestrator/src/xlights_orchestrator/pipeline/beats.py` — new `place_phrase_gesture` (model: `place_vu_meter`, ~line 630).
- `packages/xlights-orchestrator/src/xlights_orchestrator/pipeline/generate.py` — call site in `realize_section` + the treatment table's gating; VU call moves from `extras`-only.
- `packages/xlights-orchestrator/src/xlights_orchestrator/pipeline/weave.py` — `CARRIER_ROTATION`, `fallback_weave` texture default.
- Tests: beats/weave units + golden regen. Depends on nothing else in this series (can land in any order; golden conflicts with the other three changes are regen-trivial).
