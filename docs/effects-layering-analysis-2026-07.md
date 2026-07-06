# Re-measurement: Density & Motion Fabric vs Community Practice (2026-07)

*Successor to `effects-layering-analysis.md` (2026-06-11). Data produced reproducibly by
`scripts/measure_fabric.py` (capability `fabric-measurement`) — one report shape, two input modes
(`stats_from_instructions` over an instructions cache / the golden fixture; `stats_from_xsq` over a
finalized `.xsq`, community or ours). The §2.1 community aggregates are frozen into the tool's
`COMMUNITY` constant so the comparison runs without the licensed, machine-local corpus.*

## TL;DR — the inversion is closed (indeed over-corrected) in the real pipeline

The 2026-06-11 study found the generated fabric **inverted** relative to community practice: ~16%
continuous-motion vs ~58%, dominated by `On`/`Twinkle` punctuation. The wave of changes it drove
(cell fabric, counter-phase chases, motion value curves, blends, transitions, duration taxonomy
v0.3) **worked** — and the re-measurement of *real generated shows* shows motion is now the
dominant family, at or above the community share:

| Show (measured `.xsq`) | effects/min | motion | punctuation | On+Twinkle | top type |
|---|---:|---:|---:|---:|---|
| **ours** — `02 - Candy Cane Lane` | 214 | **97%** | 0% | 0% | SingleStrand 39% |
| **ours** — `Cher …__baseline` | 2,528 | **68%** | 30% | 7% | Spirals 34% |
| **ours** — `Cher …__treatment` (Phase-2) | 1,418 | 30% | 54% | 13% | Shockwave 29% |
| community — `Candy Cane Lane - Sia` (John Storms) | 187 | 31% | 61% | 61% | On 61% |
| community — `Baby Shark …` (John Storms) | 160 | 36% | 33% | 32% | On 32% |
| community — `1984 - Van Halen` | 54 | 15% | 73% | 53% | On 43% |

Two things jump out, and they reframe the whole item:

1. **Our real output already meets/exceeds the motion target.** `Candy Cane Lane` is 97% motion;
   `Cher baseline` 68%. The cell-fabric paradigm shipped and is dominant. The "58% community" number
   is no longer a stretch goal — we're past it on the shows we generate.
2. **These particular community shows are *lower* motion / *lower* density than the 2026-06-11
   corpus aggregate** (~1,300/min, ~58% motion). The aggregate was dominated by a few dense,
   per-prop mega-displays; the John-Storms group-targeted shows here measure 160–214/min and
   punctuation-heavy. This is exactly why a single global goalpost is wrong (§Targets).

The `Cher …__treatment` row (a Phase-2 treatment-aware variant) sits at 30% motion / 54%
punctuation *on purpose* — it withholds fabric in quiet/`pulse` sections. A show-level number that
drops after Phase 2 is expected and correct; the gap is evaluated per treatment (§Targets).

## The golden fixture is the outlier — and that is fine (it is the CI canary, not a real show)

`stats_from_instructions` over `tests/fixtures/golden_instructions.json` (the hermetic 24s, 2-section
fixture):

```
total: 103 effects over 24s  = 258 effects/min   (prop-row-equiv ×23.8 = 6,128/min)
family: motion 25%  punctuation 74%  bed 0%  feature 0%  other 1%
by type: On 39%, Twinkle 23%, SingleStrand 12%, Bars 12%, Shockwave 12%, …
On+Twinkle: 62%
per section:  §0 i=0.45: 185/min, motion 32%, On+Tw 68%
              §1 i=0.92: 265/min, motion 26%, On+Tw 72%   ENERGETIC
```

The golden **still measures inverted** (25% motion, On the #1 effect) — but it is a *TestModel stub*,
not a real show: its weave is a single `On` carrier + one `Twinkle` texture (the fixture hand-writes
that recipe), it has no LLM-designed motion recipes, and its peak section is deliberately
fill/flash-heavy. Its punctuation share is an artifact of the stub, not of the generator. So:

- The golden is the **reproducible-in-CI canary** that proves the tool runs forever and guards
  against *re-inversion* (a future change that pushes motion back down trips
  `tests/test_fabric_stats.py`). Its loose bounds (motion ≥ 20%, On+Twinkle ≤ 75% on the energetic
  section) have headroom above the current 26%/72% precisely because the stub is punctuation-heavy
  by construction.
- The **honest goalposts** are the real-`.xsq` numbers above, not the golden's.

### Source attribution answers "why so many `On` rows"

The transient `source` tag (Decision 8; `Field(exclude=True)`, never persisted) makes the golden's
`On` provenance legible — `stats_from_effect_instructions` on an in-process golden run reports:

```
On: accents:36, bed:1, flash:1, generator:2
Twinkle: weave:24        SingleStrand: weave:12     Bars: weave:12
Shockwave: triggers:12   VU Meter: vu:1
```

The 40 `On` rows are **36 beat-accents** + a bed + a flash + 2 generator. The accent layer is the
punctuation source, exactly as Decision 6.1 predicted — so the rebalance lever is `SPARKLE_TOP_N` /
`carrier_covers`, not the weave.

## Prop-row-equivalent normalization

The 2026-06-11 comparison compared per-prop community rows against our SEM_-group rows. The tool
computes `per_prop_expansion` = mean member-count of the SEM_ groups in `rgbeffects.xml`
(**~23.8 props/group** on the current layout). But the normalization only matters for the
**instructions cache** (which targets SEM_ groups, one row per group): there, prop-row-equivalent =
raw × 23.8. A **finalized `.xsq` already targets individual props** (`06_PROP_Arch`, …) — placement
has expanded the group rows — so in `.xsq` mode raw *is* the prop-row number and no scaling applies.
On the shared 8-prop layout, our `02 - Candy Cane Lane` (214/min prop-rows) is slightly denser than
community `Candy Cane Lane - Sia` (187/min) — well within the "≤ 2× community typical" band.

## Targets — what "closed" means (energetic sections only)

Energetic = intensity ≥ 0.5 OR, post-Phase-2, treatment ∈ {`full`, `feature`}. Quiet / `rest` /
`gesture` / `pulse` sections are **exempt** — deliberate stillness is a feature, not a regression.
These replace "community does 58%" as the goalpost and are the single enforced copy of the numbers
that the QA advisory floor and the canary literals cite.

1. **Motion share ≥ 0.45** in energetic sections. Our real shows are 68–97%; the advisory floor
   (`MOTION_SHARE_MIN`) rises 0.30 → **0.40** now that the generator clears it, staying just under
   the target so it does not spam the Judge on legitimately mixed sections.
2. **On + Twinkle ≤ 0.30** in energetic sections. Our real shows are 0–13%. The golden stub is 72%
   (a stub artifact); the canary ceiling is a loose **0.75** so re-inversion still trips it.
3. **Prop-row-equivalent density within ~2× community typical** at peak (≈ 600–900/min prop-rows;
   our real shows are 187–2,528/min prop-rows depending on layout size). `cell_budget`'s current
   peak (~600 group-rows/min) is left **unchanged** — a `BUDGET_SCALE` raise is *not* warranted,
   because the real fabric is already dense enough and denser reads as noise (the item's headline
   risk). See §Tuning.
4. **Pixel-level motion corroborates (I8 Tier 0).** Instruction counts are the author-side proxy;
   the rendered frame-delta is the product. Deferred to I8; consumed here as corroboration, not
   gated on.

## Tuning decisions (rebalance-first, one lever per commit, golden-regen per step)

The re-measurement changes the tuning plan from "raise density" to "**rebalance the golden's
punctuation, hold the real fabric, do not add density.**"

- **4.1 Rebalance punctuation down — DONE.** `SPARKLE_TOP_N` 12 → 8 (`pipeline/tuning.py`): the
  sparkle layer rides fewer drum hits, cutting `On`/`Twinkle` accents in energetic sections. Golden
  regenerated once. This is the one dial the re-measurement clearly supports (the accent layer is
  the golden's punctuation source, per attribution).
- **4.2 Weave voice count — HELD.** `MAX_WOVEN_RECIPES` stays 3. The real shows are already
  motion-dominant; a 4th texture voice adds density the re-measurement does not ask for and risks
  the noise failure. Deferred to a live-watched follow-up if a future show measures thin.
- **4.3 Budget raise — NOT DONE (deliberately).** `BUDGET_SCALE` stays 480. Target 3 is met at peak;
  raising it chases per-prop community numbers on a layout that is already dense enough. The budget
  raise is the *last* lever and the measurement withholds permission.
- **5.2 Advisory floor.** `MOTION_SHARE_MIN` 0.30 → 0.40, cited to this doc, evaluated only on
  energetic sections (the intensity gate + treatment exemption already exist in `qa/rules.py`).

## Reproduce

```
# our honest number (a real run's instructions cache), with per-section intensities + prop-row norm
python scripts/measure_fabric.py <cache>/<song_key>/instructions.json \
    --show-plan <cache>/<song_key>/show_plan.json --rgbeffects <show>/xlights_rgbeffects.xml

# a finalized .xsq (community OR ours) — parses <Effect> elements, no xLights needed
python scripts/measure_fabric.py "<show>/<name>.xsq" --rgbeffects <show>/xlights_rgbeffects.xml

# the hermetic canary input
python scripts/measure_fabric.py --golden --duration-s 24
```

## Open questions (carried from design)

- **Community corpus custody** — a redacted per-file stats JSON could be checked into `docs/` so the
  comparison is fully reproducible in-repo without the licensed `.xsq`. The frozen `COMMUNITY`
  aggregates cover the goalpost meanwhile.
- **Measure the `.fseq` instead?** Post-I8, the canary bounds may move to pixel metrics and let the
  instruction stats be diagnostic only.
- **Layer depth** — community stacks to 19; our hard cap is 4 (`clamp_layer_budget`). Community shows
  here measured max 2–7 layers, so 4 is not the current bottleneck; a hero-only raise stays a
  separate change.
