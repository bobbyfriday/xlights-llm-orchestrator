# add-blend-vocabulary

## Why

Our blend usage is a monoculture: 55% of our placed rows carry a `T_CHOICE_LayerMethod` and **98.6% of those are `Max`** (2026-07-07 corpus comparison, memory: `corpus-alignment-2026-07`). The community blends only ~10% of rows but with a real vocabulary: **Brightness 36%, Layered 23%, mask/unmask family ~21%, reveals ~6%** — and the layering guide itself already warns "Masking is the community's dominant blend, not Max/Average… Our weaver defaults to Max" (`xlights-layering-rendering-guide.md` ~line 201). Two community looks we cannot currently produce:

1. **The traveling brightness gate** (their top blend, drilled 2026-07-07): short motion cells — Shockwave 256, Spirals 236, SingleStrand 203, On 184 rows, median 950 ms — with `LayerMethod=Brightness` placed OVER a texture/bed, so the cell's own luminance shape sweeps through the layer below (an example community row is literally a bare `On` with only `T_CHOICE_LayerMethod=Brightness` — an On pulse used as a beat-gate on the bed). Our weave already places short cells over beds in exactly this geometry; it just always blends Max.
2. **The shaped reveal**: Shape over a texture with `1 is Mask` — Shape+Spirals is the #3 stacked pair in the whole community corpus (1,189 pairs; guide §9 recipe 2).

## What Changes

- **Weave blend defaults become role-aware**: texture-role cells over a based target default to `Brightness` (the traveling gate); carrier cells keep `Max` (additive pop, unchanged); an explicit LLM-chosen `blend` on a recipe always wins (existing field, existing plumbing — this is a default change in one place).
- **New curated composite `reveal`**: a texture base (Spirals) under a `Shape` layer blended `1 is Mask` — the community's Shape-reveals-Spirals showpiece — added to the peak-composite rotation.
- **Fabric measurement reports blend VALUES**: `FabricStats` gains a blend-value distribution (share of Max / Brightness / mask-family / other among blended rows) so this axis is measurable against community; the frozen `COMMUNITY` aggregates gain the measured value shares.
- Generator guidance: the existing prompt already names `'Brightness' envelopes` — add one sentence that texture cells over a bed default to Brightness and Max need not be specified.
- Golden regen once (texture-cell blend values change).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `show-orchestration`: weave texture cells over a base default to the Brightness blend; a curated mask/reveal composite exists and rotates at peaks.
- `fabric-measurement`: stats include the blend-value distribution, comparable to frozen community aggregates.

## Impact

- `packages/xlights-orchestrator/src/xlights_orchestrator/pipeline/weave.py` — `_cell` blend default; `CURATED_COMPOSITES` + peak rotation.
- `packages/xlights-orchestrator/src/xlights_orchestrator/pipeline/generate.py` — `_PEAK_COMPOSITES` tuple.
- `scripts/measure_fabric.py` — blend-value distribution in `_Row`/`FabricStats`/`render_report` + `COMMUNITY` constants; canary literals in `tests/test_fabric_stats.py`.
- Generator prompt text (one sentence).
- Interaction: `add-counter-rotation` also edits `CURATED_COMPOSITES` (kaleidoscope/bloom) — land that change first; this one only ADDS the `reveal` entry.
