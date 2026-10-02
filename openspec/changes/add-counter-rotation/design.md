# add-counter-rotation — design

> Executor note: this doc contains exact file anchors and corpus-verified values. Line numbers are
> as of commit `1cd742d` (2026-07-07); re-locate by symbol name if they drift. Read the cited code
> before editing — the mechanisms referenced here (direction_setting, counter-phase pairing,
> extra_settings merge) all already exist and are being extended, not invented.

## Context

Direction handling has one pipeline: a per-effect table maps abstract directions to effect-native
settings (`EFFECT_META[et].directions` in
`packages/xlights-orchestrator/src/xlights_orchestrator/pipeline/effect_meta.py`, re-exported as
`DIRECTION_KNOBS`), and `direction_setting(effect_type, direction, bar)` in
`packages/xlights-orchestrator/src/xlights_orchestrator/pipeline/weave.py` (~line 90) resolves a
recipe's direction to `{key: value}` extra settings. Unmapped effects return `{}` **silently** —
never an error. Extra settings override the mined look's frozen values at emit time
(`_merge_extra_settings` in `packages/xlights-core/src/xlights_core/editing.py`, ~line 36 —
override-then-append, because xLights honors the FIRST duplicate key). So the only reason Spirals
can't be steered is the missing table row.

Corpus facts (verified against `packages/xlights-core/src/xlights_core/knowledge/presets/looks.json`,
2026-07-07):

- `E_SLIDER_Spirals_Rotation` appears in 84 Spirals looks: 66 positive, **16 negative** — a signed
  slider, negative = counter-clockwise, corpus-observed on both sides. Typical magnitudes 20 and 80.
- `E_SLIDER_Ripple_Rotation` appears in 22 Ripple looks (plus `E_VALUECURVE_Ripple_Rotation` in 13).
- Morph has **zero** direction/rotation keys in the corpus — it cannot be steered by knob.
- Community same-type stacked pairs run opposite directions: SingleStrand 63%, Spirals 47%,
  Pinwheel 30% (17 community .xsq, 27,099 effects).
- Community Spirals placements: 690 cw / 334 ccw / 638 value-curve-animated. Ours: 0 ccw ever.

The chase family already has a working counter-phase mechanism: `_valid_recipes` (weave.py ~line
264) detects two static ltr/rtl chase recipes on overlapping groups and upgrades both to per-bar
`alternate` in opposite phase. This change builds the rotational twin of that rule.

Value curves: `motion_curve_setting(effect_type, curve, intensity)` in
`packages/xlights-core/src/xlights_core/knowledge/value_curves.py` (~line 64) builds spin ramps as
`start, end = 0.0, hi * (0.3 + 0.7 * level)` — positive only, though the corpus ranges are signed
(Spirals_Rotation −300…+300, Pinwheel_Twist −360…+360, Ripple_Rotation −360…+360).

Curated composites: `CURATED_COMPOSITES` (weave.py ~line 432). `kaleidoscope` = Morph ltr + Morph
rtl and `bloom` = Spirals ltr + Fan rtl both claim counter-motion that silently no-ops (Morph and
Spirals unmapped; Fan maps only center_out/center_in). `expand_composite` (~line 454) already calls
`direction_setting(lyr.effect_type, lyr.direction, i)` per layer — it will start working the moment
the rows exist and the directions name mapped values.

## Goals / Non-Goals

**Goals:**
- Spirals and Ripple respond to `ltr`/`rtl` (and therefore to `alternate`/`bounce` per-bar
  flipping, which `direction_setting` derives from the ltr/rtl pair automatically).
- Spin motion curves can ramp negative.
- Same-type rotational stacks on one target counter-rotate automatically, in all three placement
  paths (weave recipes, composite layers, generator instructions).
- The four curated composites all produce *real* motion contrast.

**Non-Goals:**
- Section-to-section spin variety for a *single* (unstacked) spiral — a separate, later change
  (would ride the same table rows; see `effect-variety-audit` memory).
- Look-menu seeding/rotation (tracked separately in the audit).
- Morph steering via its start/end corner coordinates (`E_SLIDER_Morph_Start_X1` etc.) — fiddly,
  no corpus-mined vocabulary for it; out of scope.
- Any change to Pinwheel/Fan/Butterfly/Galaxy rows — already mapped correctly.
- QA advisories for direction monotony — the deterministic pass makes them redundant here.

## Decisions

**D1 — Table rows (effect_meta.py).** Add to the existing `EffectMeta` rows (keep the row-comment
provenance style of the file):

```python
"Spirals": EffectMeta(
    speed=("E_TEXTCTRL_Spirals_Movement", 0.5, 4, "f1"),
    directions={"ltr": ("E_SLIDER_Spirals_Rotation", "20"),
                "rtl": ("E_SLIDER_Spirals_Rotation", "-20")},
    energy_band=(2, 5), duration_class="cellable"),
"Ripple": EffectMeta(
    speed=("E_TEXTCTRL_Ripple_Cycles", 1, 8, "f1"),
    directions={"ltr": ("E_SLIDER_Ripple_Rotation", "20"),
                "rtl": ("E_SLIDER_Ripple_Rotation", "-20")},
    energy_band=(2, 3), duration_class="cellable"),
```

Magnitude 20 is the corpus-typical value (Spirals frozen values are 20 and 80; 20 is the mode).
Values are strings — the table stores `(key, value)` string pairs. `DIRECTION_KNOBS` is a derived
view; no other wiring needed. Rationale for ltr/rtl naming (not cw/ccw): the whole direction
vocabulary (`CellRecipe.direction`, the generator prompt, `direction_setting`'s per-bar flip
which looks for an `ltr`/`rtl` pair) is built on ltr/rtl; a new pair name would need parallel
plumbing for zero benefit.

**D2 — Signed spin curves (value_curves.py).** `motion_curve_setting` gains a keyword-only
`sign: int = 1`. For `kind == "spin"`: `end = (hi if sign >= 0 else lo) * (0.3 + 0.7 * level)`
(lo is already negative for all spin params, so magnitude scaling is symmetric); `start` stays 0.
Sweep kind ignores `sign`. Callers that don't pass it are unchanged (default 1) — golden-safe
except where D3 threads a −1.

**D3 — Auto counter-rotation, three placement paths.** Define once in weave.py:

```python
# Rotational effects: have an ltr/rtl direction pair but are NOT linear chases — their
# "direction" is spin. The chase counter-phase rule (below) covers the chase family.
ROTATIONAL_EFFECTS = frozenset(
    et for et, m in EFFECT_META.items()
    if "ltr" in m.directions and "rtl" in m.directions and not m.chase_family)
```

(After D1 this is {Spirals, Ripple, Pinwheel, Butterfly}. Import EFFECT_META — weave.py already
imports from effect_meta.)

- *Weave recipes* — in `_valid_recipes`, after the existing chase counter-phase block: for each
  pair of recipes with the SAME effect_type in `ROTATIONAL_EFFECTS`, overlapping groups, and BOTH
  with empty `direction`, set the first's direction to `"ltr"` and the second's to `"rtl"`.
  Explicit LLM-chosen directions are never overridden.
- *Composite layers* — in `expand_composite`: when two layers share an effect_type in
  `ROTATIONAL_EFFECTS` and the later layer has no explicit `direction`, assign `"ltr"` to the
  first and `"rtl"` to the later one before the existing `direction_setting` call. Additionally,
  when a layer's `motion_curve` is a spin kind, thread `sign=-1` into `motion_curve_setting` for
  odd layer indexes so curved rotations counter-phase too.
- *Generator instructions* — new pure function in weave.py:

  ```python
  def counter_rotate_stacks(instrs: list[EffectInstruction]) -> None:
      """Same-type rotational effects overlapping on the same target: alternate the spin of
      each successive layer (2nd, 4th, ... get rtl) via extra_settings, unless the instruction
      already carries that effect's direction key. In-place; deterministic (list order)."""
  ```

  Group by `(target, effect_type)` for types in `ROTATIONAL_EFFECTS`, sort by `(layer, start_ms)`,
  detect time overlap between successive members, and on the 2nd/4th/… overlapping instruction set
  `extra_settings[key] = rtl_value` — skipping any instruction whose `extra_settings` already has
  that key (an explicit direction wins). Call it from `realize_section` in
  `packages/xlights-orchestrator/src/xlights_orchestrator/pipeline/generate.py`, immediately
  before `clamp_hard_caps(kept, …)` — `realize_section` is shared by first-pass, refine, and
  `xlo regen`, so all paths get it with one call site.

  Why "always flip the upper" rather than a seeded choice: it's structural (no seed to
  maintain), matches the community pattern (the pair is the look), and repeated sections rhyme
  automatically because the base layer keeps the look's native spin.

**D4 — Composite redefinition (CURATED_COMPOSITES in weave.py).**

```python
# two counter-rotating Spirals blended Max — the canonical megatree showpiece
# (layering guide §9 recipe 7; Morph cannot be steered by knob — zero direction keys in corpus)
"kaleidoscope": [CompositeLayer(effect_type="Spirals", direction="ltr"),
                 CompositeLayer(effect_type="Spirals", direction="rtl", blend="Max")],
# radial bloom: Spirals rotating against a Fan unfolding outward
"bloom": [CompositeLayer(effect_type="Spirals", direction="ltr"),
          CompositeLayer(effect_type="Fan", direction="center_out", blend="Max")],
```

`swirl` (Galaxy + Butterfly) and `ember` (Plasma + Fire, Brightness blend) are untouched — they
never claimed directional counter-motion. Note kaleidoscope becomes a same-type pair, which D3's
composite rule would also have handled; the explicit directions make the intent legible.

## Risks / Trade-offs

- [Golden churn] Direction keys now appear in extra_settings for Spirals/Ripple cells with
  directions, and peak composites change effect types. → One golden regen
  (`XLO_REGEN_GOLDEN=1 uv run pytest tests/test_golden_pipeline.py`), one commit, per repo
  convention. Eyeball the diff: expect ONLY added `E_SLIDER_Spirals_Rotation`/
  `E_SLIDER_Ripple_Rotation` keys and the composite swap.
- [xLights rejects a negative slider via HTTP] Corpus shows negative frozen values in real
  community sequences, so the value is valid in the settings string; `extra_settings` bypass knob
  validation by design (they merge post-assembly). Risk is low; if a live smoke test shows
  `ApplySetting` errors in the xLights log, fall back to magnitude-only flip via the
  `E_VALUECURVE_Spirals_Rotation` ramp (D2) instead — but do not pre-emptively build that.
- [Double-steering: a look with frozen rotation + our extra setting] Not a conflict —
  `_merge_extra_settings` REPLACES the frozen key (first-occurrence-wins is why it overrides
  in place). The look keeps its other character (count, thickness, 3D).
- [`alternate`/`bounce` on Spirals cells now flips sign per bar] This is new behavior for any LLM
  recipe that already said `direction: alternate` on Spirals (previously a silent no-op). It is
  the *intended* semantics; flag in the PR description so the visual diff is expected.

## Migration Plan

Single PR (branch `feat/counter-rotation`, PR to `main` per repo workflow — never commit direct).
Order: D1+D2 (+ unit tests) → D3 → D4 → golden regen last, one commit. Rollback = revert the PR;
no data or schema migration.

## Open Questions

(none blocking — magnitude 20 vs 80 for Spirals is a taste call; 20 chosen as the corpus mode,
revisit after a live watch)
