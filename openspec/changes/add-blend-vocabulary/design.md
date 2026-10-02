# add-blend-vocabulary — design

> Executor note: anchors as of commit `1cd742d` (2026-07-07). The one subtle domain fact you need:
> **layer conventions are inverted between the two worlds.** In a finalized `.xsq`, the FIRST
> `<EffectLayer>` (index 0) is L1 = the TOP layer (see `agents/generator.py` scene note: "The
> cookbook's L1 is the TOP layer → `layer` 0"). In OUR emitter, a HIGHER layer index renders on
> top (verified live — see `_top_layer` in `effect_emitter.py`). A `T_CHOICE_LayerMethod` always
> rides the UPPER layer and describes how it combines with the layer(s) below it.

## Context

Blend plumbing already exists end-to-end: `CellRecipe.blend` (LLM-settable), `_cell` in
`packages/xlights-orchestrator/src/xlights_orchestrator/pipeline/weave.py` (~line 336) applies
`extra["T_CHOICE_LayerMethod"] = recipe.blend or "Max"` when `blended=True` (the cell sits on a
target that has a base layer under it), `CompositeLayer.blend` flows through `expand_composite`,
and the emitter merges extra settings over the look. Nothing needs new plumbing — only defaults,
one new recipe, and measurement.

Corpus grounding (2026-07-07 drill-down):

- Community blended-row value shares: Brightness 36.0%, Layered 22.8%, Effect 1 8.5%, the
  mask/unmask family ≈ 20.7%, reveals ≈ 6.2%, Max ≈ 0% (not in their top 10). Ours: Max 98.6%.
- Community `Brightness` rows are SHORT MOTION CELLS over a base: Shockwave 256, Spirals 236,
  SingleStrand 203, On 184; median 950 ms; almost none carry value curves — the effect's own
  moving luminance IS the envelope. (An observed row: settings string = just
  `T_CHOICE_LayerMethod=Brightness` on a bare On.)
- Shape-over-Spirals (mask/reveal) = 1,189 stacked pairs, #3 combo in the corpus; layering guide
  §9 recipe 2 ("Shaped reveal… '1 is Mask'; invert with UnMask if polarity looks wrong").

## Goals / Non-Goals

**Goals:**
- Texture cells over a bed read as traveling brightness gates (community's dominant blend).
- One curated mask/reveal composite in the peak rotation.
- Blend-value distribution measurable in `measure_fabric` with frozen community goalposts.

**Non-Goals:**
- `Layered` / `Effect 1` / `Average` blend modes — additional vocabulary, no evidence they beat
  Brightness/mask for our looks; revisit after a live watch.
- LLM-side blend planning changes beyond one prompt sentence (the field already exists).
- Mask support in weave CELLS (community mask rows ride longer spans; cells are 1–4 beats — the
  composite is the right vehicle).
- Value-curve beat-ducking envelopes (guide §9 recipe 3, Subtractive) — the corpus says the
  dominant envelope is the moving-cell kind, which we get for free; VC ducking is a possible
  follow-up.

## Decisions

**D1 — Role-aware blend default in `_cell` (weave.py ~line 336).** Replace the constant default:

```python
if blended:
    # Community blend vocabulary (corpus 2026-07-07): texture cells over a base read as
    # TRAVELING BRIGHTNESS GATES (their #1 blend, 36% — Shockwave/Spirals/chase cells whose
    # luminance sweeps the bed below); carriers stay Max (additive pop over the bed).
    default = "Brightness" if recipe.role == "texture" else "Max"
    extra["T_CHOICE_LayerMethod"] = recipe.blend or default
```

An explicit `recipe.blend` (LLM) always wins — unchanged. Only `role == "texture"` flips; `bed`
cells are never blended (`blended=False` path) and `carrier`/`accent` keep Max. Note
`expand_weave` computes `blended` = target has a bed or the carrier under it (~line 402) — a
Brightness gate always has something real below it by construction; over a *carrier* (not a wash)
the gate still reads (the carrier is lit whenever the gate samples it).

**D2 — Curated `reveal` composite (weave.py `CURATED_COMPOSITES`).** Add:

```python
# a Shape reveal over a spiral texture — the community's #3 stack (1,189 Shape+Spirals pairs);
# the Shape's lit pixels reveal the texture below ("1 is Mask"; guide §9 recipe 2)
"reveal": [CompositeLayer(effect_type="Spirals"),
           CompositeLayer(effect_type="Shape", blend="1 is Mask")],
```

And add `"reveal"` to `_PEAK_COMPOSITES` in `pipeline/generate.py` (~line 62), making the rotation
5 long. Shape has 54 mined looks — `candidate_look_ids("Shape")` is non-empty (expand_composite
skips layers with no looks; verify in the test). **Ordering dependency**: `add-counter-rotation`
rewrites the `kaleidoscope`/`bloom` entries in this same dict — land it first; this change only
adds a key (merge-trivial either way, but the tests in both changes touch neighboring lines).

Polarity risk is real (guide: "If Mask looks wrong, try UnMask"): after implementing, do one live
render check (drop a `reveal` composite on the hero in a scratch sequence via the existing demo
script `scripts/demo_build_sequence.py` if runnable, or eyeball the golden's peak section in
xLights) — if the texture shows OUTSIDE the shape instead of inside, switch the blend string to
`"1 is Unmask"`. Record which polarity won in the composite's comment.

**D3 — Blend-value distribution in `measure_fabric.py`.** `_Row.blend: bool` becomes
`blend_value: str` (empty = none); `_row_from_instruction` / `_row_from_xsq_effect` read the
actual `T_CHOICE_LayerMethod` value (both already parse it). `FabricStats` gains
`blend_value_share: dict[str, float]` — shares among BLENDED rows, bucketed:
`{"Max", "Brightness", "mask" (any value containing "Mask"/"Unmask"/"reveals"), "other"}`.
Keep `blend_mode_share` (share of all rows carrying any blend) unchanged for compatibility.
`COMMUNITY` gains `blend_value_brightness_share=0.36`, `blend_value_mask_share=0.27`
(mask family + reveals), with a comment citing this change. `render_report` prints one extra line.
Extend the canary literals in `tests/test_fabric_stats.py` LOOSELY (e.g. golden's Max share ≤ 0.95
after D1) — the canary's job is to catch re-inversion to all-Max, not to pin exact numbers.

## Risks / Trade-offs

- [A Brightness gate over a DIM bed reads darker than today's Max] True and intended — Max adds
  light, Brightness modulates it; texture cells will read as bed-colored motion rather than extra
  light. The bed floor (`_DIM_BED_BRIGHTNESS` 55, `WEAVE_BED_BRIGHTNESS`) keeps a floor under it.
  If a live watch shows dark textures, the dial is: texture default flips only when intensity ≥
  0.5 (add the gate in `_cell` — it already receives `intensity`). Do not pre-build; note in PR.
- [LLM recipes that relied on the old always-Max default] `diversify_carrier` and scene stacks set
  explicit blends where they matter; the golden diff will show the actual blast radius — eyeball
  it (expected: texture-role weave cells only).
- [Mask polarity backwards] → D2's live-check step; one string to flip.
- [`_Row.blend` field type change breaks external users of measure_fabric] It's a repo-internal
  dataclass consumed by `_stats`/tests only; grep `rg "\.blend\b" scripts tests` and fix the two
  call sites.

## Migration Plan

Single PR (branch `feat/blend-vocabulary`), after `add-counter-rotation` merges. Order: D3
(measurement first — capture a BEFORE report on a real cache: `uv run python
scripts/measure_fabric.py data/analyses/orchestrator/e1a6805bc78a0643/instructions.json`) → D1 →
D2 → golden regen → AFTER report in the PR description. Rollback = revert.

## Open Questions

- Peak-composite rotation length grows to 5 — recurring-label shows will see `reveal` roughly every
  5th peak identity. Fine at this scale; revisit if the rotation grows further.
