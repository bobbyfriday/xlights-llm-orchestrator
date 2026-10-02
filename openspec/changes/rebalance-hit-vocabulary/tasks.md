## 1. Shared Shockwave settings

- [x] 1.1 Move `SHOCKWAVE_SETTINGS` (dict + its provenance comment) from `pipeline/triggers.py` (~line 35) to `pipeline/effect_meta.py`; in triggers.py replace the definition with `from .effect_meta import SHOCKWAVE_SETTINGS` (name unchanged — triggers' own callers must not churn). Run `uv run pytest tests/ -k trigger` to confirm no behavior change.

## 2. Role-differentiated accents (beats.py)

- [x] 2.1 Add `SHOCKWAVE_ACCENT_MS = 600` to `pipeline/tuning.py` with a comment citing the community median (600 ms, 2026-07-07 corpus measurement).
- [x] 2.2 In `place_beat_accents` (`pipeline/beats.py` ~line 355): extend the `_mk` closure to accept an effect override (effect_type, look_id, extra settings); switch the SPARKLE block (~line 436) and BACKBEAT block (~line 420) to Shockwave + `SHOCKWAVE_SETTINGS` + `SHOCKWAVE_ACCENT_MS` per design.md D2. Backbone/hero/bass unchanged. Keep legato soft-edge behavior applying to the overridden effect.
- [x] 2.3 Unit tests (find existing accent tests via `grep -rl place_beat_accents tests/`): (a) sparkle instructions are Shockwave with the radiating settings; (b) backbone stays On (or the Director's explicit accent_effect); (c) backbeat Shockwave duration ≤ next beat; (d) legato section still soft-edges.

## 3. Strobe demotion + Shimmer cap (qa/rules.py)

- [x] 3.1 Add `SHIMMER_MAX_PER_SECTION = 2` to `pipeline/tuning.py`.
- [x] 3.2 Implement `demote_offpeak_hits(instructions, *, is_peak) -> int` in `qa/rules.py` beside `clamp_hard_caps`, per design.md D3 (off-peak Strobe → Shockwave with remapped look + `SHOCKWAVE_SETTINGS`; Shimmer beyond cap dropped, earliest kept).
- [x] 3.3 Call it from `realize_section` in `pipeline/generate.py` next to the existing `clamp_hard_caps(kept, ...)` call (`si in _peaks` is already in scope there).
- [x] 3.4 Unit tests: off-peak Strobe substituted (same span/target); peak Strobe untouched; 4 Shimmers → 2 earliest survive; return count correct.

## 4. Flat-flash QA advisory

- [x] 4.1 Add `FLAT_FLASH_SHARE_MAX = 0.30` to `pipeline/tuning.py` (comment: community ≈ 7.5%, ours measured 42% — loose bound to avoid Judge spam).
- [x] 4.2 In `qa/rules.py::evaluate`, add the per-section flat-flash advisory block mirroring the motion-share advisory (~lines 135–157) exactly: energetic-only, `_QUIET_TREATMENTS` exempt, `severity="warn"`, `objective=False`; `FLAT_FLASH = frozenset({"On", "Twinkle", "Strobe", "Shimmer", "Lightning"})`.
- [x] 4.3 Unit tests in the existing qa rules test file: 50%-On energetic section warns; `rest` treatment exempt; score unaffected by the advisory.
- [x] 4.4 Run `evaluate` over a real cache (`data/analyses/orchestrator/e1a6805bc78a0643/instructions.json` — load, evaluate with no plan sections if needed) to eyeball advisory volume. Also check design.md risk: if accent-sourced Shockwaves now trip catalog rule #4 (feature-overlap) in that cache, exclude `source == "accents"` instructions from the FEATURES sweep in `evaluate` and add a test for that exclusion.

## 5. Prompt grounding + finalize

- [x] 5.1 Add the one-sentence corpus grounding to `agents/prompts/director.md` and `agents/prompts/generator.md` per design.md D5 (Shockwave-preferred hits; Strobe climax-only; include the 3-in-27,000 number).
- [x] 5.2 Full suite, then golden regen: `XLO_REGEN_GOLDEN=1 uv run pytest tests/test_golden_pipeline.py`. Expected diff: sparkle/backbeat accent rows change type/duration; any off-peak Strobe rows become Shockwave. Investigate anything else.
- [x] 5.3 PR to `main` (branch `feat/rebalance-hit-vocabulary`); note in the description that flat-flash share is expected to drop from ~42% toward ≤30% and how to re-measure (`scripts/measure_fabric.py <cache>/instructions.json`).
