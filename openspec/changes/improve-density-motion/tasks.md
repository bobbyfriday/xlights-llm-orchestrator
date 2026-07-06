## 1. Measurement tool

- [ ] 1.1 Add `scripts/measure_fabric.py` with `FabricStats` and `SectionStats` dataclasses per the
  design's field list (`effects_per_min`, `share_by_family` = motion/punctuation/bed/feature/other,
  `share_by_type` top-N, `duration_p50_by_type` ms, `blend_mode_share`, `transition_share`,
  `value_curve_kinds`, `layer_depth_hist`, `per_prop_expansion`, `per_section`).
- [ ] 1.2 Implement `stats_from_instructions(instrs: list[dict], duration_s: float) -> FabricStats`
  over an `EffectInstruction`-dump list (the `instructions` cache or the golden fixture).
- [ ] 1.3 Implement `stats_from_xsq(path: Path) -> FabricStats` parsing `<Effect>` elements
  (ElementTree) so community shows AND our finalized output measure identically.
- [ ] 1.4 Freeze the §2.1 community aggregates into the script as constants so the comparison runs
  without the corpus.
- [ ] 1.5 Compute `per_prop_expansion` from `rgbeffects.xml` modelGroups (reuse the parsing in
  `xlights_core/knowledge/layout_semantics.py`) and add the prop-row-equivalent effects/min column
  (`raw × expansion` for group-targeted rows).
- [ ] 1.6 Report every stat per section, bucketed by intensity (and, post-Phase 2, `treatment`), via
  `FabricStats.per_section`; keep the aggregation importable by `qa/musicality.py`.
- [ ] 1.7 Unit tests for both parsers: `stats_from_instructions` against hand-built instruction lists
  (known shares/durations); `stats_from_xsq` against a ≤20-effect synthetic `.xsq` written by the
  test (ElementTree — no xLights needed).

## 2. Attribution (source tag)

- [ ] 2.1 Add a transient per-layer `source` tag (`"weave" | "accents" | "bed" | "triggers" |
  "flash" | "generator" | "vu" | "composite"`) — either an excluded-from-`model_dump` field on
  `EffectInstruction` or a parallel counter returned by `realize_section` — surfaced only in the
  measurement report. Confirm the cache/golden formats stay byte-identical (I6 drift-guard does not
  trip); if the decision requires persistence, regenerate the golden once.
- [ ] 2.2 Surface a per-type-per-source breakdown in the report so tuning can see whether an `On` row
  is a bed, an accent, or an LLM wash.

## 3. Baseline measurement + targets doc

- [ ] 3.1 Run the tool on (a) the golden fixture, (b) ≥1 full real run's `instructions` cache (Candy
  Cane Lane / Mad Russian Christmas re-run on current code), and — if the show folder is at hand —
  (c) 2–3 community `.xsq` to validate the parser against the 2026-06-11 numbers.
- [ ] 3.2 Commit the report as `docs/effects-layering-analysis-2026-07.md` (the successor snapshot),
  with the prop-row-equivalent normalization and per-section (intensity-bucketed) breakdown.
- [ ] 3.3 Decide and record explicit targets in that doc: motion share ≥ 0.45, On+Twinkle ≤ 0.30, and
  prop-row-equivalent density within ~2× of community typical (≈ 600–900/min at peak) — energetic
  sections only, quiet/`rest`/`gesture` exempt — replacing "community does 58%" as the goalpost.
- [ ] 3.4 Get the target numbers into `pipeline/tuning.py` comments so the dials cite their evidence,
  matching house style ("Revision-log analysis (42 runs): …").

## 4. Tune the levers (rebalance-first, one lever per commit)

- [ ] 4.1 Rebalance punctuation down: lower `SPARKLE_TOP_N` (12 → ~8) and let `carrier_covers`
  suppress more of the On accent layer; golden regen (`XLO_REGEN_GOLDEN=1`) + a re-measurement delta
  in the commit message.
- [ ] 4.2 Raise the weave's voice count: `MAX_WOVEN_RECIPES` 3 → 4 and add a second texture to
  `fallback_weave` when the section's vocabulary offers one; golden regen + delta.
- [ ] 4.3 Raise the budget: `BUDGET_SCALE` 480 → ~700 (peak ≈ 820 cells/min) only after 4.1–4.2, and
  only if the I8-Tier-0 motion metric and a live watch agree the added cells read as fabric; golden
  regen + delta + I8/live spot-check.
- [ ] 4.4 Measure wall-clock per 100 instructions during the budget raise so emitter/render cost
  regressions surface.

## 5. Guard + advisory floor

- [ ] 5.1 Add hermetic `tests/test_fabric_stats.py` asserting loose bounds on the golden fixture's
  energetic section (e.g. motion share ≥ 0.35, On+Twinkle ≤ 0.45) so a future change can't silently
  re-invert the fabric; the canary exempts quiet/`rest`/`gesture` sections (Phase 2 sparseness is not
  a regression).
- [ ] 5.2 Raise `MOTION_SHARE_MIN` 0.30 → 0.40–0.45 (consider scaling with intensity) and update its
  comment to cite the re-measurement — only once the generated shows clear the new floor.
- [ ] 5.3 Extend the motion-share advisory tests (rules QA) so the finding fires below and stays
  silent above the new floor, at the `MOTION_SHARE_INTENSITY` gate.

## 6. Verify

- [ ] 6.1 Golden discipline: every deliberate dial change regenerates the golden snapshot exactly
  once, in its own commit; non-tuning commits leave `fixtures/golden_instructions.json`
  byte-identical.
- [ ] 6.2 One attended live run per major dial change, watched against the review bundles
  (`visual_review/iterN`), to confirm "denser" reads as intentional fabric, not noise.
- [ ] 6.3 Full suite green; `openspec validate improve-density-motion --strict` clean.
