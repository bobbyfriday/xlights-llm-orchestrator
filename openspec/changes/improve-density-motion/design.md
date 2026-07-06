## Context

The 2026-06-11 corpus study (`docs/effects-layering-analysis.md`) drove a wave of shipped changes,
but the number that justified the cell-fabric paradigm is stale and the fabric dials were set by
judgment, not against a measurement. This change re-measures and then tunes.

### What the analysis found (2026-06-11)

| Metric | Community | Ours (then) |
|--------|-----------|-------------|
| Continuous-motion share (SingleStrand, Spirals, Pinwheel, Ripple, Wave, Bars) | ~58% | ~16% |
| Punctuation/static share (On, Twinkle, Strobe, Shockwave, Lightning, Shimmer) | ~31% | ~83% |
| `On` / `Twinkle` alone | 3% / <1% | 22% / 23% |
| Effects per minute | ~1,300 typical (up to 3,200) | ~270 |
| Median effect duration (top types) | 0.3–0.9s (p90 ≤ ~2–3s) | 49–88s washes existed |
| Blend modes set | Brightness 36%, Layered 23%, masks ~16% | none |
| Value-curved params | motion params (Rotation 30%, Twist, Radius) | 66% Brightness |
| Layer depth | up to 19; 22% of rows multi-layer | max 4 |

### What shipped in response (all archived)

- `2026-06-11-add-cell-fabric` — the paradigm fix: LLM-designed `CellRecipe`s expanded
  deterministically by `pipeline/weave.py` into beat-snapped cells; fallback weave (SingleStrand
  carrier on the rhythm pool); beat-layer rebalance (`carrier_covers` drops the every-beat On chase
  when a carrier owns the pool, weave.py:183–193); motion-share advisory in QA; blend-mode
  correction; duration taxonomy v0.3 ("sustained" → "cell-able", 1–2 bar cells, `normalize_durations`
  chops).
- `2026-06-13-add-counterphase-chases` — opposed ltr/rtl chase pairs upgrade to per-bar
  counter-phase (weave.py:281–298) — the woven figure instead of a perpetual head-on collision.
- `2026-06-14-unblock-color-wash` — Color Wash restored as a placeable bed (was a stale blacklist
  from the GET-encoding bug).
- `2026-06-09-add-value-curve-synthesis`, `2026-06-12-add-directional-sweeps`,
  `2026-06-12-add-settings-hygiene` — motion value curves, per-effect direction knobs
  (`DIRECTION_KNOBS`), real per-effect speed keys (`SPEED_KEYS`).
- Since then: carrier rotation across sections (`CARRIER_ROTATION = ("SingleStrand", "Bars",
  "Garlands", "Wave")`, weave.py:198), composite stacks (multi-effect blended layers,
  weave.py:446–499), in/out transitions (`_VALID_TRANSITIONS`, weave.py:106–112), phrasing soft
  edges, VU meter layer.

### The dials as they stand (candidate tuning levers)

| Lever | Current value / location | Effect on fabric |
|-------|--------------------------|------------------|
| Cell budget | `BUDGET_BASE = 120.0`, `BUDGET_SCALE = 480.0` (tuning.py:46–47); `cell_budget()` = `section_min × (120 + 480·intensity)`, floor 4 (weave.py:155–158). Peak ≈ 600 cells/min. | The primary density dial. The tuning.py comment records the normalization: *"the community's ~1,300/min was per-prop rows; ours weaves group rows (~15 targets), so scaled."* Over budget, cells are thinned via `_downsample` (weave.py:430–434). |
| Recipes per section | `MAX_WOVEN_RECIPES = 3` (weave.py:43) — one carrier + two textures/accents | Caps layer pressure; community hero rows stack far deeper. Raising to 4 adds one texture voice per section. |
| Alternation patterns | `_slot_targets` (weave.py:243–255): `chase` lights 1 group/slot, `sparse` half the slots, `all` every group | Per-slot multiplicity — `all` on an n-group recipe multiplies instruction count ×n. |
| Cell length | `cell_beats` 1–8 (CellRecipe, show_plan.py:88); sweep floor `_SWEEP_MIN_BEATS = 2` (weave.py:100); legato floor `LEGATO_CELL_BEATS_FLOOR = 2` (tuning.py:29) | Shorter cells = more cells = higher density; community medians (0.3–0.9s) are ~1 beat at 120 BPM. |
| Fallback weave richness | 1 carrier + at most 1 texture; non-rhythmic sections get *no* fabric (weave.py:219–240) | When the LLM omits the weave, the fabric is thin by construction. Adding a second texture/accent lifts the floor. |
| Beat-accent layer composition | `MAX_ACCENTS_PER_SECTION = 80`, `SPARKLE_TOP_N = 12`, `HERO_MAX_ONSETS = 40`, `BASS_MAX_ONSETS = 16` (tuning.py:40–52) | These place *punctuation* (On/Twinkle) — the share the analysis said to demote. They interact with `carrier_covers`: lowering accents while raising cells shifts the ratio without changing totals. |
| Motion-share advisory | `MOTION_SHARE_MIN = 0.30`, `MOTION_SHARE_INTENSITY = 0.5`, `MOTION_EFFECTS = DURATION_CELLABLE ∪ {Fire, Galaxy}` (qa/rules.py:40–42) | The Judge-visible target. 0.30 was set below community's 0.58 deliberately; re-measurement decides whether to raise it and/or energy-scale it. |

### A fresh data point: the golden fixture, measured today

Running the corpus-comparison metrics over `tests/fixtures/golden_instructions.json` (the hermetic
24s, 2-section fixture) gives:

```
total: 103 instructions over 24s  ≈ 258 effects/min
by type: On 40, Twinkle 24, SingleStrand 12, Bars 12, Shockwave 12, VU Meter 1, Butterfly 1, Galaxy 1
motion share (DURATION_CELLABLE set): 24.3%      punctuation (On+Twinkle+Shockwave): 73.8%
median duration: 1,000 ms
```

Caveats — this fixture *understates* the real pipeline (24s song; a TestModel weave with a single
Twinkle texture; no LLM-designed recipes; the second section is a peak whose fill/flash layers are
punctuation-heavy by design) — but it demonstrates three things: the measurement is trivially
reproducible in-repo; the median duration collapsed from 49–88s washes to 1.0s; and the *share*
inversion is still visibly present (On is still the #1 effect). The real re-measurement must use a
full generated show, but the direction is clear.

## Goals / Non-Goals

**Goals:**
- Re-measure the density/motion fabric on a current generated show with a reproducible, in-repo tool.
- Replace "community does 58%" as the goalpost with explicit, treatment-aware targets recorded with
  rationale.
- Tune the fabric dials against the measurement, rebalance-first (shares before totals), one lever
  per commit with a before/after delta.
- Guard the result with a hermetic canary so a future change cannot silently re-invert the fabric.
- Keep quiet/`rest`/`gesture` sections exempt so improve-musicality Phase 2's deliberate sparseness
  is never a density regression.

**Non-Goals:**
- Do not chase 58%/1,300 blindly — different layouts (mega-displays sequenced per-prop), different
  tools (copy-paste inflates counts), a different authoring economy.
- No pixel-level motion metric here — that is I8 Tier 0; this change consumes it as corroboration.
- No layer-depth cap raise (community stacks to 19; our hard cap is 4 via `clamp_layer_budget`) — see
  Open Questions; possibly a separate change.
- Do not modify the improve-musicality change; only reference it where the two interact.

## Decisions

**1. One measurement script, two input modes, one report shape.**
`scripts/measure_fabric.py` exposes `stats_from_instructions(instrs, duration_s) -> FabricStats` and
`stats_from_xsq(path) -> FabricStats` (parse `<Effect>` elements from an `.xsq` — community shows AND
our finalized output). `FabricStats` carries: `effects_per_min`, `share_by_family` (motion /
punctuation / bed / feature / other), `share_by_type` (top-N), `duration_p50_by_type` (ms),
`blend_mode_share` (rows with `T_CHOICE_LayerMethod`), `transition_share` (rows with
`T_CHOICE_In/Out_Transition_Type`), `value_curve_kinds` (brightness vs motion params),
`layer_depth_hist`, `per_prop_expansion` (float | None), and `per_section` (a list of `SectionStats`
= effects/min + motion share + treatment). One report shape means community files and our shows
produce directly comparable tables. *Rationale:* the original comparison was a one-off; making it a
script makes it reproducible and CI-runnable forever, and lets `qa/musicality.py` import
`FabricStats.per_section` rather than re-deriving it.

**2. Inputs — the honest number and the hermetic canary.**
Our side: (a) the `instructions` cache of any real run (`<cache_root>/<song_key>/instructions` — a
JSON list of `EffectInstruction` dumps, persisted at run.py:432–433 and refreshed post-refine at
run.py:474–475) is the honest number; (b) the golden fixture is the hermetic canary that keeps the
measurement runnable in CI forever. Community side: the original 17 `.xsq` live in the user's xLights
show folder, not the repo; the `.xsq` mode re-derives their stats on demand, and the §2.1 aggregates
are **frozen into the script as constants** so the comparison still runs without the corpus.

**3. Prop-row-equivalent normalization is the critical fix to the original comparison.**
Community sequences target individual prop rows; ours target ~15 SEM_ groups, where one group-level
effect animates every member prop. Define `per_prop_expansion` = mean member-count of the groups we
actually target (derivable from `rgbeffects.xml` modelGroups — parsing already exists in
`xlights_core/knowledge/layout_semantics.py`). Report both raw effects/min and prop-row-equivalent
effects/min (`raw × expansion` for group-targeted rows). *Rationale:* the tuning.py comment made this
argument qualitatively; the script makes it a number, so we compare like with like.

**4. Every stat is also per-section, energy-bucketed.**
A single whole-show number hides exactly the contrast improve-musicality is trying to create.
`FabricStats.per_section` reports each stat with the section's intensity and (post-Phase 2) its
`treatment`, so quiet sections are analyzed separately from peaks.

**5. Targets — what "closed" means (energetic sections only: intensity ≥ 0.5, post-Phase 2
treatments `full`/`feature`).**
1. **Motion share ≥ 0.45** of instructions in energetic sections (today's advisory floor is 0.30;
   the fixture measures 0.24). Quiet/`rest`/`gesture` sections are exempt — deliberate stillness is a
   feature, not a regression.
2. **On + Twinkle combined ≤ 0.30** in energetic sections (they are ~62% of the golden fixture
   today). This targets the inversion directly rather than the total.
3. **Prop-row-equivalent density within ~2× of community typical** in peak sections — i.e. raw
   group-row density ≈ 600–900/min at peak once expansion is accounted for, vs `cell_budget`'s
   current 600/min ceiling.
4. **Pixel-level motion corroborates:** I8's Tier 0 frame-delta metric (per-group motion from the
   `.fseq`) must rise alongside instruction-level motion share. Instruction counts are a proxy;
   photons are the product. If instruction share rises but rendered motion doesn't (cells too dim,
   occluded, or per-model-confined), the tuning is wrong even though the proxy improved.

**6. Tune one lever at a time, rebalance-first, golden-regen per step.**
1. **Rebalance before adding:** reduce punctuation first — lower `SPARKLE_TOP_N` (12 → ~8) and let
   `carrier_covers` suppress more of the On accent layer (audit why 40 `On` rows survive in a fixture
   whose both sections have carriers — the per-type-per-source breakdown answers this by tagging
   which realization layer emitted each instruction, see Decision 8).
2. **Raise the weave's voice count:** `MAX_WOVEN_RECIPES` 3 → 4 and add a second texture to
   `fallback_weave` when the section's vocabulary offers one.
3. **Raise the budget:** `BUDGET_SCALE` 480 → ~700 (peak ≈ 820 cells/min) only after 1–2, and only
   if the I8 motion metric and a live watch agree the added cells read as fabric, not noise.
4. **Raise the advisory floor:** `MOTION_SHARE_MIN` 0.30 → 0.40–0.45 (and consider scaling with
   intensity) so the Judge defends the new fabric — but only once the generated shows clear it,
   otherwise it just spams the Judge.

**7. Interaction with improve-musicality Phase 2 (treatments).**
Phase 2 introduces `treatment ∈ {full, feature, pulse, gesture, rest}` and makes `realize_section`
*withhold* layers — deliberate sparseness. Consequences: (a) **per-treatment density targets, not one
number** — the report groups by treatment; the gap is evaluated only on `full`/`feature` sections; a
show-level effects/min that *drops* after Phase 2 is expected and correct. (b) **Ordering** — run the
baseline measurement *before* Phase 2 lands (so the current gap is quantified against current
semantics), but do the *tuning* after or alongside Phase 2, otherwise dials get tuned for a
realization model that's about to change (the roadmap's sequencing table puts I7 in the "continuous
hardening" slot after F-A phases). (c) **Shared metric plumbing** — Phase 2's advisory
`dynamic-range`/`focus-budget` metrics (planned `qa/musicality.py`) and this item's motion/density
stats want the same per-section instruction aggregation, so build `FabricStats.per_section` for
`qa/musicality.py` to import.

**8. Attribution: a transient `source` tag, report-only.**
Tuning blind-spots come from not knowing whether an `On` row is a bed, an accent, or an LLM wash.
`EffectInstruction` carries no provenance. Add a transient `source` tag (`"weave" | "accents" | "bed"
| "triggers" | "flash" | "generator" | "vu" | "composite"`) — either an excluded-from-dump field on
`EffectInstruction` or a parallel counter returned by `realize_section` — surfaced only in the
measurement report. This keeps the cache/golden formats unchanged. *Decision:* keep it transient
(excluded from `model_dump`) or as a side-channel counter; if it must persist, the golden fixture
regenerates once.

## Risks / Trade-offs

- [Density increases read as visual noise (the "random, not intentional" failure) → worse shows with
  better numbers] → Target the *inversion* (shares) before totals; per-step live/I8 checks; the Judge
  + visual critic remain the taste gate.
- [Chasing per-prop community numbers on a group-row architecture → pointless 5× density, render-time
  blowups, layer-clamp churn (`clamp_layer_budget` drops overflow)] → The prop-row-equivalent
  normalization (Decision 3); the 2× band in target 3; watch `clamp_layer_budget`'s dropped-count log
  line.
- [Phase 2 treatments land mid-tuning and shift which sections even get fabric → dials tuned twice] →
  Baseline before Phase 2; tune after; per-treatment targets from day one.
- [Emitter/render cost scales with instruction count (each cell = one `addEffect` call) → slower runs,
  slower refine loops] → Measure wall-clock per 100 instructions during the tuning step; budget
  raises are the last lever, not the first.
- [Community corpus unavailable (show folder machine-local) → can't re-validate the 2026-06 numbers]
  → Frozen aggregates in the script keep the comparison runnable; parser validated opportunistically
  when the folder is reachable.
- [Provenance tag leaks into persisted schemas → cache invalidation / golden churn / I6 drift-guard
  trip] → Keep it transient (excluded from `model_dump`) or as a side-channel counter; decide
  explicitly before coding (Decision 8).

## Migration Plan

- The `source` attribution is transient by construction, so no cache or golden migration is required
  in the common path. If the decision lands on a persisted field instead, the golden fixture
  regenerates exactly once, in its own commit.
- Each deliberate dial change regenerates the golden snapshot exactly once (`XLO_REGEN_GOLDEN=1`), in
  its own commit, so `git log fixtures/golden_instructions.json` reads as the tuning history.
  Non-tuning commits leave it byte-identical.
- `MOTION_SHARE_MIN` is raised only after the generated shows clear the new floor, so the Judge is
  not spammed before the generator can satisfy it.

## Open Questions

1. **Community corpus custody:** should a redacted per-file stats JSON (not the `.xsq` themselves —
   licensed vendor content) be checked into `docs/` so the comparison is fully reproducible in-repo?
2. **Measure the `.fseq` instead?** Instruction counts are the author-side proxy; I8's Tier 0
   measures the rendered result. Should the canary bounds eventually move to pixel metrics entirely
   and let instruction stats be diagnostic only? (Leaning yes, post-I8.)
3. **Layer depth:** community stacks to 19 layers; our hard cap is 4 (`clamp_layer_budget`, catalog
   rule #10). Is raising the cap on the hero/focal group (only) in scope here, or a separate change?
   The composite stacks already push against it.
4. **Where do the frozen targets live** — tuning.py comments, the analysis doc, or a small
   `fabric_targets.py` the canary test imports? (Recommend: doc for prose + the canary's literals as
   the single enforced copy.)
5. **Density vs song genre:** the two generated shows are both high-energy Christmas pop. Should
   targets be conditioned on the brief's overall energy (a ballad show legitimately measuring
   "sparse")? Per-section intensity bucketing may already cover this.

## Notes

**Dependencies / sequencing (roadmap I7 meta):** Complexity M, analysis-first. Depends on nothing
hard; pairs naturally with F-A improve-musicality Phase 2 (treatments redefine what "dense" means per
section) and benefits from I8 Tier 0 (pixel-level motion metric as ground truth). Unblocks show
quality (the "fabric" dimension) and informs the MOTION_SHARE advisory thresholds in QA. Sequencing
row 9 in `docs/roadmap-2026-07.md`, "continuous hardening" slot after the F-A phases.

**References:** roadmap `docs/roadmap-2026-07.md` §I7; the source analysis
`docs/effects-layering-analysis.md` (2026-06-11, its §6 recommendations are the shipped-changes
checklist); archived changes `2026-06-11-add-cell-fabric` (design + the ≥3× density target),
`2026-06-13-add-counterphase-chases`, `2026-06-14-unblock-color-wash`, `2026-06-11-add-effect-durations`,
`2026-06-12-add-directional-sweeps`, `2026-06-12-add-settings-hygiene`;
`changes/improve-musicality/proposal.md` (Phase 2 treatments — the density-semantics change);
related items I8 (pixel-level motion ground truth), I3 (consolidates the constants this item tunes).

**Live verification (non-CI):** one attended run per major dial change, watched against the review
bundles (`visual_review/iterN`), because "denser" can read as "noisier" — the failure mode no
instruction-count test can see. I8's motion heatmap makes this cheaper.
