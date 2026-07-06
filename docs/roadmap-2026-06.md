# Roadmap — June 2026: state, refactoring & new features

> **Superseded by [`roadmap-2026-07.md`](roadmap-2026-07.md)**, which carries a scorecard of what
> shipped from this document and the current improvement/feature plan.

A forward-looking assessment of the orchestrator after the first ~56 OpenSpec changes.
Companion to [`craft-roadmap.md`](craft-roadmap.md) (which is now ~85% delivered).

## Where the project stands

A mature, disciplined codebase: ~8,500 lines of source across 3 uv-workspace packages,
~5,000 lines of tests (49 files at the repo root), 56 archived OpenSpec changes, zero
`TODO/FIXME/HACK` markers, comprehensive type hints, and a clean judgment-vs-realization
split (the LLM owns taste; code owns timing, placement, brightness, sparsity). The
architecture is sound — the opportunities below are about scaling the craft, generalizing
beyond a single layout, and hardening the dev infrastructure, not fixing rot.

`docs/craft-roadmap.md` is ~85% delivered: 7 of its 9 items shipped. Only two true features
remain (matrix Text, lyric-driven Faces), plus one deliberately deferred (submodel targeting,
because the current layout has no submodels).

---

## Part 1 — Refactoring (highest-leverage first)

### R1. Add the missing dev infrastructure ⭐ (biggest ROI, lowest risk)
There is no CI, no linter, no type-checker, no formatter — `pyproject.toml` configures only
pytest. For a codebase landing changes this fast via PR, this is the gap most likely to bite.
- GitHub Actions running `pytest` (the `-m "not live"` suite is already hermetic) on every PR.
- **ruff** (lint + format) and **mypy/pyright** — the code is already fully type-hinted, so the
  type-checker will mostly pass and lock in the discipline.
- Ship `py.typed` markers (currently absent) so downstream typing works.

Mechanical, non-behavioral, and it protects all 56 changes' worth of invariants.

### R2. Decompose `pipeline/run.py` (607 lines)
`run_pipeline` is a ~240-line god-function and the generate stage is ~80 lines inlined inside
it (run.py:462–540), mixing LLM calls, intensity math, brightness ramps, weave expansion, beat
accents, triggers, and key-moment synthesis. Extract:
- `pipeline/generate.py::generate_instructions(...)` — lift the whole per-section loop out.
- `pipeline/cache.py` — the read/compute/write cache dance repeats 4× with slight variations.
  Make one `cached_stage(key, stage, compute)` helper.
- `pipeline/finalize.py` — the offline `.xsq` patch sequence (media/render-order/timing).
- Promote the nested closures in `_refine_loop` (`_regen`, `_redesign`, `_report`) to
  module-level functions. Target: run.py → ~250 lines that read as a 6-stage skeleton.

### R3. Centralize scattered domain knowledge
Duplicated across `beats.py`, `weave.py`, `triggers.py`, `rules.py`:
- Semantic group names (`SEM_*`) referenced in 4+ files → one `semantic_groups.py` module.
- Intensity/escalation math (`effective_intensity`, `escalation_level`, coverage caps) appears
  in beats + weave + triggers → extract `intensity.py`.
- Effect metadata (`SPEED_KEYS`, `ENERGY_BAND`, `DURATION_*`, `DIRECTION_KNOBS`) hardcoded
  across modules → consolidate into one data-driven table (or JSON).

### R4. A tuning-constants surface
Thresholds like `MIN_SECTION_S`, `INSTR_MAX_SECTION_S`, `REGRESS_MARGIN`, `MEGA_TREE_NODES`,
`WASH_MIN/MAX_B` are good but buried as module constants. Gather the show-feel knobs into one
documented config (sibling to `models/config.yaml`) so the "voice" is tunable like the markdown
guides already are.

### R5. Lower-priority cleanups
- `beats.py`/`weave.py` are long flat function modules (45+ / 40+ functions). Optional grouping
  into small classes, but they're cohesive — don't over-engineer.
- The pervasive best-effort `except Exception` blocks are appropriate for an orchestrator but
  swallow context silently — add `log.debug(exc)` so failures are diagnosable.

---

## Part 2 — New features

### Horizon 1 — Finish the craft-roadmap (vocal dimension)
Both remaining items hit the same wall: Faces, Text, Pictures, Video, Shader are asset-bound
types deliberately excluded from the mined preset catalog (`constants.py::ASSET_BOUND_TYPES`).
They need a new placement path outside `PresetLibrary`/`assemble()`.
- **F1. Matrix narrative Text** (M) — section labels / song title / lyric phrases on the matrix.
  No assets, stock effect, lyric timing track already exists. Best next feature: high visible
  payoff, contained scope.
- **F2. Lyric-driven Faces** (L) — singing faces on character props from phoneme timing. Word/
  line timing exists (`lyrics_align.py`); phonemes need a new extractor. Vocal songs only.

### Horizon 2 — Generalize beyond one layout (the biggest product unlock)
The system is currently coupled to one user's `rgbeffects.xml` and hand-built SEM_ groups.
- **F3. Layout onboarding flow** — `layout_semantics.py` already classifies props and builds
  SEM_ groups; wrap it in a guided `xlo init-layout` command that auto-generates and patches the
  SEM_ groups for any layout, with a review step for low-confidence classifications.
- **F4. Submodel targeting** — unblocks once layouts with submodels exist (tree zones/rings for
  drum-kit mapping, vertical runs). Deferred infra, not dead.

### Horizon 3 — Product & operability
- **F5. Golden/regression tests for the deterministic layers** — snapshot the generated
  `instructions.json` for a fixture analysis so refactors R2–R4 can't silently change output.
  The safety net that makes the refactoring safe; pair it with R2.
- **F6. Cost & quality dashboard from the revision log** — the structured JSONL revision logs
  already carry per-role model snapshots and score deltas. A small analyzer turns that into
  "cost per show / score-improvement per iteration / which sections churn."
- **F7. Provider A/B eval harness** — formalize the manual Gemini-vs-Claude per-role A/B
  (already noted in `config.yaml` comments): run a fixture song through both, diff QA scores.
- **F8. Progress streaming / richer UI** — extend the stdlib browser brief-editor pattern
  (`brief_editor.py`) to live pipeline progress.

---

## Recommended sequencing

| Order | Item | Why |
| --- | --- | --- |
| 1 | R1 (CI + ruff + mypy) | Protects everything else; mechanical |
| 2 | F5 + R2 (golden tests, then split run.py) | Tests make the decomposition safe |
| 3 | R3 + R4 (centralize constants/intensity) | Cleaner ground for new features |
| 4 | F1 (matrix Text) | Highest-payoff contained feature |
| 5 | F3 (layout onboarding) | Turns a personal tool into a shareable one |
| 6 | F6/F7 (cost dashboard, A/B) | Optimize the spend already being logged |

The honest one-liner: infrastructure (CI/lint/types) is the real gap; the application code is in
good shape. R1 + F5 are the unglamorous wins that de-risk everything after.
