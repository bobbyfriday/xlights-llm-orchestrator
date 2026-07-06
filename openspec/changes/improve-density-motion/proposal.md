## Why

The 2026-06-11 corpus study (`docs/effects-layering-analysis.md` — 130,229 effects mined from 17
community/vendor `.xsq` files vs 2,265 effects across our two generated shows) found the generated
fabric **inverted** relative to community practice: community shows are ~58% continuous-motion
effects at ~1,300 effects/min placed as 0.3–0.9s beat-quantized cells; ours were ~16% motion at
~270 effects/min, dominated by punctuation (On 22%, Twinkle 23%) over long washes. That analysis
drove a burst of changes (cell fabric, counterphase chases, motion value curves, blend modes,
transitions, duration taxonomy v0.3) which **partially** closed the gap — but nobody has re-measured
since.

The number that justified the whole cell-fabric paradigm is now a month stale, the tuning dials in
`weave.py`/`tuning.py` were set by judgment rather than against a measurement, and improve-musicality
Phase 2 is about to make "density" a per-treatment concept. Running today's corpus metrics over the
golden fixture confirms the inversion is still visibly present in what the deterministic layers emit:
103 instructions over 24s (~258 effects/min), motion share 24.3% (below the 0.30 advisory floor),
punctuation (On+Twinkle+Shockwave) 73.8%, median duration collapsed from 49–88s washes to 1.0s (so
the duration fix landed, but On is still the #1 effect).

This item is: **re-measure, then tune against the measurement — with treatment-aware targets, not
one global number.**

## What Changes

- **New measurement tool `scripts/measure_fabric.py`** with two input modes and one report shape so
  community `.xsq` files and our shows produce directly comparable tables: `stats_from_instructions`
  (over an `instructions` cache or the golden fixture) and `stats_from_xsq` (parsing `<Effect>`
  elements from a finalized `.xsq`). It reports a `FabricStats` dataclass — effects/min, share by
  family (motion/punctuation/bed/feature/other), share by type, median duration by type, blend-mode
  and transition share, value-curve kinds, layer-depth histogram, a **prop-row-equivalent
  normalization** (`per_prop_expansion`), and **per-section** stats bucketed by intensity (and,
  post-Phase 2, treatment).
- **Prop-row-equivalent normalization** — the critical fix to the original comparison: community
  sequences target individual prop rows; ours target ~15 SEM_ groups where one group-level effect
  animates every member prop. Report both raw effects/min and prop-row-equivalent effects/min
  (`raw × expansion`) using the mean member-count of the groups we actually target.
- **A committed 2026-07 re-measurement doc** (`docs/effects-layering-analysis-2026-07.md`) that
  quantifies the current gap on ≥1 full real show with the normalization and per-section breakdown,
  and records explicit treatment-aware targets (motion share, On+Twinkle share, density band)
  replacing "community does 58%" as the goalpost.
- **Tuning the fabric levers against the measurement, one lever per commit**, in rebalance-first
  order: lower punctuation (`SPARKLE_TOP_N` 12 → ~8, let `carrier_covers` suppress more On accents),
  raise the weave's voice count (`MAX_WOVEN_RECIPES` 3 → 4, richer `fallback_weave`), then raise the
  budget (`BUDGET_SCALE` 480 → ~700) only if the I8 motion metric agrees, then raise the advisory
  floor (`MOTION_SHARE_MIN` 0.30 → 0.40–0.45).
- **A per-layer `source` attribution** surfaced only in the measurement report (transient, excluded
  from persisted schemas) so tuning knows whether an `On` row is a bed, an accent, or an LLM wash.
- **A hermetic fabric-stats canary test** guarding the golden fixture against silent re-inversion,
  with treatment-aware bounds that exempt quiet/`rest`/`gesture` sections so improve-musicality
  Phase 2's deliberate sparseness cannot register as a density regression.

This change is thematically adjacent to (and sequenced after) improve-musicality Phase 2, but is its
own change. It references that change where they interact (per-treatment density, shared
`FabricStats.per_section` plumbing) but does not modify it.

## Capabilities

### New Capabilities
- `fabric-measurement`: a reproducible corpus-comparison measurement of a show's effect fabric
  (density, motion-vs-punctuation share, duration, blend/transition/value-curve usage, layer depth)
  from either an instructions cache/golden fixture or a finalized `.xsq`, with prop-row-equivalent
  normalization and per-section, intensity-bucketed breakdown.

### Modified Capabilities
- `show-orchestration`: the cell-density budget and the motion-share advisory become
  measurement-tuned and treatment-aware — density targets and the advisory floor cite the 2026-07
  re-measurement and are evaluated only on energetic (`full`/`feature`) sections, with quiet/`rest`/
  `gesture` sections exempt.
- `show-refinement`: QA gains a hermetic fabric-stats canary that guards the golden fixture's
  motion-vs-punctuation shares against re-inversion (treatment-aware, energetic sections only).

## Impact

- New `scripts/measure_fabric.py` (`stats_from_instructions`, `stats_from_xsq`, `FabricStats`,
  `SectionStats`, frozen community aggregates from §2.1, per-group expansion from `rgbeffects.xml`
  modelGroups — parsing already exists in `xlights_core/knowledge/layout_semantics.py`).
- Tuning of constants in `pipeline/tuning.py` (`BUDGET_BASE`/`BUDGET_SCALE`, `SPARKLE_TOP_N`,
  `MAX_ACCENTS_PER_SECTION`, `HERO_MAX_ONSETS`, `BASS_MAX_ONSETS`) and `pipeline/weave.py`
  (`MAX_WOVEN_RECIPES`, `fallback_weave`, `_slot_targets`, `cell_budget`), each cited in a comment to
  the re-measurement doc (house style: "Revision-log analysis (42 runs): …").
- `qa/rules.py` (`MOTION_SHARE_MIN`, `MOTION_EFFECTS`, `MOTION_SHARE_INTENSITY`) advisory-floor
  update once the generator clears it.
- A transient `source` tag on the per-section realization (`pipeline/generate.py::realize_section`)
  or a parallel counter — excluded from `EffectInstruction.model_dump` so cache/golden formats are
  unchanged.
- New docs: `docs/effects-layering-analysis-2026-07.md` (the successor snapshot).
- Tests: new `tests/test_fabric_stats.py` (parser unit tests + golden canary with loose bounds),
  extended motion-share advisory tests when `MOTION_SHARE_MIN` moves. The golden fixture regenerates
  once per deliberate dial change (`XLO_REGEN_GOLDEN=1`), one per commit.
- Risk profile: tuning changes what effects appear where (visual change, no schema change); the
  transient `source` tag must not leak into persisted schemas (cache/golden/I6 drift-guard).
