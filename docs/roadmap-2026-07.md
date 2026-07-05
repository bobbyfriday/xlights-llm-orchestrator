# Roadmap — July 2026: improvements & the road ahead

A fresh assessment of the orchestrator after ~63 OpenSpec changes. Successor to
[`roadmap-2026-06.md`](roadmap-2026-06.md) (much of which has since shipped) and companion to
[`craft-roadmap.md`](craft-roadmap.md) and the active
[`improve-musicality`](../openspec/changes/improve-musicality/proposal.md) proposal. This document
does two things: catalogs the concrete **functionality improvements** still worth making, and lays
out a **feature roadmap** in dependency-ordered horizons.

> **Per-item design docs:** every item below (I1–I8, F-A–F-J) has a thorough standalone design
> document under [`docs/roadmap-2026-07/`](roadmap-2026-07/index.html) — problem, current-state
> code walkthrough, proposed design, implementation plan, testing strategy, risks, and acceptance
> criteria — written before the execution phase.

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

Ordered by leverage. I1–I3 and I8 unblock roadmap features (and cut run cost); I4–I7 harden what
exists.

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

### I8. Cheaper visual analysis: fseq metrics + a tiered critique ⭐

Today each refine iteration sends up to 6 sections × (still + 10s MP4 clip) to the **planner-tier**
visual critic with two full guides in its prompt (`pipeline/visual.py`, `agents/visual_critic.py`)
— roughly 30–40k multimodal tokens per iteration on the most expensive model, for findings that
are **advisory only**. But the critic's four aspects (`coverage`, `color`, `motion`, `energy`) are
largely computable from data we already have: the `.fseq` is the exact per-node RGB of every frame,
and the layout gives node→group mapping (`make_lit_sampler` already samples it pointwise).

**Tier 0 — deterministic fseq metrics (every iteration, ~free, no LLM).** Per-section, per-group
time series from the channel data: brightness/lit-fraction (coverage; "dark during the peak"),
frame-to-frame delta (motion; "static during a high-energy moment", with exact group attribution),
brightness-derivative × beat-grid cross-correlation (music-sync as a score), dominant hues vs the
planned palette with hue-distance checks (catches the "gold + amber + warm white reads as one
color" failure), and section-signature similarity — which is the pixel-level version of the
`repetition-rhyme` / `dynamic-range` metrics the improve-musicality proposal defines on
instructions. Unlike the LLM critique, these can enter the **objective** gate.

**Tier 1 — contact sheets on a cheap model (flagged/changed sections only).** Tile 6–9
beat-aligned frames per section into one montage (~1–2k tokens vs ~2.5k+ per clip), downscaled to
~512px, plus an optional per-pixel-std motion heatmap; drop the guides from the critic prompt;
route to the worker/cheap tier. Critique only sections whose instructions changed since the last
iteration (hash them like the stage caches) — `regen` is section-scoped but the critique currently
re-judges all sections every iteration.

**Tier 2 — today's still+clip on the pro model, rarely.** Only when Tiers 0–1 disagree or a
section keeps churning; the gestalt "random vs intentional" judgment is the one thing that needs a
strong multimodal model, and it doesn't need asking six times per iteration.

Caveat: fseq metrics inherit offline-render fidelity (the reason `RealRender` exists) — fine for
coverage/motion/energy, but keep one real-render check near the end of a run as the ground-truth
gate. Net effect: >10× cheaper visual analysis while *adding* objective metrics that don't exist
today. **Complexity: M (Tier 0+1); Tier 2 is the current code, demoted.**

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

#### Prop-grouping assessment (2026-07)

The SEM_ grouping **architecture is the right contract** — choreographing against roles and
ensembles instead of raw models matches community sequencing practice and the hard xLights
constraint that groups load only at startup (so a static, pre-built vocabulary is the only
practical design; dynamic per-section groups are impossible, and targeting individual models would
lose group-canvas spatial rendering and explode effect counts). Several specifics beat the obvious
alternatives:

- **Subtractive ensembles** (`SEM_ALL_LESS_FOCAL*`, `layout_semantics.py`) — the bed goes on
  "everything except the feature," killing bed-ghosting with zero blending arithmetic.
- **Empirical targetability probing** (`pipeline/groups.py`) — a throwaway effect per group on a
  disposable sequence, cached per layout fingerprint; targetability genuinely isn't derivable from
  the XML, so probing beats parsing.
- **One source of truth for names** (`pipeline/semantic_groups.py`) — a typo is an import error,
  not a silently dark prop — and name-derived canonical render order (`canonical_order`).
- Flat groups, no nesting — sidesteps xLights' unpredictable group-of-group rendering.

But the implementation covers only **half of `xlights-layout-semantics-spec.md`**:

1. **The classifier is prose, not code.** Spec §3 (DisplayAs mapping → pixel-count disambiguation →
   name heuristics → group hints → LLM fallback) has no implementation; `layout_semantics.py`
   starts from already-classified `Prop` objects. This layout was classified once, by hand — the
   root of the single-layout coupling. (No code writes the SEM_ modelGroups either; group creation
   is agent/manual today.)
2. **The manifest is designed but never emitted or consumed — the biggest miss.** Spec §6's
   `layout_semantics.json` (node counts, normalized positions, capability classes, sweep order,
   mirror pairs, focal flags) exists nowhere. The Director receives a flat list of group names
   (`agents/director.py::render_input`), so the LLM plans knowing nothing of scale, geometry, or
   symmetry; QA fakes capability gating with name prefixes (`qa/rules.py::_LINEAR_PREFIXES`).
3. **Group render modes aren't code-managed.** Spec §5.7 requires "Per Preview" on ensembles and
   "Horizontal Per Model" on `_LTR` groups (or chases don't traverse in order), but only `GridSize`
   is patched (`patch_sem_gridsize`) — a wrong mode silently breaks every sweep on that group.
4. **The choreography vocabulary is hardcoded to this layout's prop mix.** `METRIC_RING`, backbeat
   and bed preferences are constants; they degrade gracefully via `if g in avail` filters, but a
   layout with a different prop mix gets a weaker beat anchor by accident, not by decision.
5. **Validation is manual.** The spec's role-color test and sweep test (§7) are described but not
   implemented, even though the offline preview renderer and visual critic could run them —
   misclassification poisons every downstream decision.

A minor accepted tension: membership overlap (a prop sits in ALL + band + side + role + focal
simultaneously) is resolved implicitly by render order and the occlusion guards rather than by
explicit partitions. It works; it's just render-order-load-bearing.

**F-E. `xlo init-layout` onboarding** (L) — the fix for all of the above is finishing the spec as
one guided CLI command, which is what turns a personal tool into a shareable one:

- Implement the §3 classifier + §4 spatial derivation as real code (LLM fallback only for the
  unresolved tail), with a review step for low-confidence classifications.
- Write the SEM_ groups, per-group **layout modes**, and grid size into `rgbeffects.xml`
  idempotently (extend the existing `patch_sem_gridsize`/`patch_view` pattern).
- **Emit the §6 manifest**, and consume it: a compact traits/props block in the Director's input
  ("SEM_ARCHES: 6 arches, ~50 nodes each, ground band, mirror-symmetric" — ~1 KB of prompt for
  much better-grounded designs), capability-class gating in QA instead of name prefixes, and
  mirror-pair/sweep-order data for true call-and-response and center-out waves.
- Derive the choreography orderings (metric ring, backbeat/bed preferences) from the manifest —
  rank rhythm families by count, spread, and node budget — keeping today's constants as fallback.
- Auto-run the §7 role-color and sweep validation via the offline preview renderer + visual
  critic after any layout (re)setup.

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
| 2 | I8 Tiers 0–1 (fseq metrics, contact-sheet critique) | Slashes the cost of every refine iteration before the refine-heavy work below; its metrics feed F-A's QA |
| 3 | F-A Phase 1 (repetition identity) + I5 (degradation logging) | Biggest show-quality lever; logging pays off during its live-verify |
| 4 | I3 (refine-loop decomposition + constants) | Required ground for F-A Phase 2 |
| 5 | F-A Phases 2–3 | Treatments, transitions, color script |
| 6 | F-B + F-C (asset path, matrix Text) | Highest-payoff contained feature; closes the craft roadmap's biggest gap |
| 7 | F-E (`xlo init-layout`) | The product unlock — do it once the show quality is worth sharing |
| 8 | F-G/F-H (dashboard, A/B) | Harvest the telemetry from step 1 |
| 9 | I2, I6, I7 | Continuous hardening, slotted between features |

The honest one-liner this month: the codebase is healthy and the June infrastructure debt is mostly
paid — the leverage now is **musicality** (the improve-musicality proposal), **observability**
(token/cost telemetry, degradation logging), and then **generalization** (layout onboarding) once
the shows are good enough to share.
