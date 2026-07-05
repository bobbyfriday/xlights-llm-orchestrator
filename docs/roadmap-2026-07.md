# Roadmap — July 2026: improvements & the road ahead

A fresh assessment of the orchestrator after ~63 OpenSpec changes. Successor to
[`roadmap-2026-06.md`](roadmap-2026-06.md) (much of which has since shipped) and companion to
[`craft-roadmap.md`](craft-roadmap.md) and the active
[`improve-musicality`](../openspec/changes/improve-musicality/proposal.md) proposal. This document
does two things: catalogs the concrete **functionality improvements** still worth making, and lays
out a **feature roadmap** in dependency-ordered horizons.

## Where the project stands

~9,400 lines of source across the 3 workspace packages (`xlights-core` ~3,270, `xlights-orchestrator`
~5,850, `xlights-mcp` ~240), 65 test files, 63 archived changes, and still **zero TODO/FIXME/HACK
markers** — the debt is architectural, not flagged. The judgment-vs-realization split remains clean
and the deterministic layers are well tested (including a golden pipeline snapshot).

### June roadmap scorecard

Much of `roadmap-2026-06.md` landed within a month; what remains is carried forward below.

| Item | Status |
| --- | --- |
| R1 CI + ruff + mypy | ✅ Shipped (`.github/workflows/ci.yml`) — but mypy is **advisory** (`continue-on-error`), no `py.typed` |
| R2 Decompose `run.py` | ✅ Largely done — `generate.py`, `cache.py`, `finalize.py` extracted; 607 → 486 lines. `_refine_loop` still monolithic |
| R3/R4 Centralize constants | 🟡 Partial — `semantic_groups.py` and `tuning.py` exist; effect-metadata tables and refine thresholds still scattered |
| R5 Log swallowed exceptions | ❌ Open — 45 `except Exception` blocks across 20 files, most silent |
| F5 Golden tests | ✅ Shipped (`test_golden_pipeline.py`) |
| F1 Matrix Text / F2 Faces | ❌ Open — still blocked on an asset-bound placement path |
| F3 Layout onboarding | ❌ Open — SEM_ group setup is still a manual module invocation |
| F6 Cost dashboard / F7 A/B harness | ❌ Open — and blocked on missing token telemetry (see I2) |
| F8 Live progress UI | ❌ Open |

Also delivered since June: targeted section regen (`xlo regen`), the song-end envelope fade, the
refine-loop skip-high-objective gate, the VU meter layer, composite stacks, and the render-hygiene
fixes. Three of those changes are implemented but not yet archived in `openspec/changes/` —
closing them out (live-verify + archive) is cheap hygiene.

---

## Part 1 — Functionality improvements

Ordered by leverage. I1–I3 unblock roadmap features; I4–I7 harden what exists.

### I1. Token & cost telemetry ⭐ (unblocks F6 and F7)

There is **no token accounting anywhere**, despite an active cost-reduction effort (guide-extract
trimming, tiered model routing, the skip-objective gate — all justified by *estimated* cost).
PydanticAI already returns `RunUsage` on every agent run; the revision log already records per-role
`model_snapshot` per iteration.

- Capture `result.usage()` in the agent wrappers and thread it into `revision_log.py` (JSONL) —
  per-role, per-iteration input/output token counts.
- Add a per-run cost summary line (tokens × published per-model rates, table in `models/config.yaml`).
- This directly unblocks the **cost & quality dashboard** (F6) and makes the **provider A/B
  harness** (F7) meaningful — you can't A/B Gemini vs Claude on cost/quality without cost numbers.

Small, contained, and it turns every future run into evaluation data. **Complexity: S.**

### I2. Retry/backoff for transient failures

The only explicit retry in the codebase is `lyricsgenius(retries=1)`. LLM calls rely on PydanticAI
defaults; xLights REST calls have a typed error taxonomy (`exceptions.py`) and a write lock but no
backoff. Today a transient 429/529 or a momentary xLights hiccup fails an analyst (dropped from the
panel) or a whole stage.

- A thin retry decorator (or `tenacity`) on agent invocation: 2–3 attempts, exponential backoff,
  retry only on transient classes (rate-limit, overload, timeout) — never on schema/validation errors.
- Same for `XLightsClient` on connection errors and 5xx, preserving the mutation lock.
- Panel analysts should retry once before being dropped — a dropped analyst silently degrades brief
  quality, and nothing in the output says so. Log the drop at warning level.

**Complexity: S–M.**

### I3. Decompose `_refine_loop` and finish the constants consolidation

`_refine_loop` (~180 lines in `pipeline/run.py`) is now the most complex, highest-risk function in
the codebase: it carries the objective-regression revert, stall stop, plateau detector,
anti-oscillation ledger, design escalation, and skip-high-objective gate, plus nested closures
(`_regen`, `_redesign`, `_report`, `_record`). The `improve-musicality` proposal will add advisory
metrics that flow through this exact code.

- Extract a `pipeline/refine_loop.py` with the guards as named, individually-testable functions
  (the golden test + `test_refine` make this safe).
- Finish R3/R4: move the remaining refine thresholds (`REGRESS_MARGIN`, `STALL_LIMIT`,
  `REFINE_SKIP_OBJECTIVE`) and the effect-metadata tables (`SPEED_KEYS`, `DURATION_*`,
  `DIRECTION_KNOBS`) into `pipeline/tuning.py` / one data-driven table, documented like the
  markdown guides.

Do this **before** improve-musicality Phase 2, which touches the same seams. **Complexity: M.**

### I4. Promote mypy to a hard gate; ship `py.typed`

The code is fully annotated but CI runs mypy with `continue-on-error: true` and a ~30-finding
backlog. Advisory type-checking decays — findings accumulate until the signal is noise.

- Burn down the backlog (mostly mechanical), flip `continue-on-error` off.
- Add `py.typed` markers to all three packages so downstream typing works.
- Optional: coverage reporting in CI (even without a threshold, the trend is visible in PRs).

**Complexity: S, mechanical.**

### I5. Diagnosable best-effort failures

45 `except Exception` blocks across 20 files (9 in `run.py`, 6 in `visual.py`) — appropriate
best-effort posture for an orchestrator, but most swallow the exception silently. When a stage
degrades (no visual critique, missing lyrics, skipped triggers), the run log doesn't say why.

- One convention: every best-effort block logs `log.debug("…: %s", exc)` (warning level when a
  whole capability is lost, e.g. a dropped analyst or failed render).
- A per-run "degradations" summary at the end: what was skipped and why. Cheap to add once the
  logging exists, and it turns "the show looks off" into "stems failed, brief had no instruments."

**Complexity: S.**

### I6. Close the test gaps at the edges

The deterministic core is well covered; the edges are not:

- `cli.py` argument wiring (a bad flag rename ships silently today), `models/registry.py` routing,
  `brief_editor.py` request handling, and the MCP server (`server.py` — its tools can be exercised
  against a fake client the same way `test_client` does).
- A schema-drift guard for agent outputs: validate a stored known-good JSON payload for each agent
  `output_type` so a pydantic model change that would break cached briefs fails a test, not a run.

**Complexity: S–M, incremental.**

### I7. Close the remaining density/motion gap

`effects-layering-analysis.md` (2026-06-11) found our fabric inverted vs community practice (16%
motion vs 58%; ~270 effects/min vs ~1,300) — the cell-fabric and counterphase changes only
partially closed this. Re-run the corpus comparison on a current generated show to quantify the
remaining gap, then tune cell density / motion-vs-punctuation ratios in `weave.py` against it.
Pairs naturally with improve-musicality Phase 2 (treatments change what "dense" should mean per
section). **Complexity: M, analysis-first.**

---

## Part 2 — Feature roadmap

### Horizon 1 — Musicality (the current design frontier)

**F-A. Land `improve-musicality`** — already proposed and designed
([proposal](../openspec/changes/improve-musicality/proposal.md)); the biggest show-quality lever:
repetition identity (Phase 1), section treatments with energy-keyed coverage QA (Phase 2),
transitions + color script + phrase dynamics (Phase 3). Each phase lands independently. Sequence
I3 (refine-loop decomposition) before Phase 2. Also archive the three implemented-but-open changes
(`add-refine-skip-high-objective`, `add-song-end-envelope-fade`, `add-targeted-section-regen`).

### Horizon 2 — Finish the craft roadmap (the vocal/narrative dimension)

Both remaining `craft-roadmap.md` items are blocked on the same enabler:

**F-B. Asset-bound placement path** (enabler, M) — Faces/Text/Pictures/Video/Shaders are excluded
from the mined preset catalog (`ASSET_BOUND_TYPES`); they need a placement route outside
`PresetLibrary`/`assemble()`. Build it once, unblock both features.

**F-C. Matrix narrative Text** (M) — section labels, song title, lyric phrases on the matrix.
Stock effect, no assets, lyric timing track already exists. Highest visible payoff per unit work.

**F-D. Lyric-driven Faces** (L) — singing faces on character props. Word/line timing exists
(`lyrics_align.py`); phoneme timing needs a new extractor. Vocal songs only.

### Horizon 3 — Generalize beyond one layout (the product unlock)

**F-E. `xlo init-layout` onboarding** (L) — the system is coupled to one `rgbeffects.xml` and
hand-built SEM_ groups; `docs/usage.md` still documents SEM setup as a manual module invocation.
`layout_semantics.py` already classifies props and builds the groups — wrap it in a guided CLI
command with a review step for low-confidence classifications. This is what turns a personal tool
into a shareable one, and every craft feature multiplies in value across layouts it can run on.

**F-F. Submodel targeting** (L, conditional) — unblocks with F-E once layouts that *have*
submodels arrive (tree zones/rings, drum-kit mapping, vertical runs). Deferred, not dead.

### Horizon 4 — Operability & evaluation

**F-G. Cost & quality dashboard** (S once I1 lands) — analyzer over the revision-log JSONL:
cost per show, score-improvement per iteration, which sections churn, cost-per-point-gained.

**F-H. Provider A/B eval harness** (M, needs I1) — run a fixture song through Anthropic and
Gemini per-role routings; diff QA scores, iteration counts, and cost. Formalizes the manual A/B
already hinted at in `models/config.yaml` comments.

**F-I. Live progress streaming** (M) — extend the stdlib-browser pattern from `brief_editor.py`
to a live pipeline view (stage, section, QA scores as they land). Also replace the two blocking
`input()` checkpoints in attended mode with the same browser surface, so attended runs don't hold
a terminal hostage.

**F-J. Headless / preview-only iteration mode** (M–L, exploratory) — the offline preview renderer
(`xlights_core.preview`: `.fseq` + layout → PNG/MP4) already exists for the visual critic. A mode
that iterates against offline renders without a live xLights would enable CI-run full-pipeline
evals, cloud execution, and much faster refine loops — worth a spike to find what truly requires
the live app (render fidelity is the open question).

---

## Recommended sequencing

| Order | Item | Why |
| --- | --- | --- |
| 1 | I1 (token/cost telemetry) + I4 (mypy gate) | Small, mechanical; every later run becomes eval data |
| 2 | F-A Phase 1 (repetition identity) + I5 (degradation logging) | Biggest show-quality lever; logging pays off during its live-verify |
| 3 | I3 (refine-loop decomposition + constants) | Required ground for F-A Phase 2 |
| 4 | F-A Phases 2–3 | Treatments, transitions, color script |
| 5 | F-B + F-C (asset path, matrix Text) | Highest-payoff contained feature; closes the craft roadmap's biggest gap |
| 6 | F-E (`xlo init-layout`) | The product unlock — do it once the show quality is worth sharing |
| 7 | F-G/F-H (dashboard, A/B) | Harvest the telemetry from step 1 |
| 8 | I2, I6, I7 | Continuous hardening, slotted between features |

The honest one-liner this month: the codebase is healthy and the June infrastructure debt is mostly
paid — the leverage now is **musicality** (the improve-musicality proposal), **observability**
(token/cost telemetry, degradation logging), and then **generalization** (layout onboarding) once
the shows are good enough to share.
