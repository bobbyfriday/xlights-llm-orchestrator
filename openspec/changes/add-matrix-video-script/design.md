## Context

The pipeline already computes a complete, time-coded account of the show's intended look and caches it
per song (`SectionPlan.look`/`palette`/`motion`/`transition`/`treatment`/`intensity` with real
`start_ms`/`end_ms`; the brief's narrative, identity, themes and `featured_lyric_moments`; the rhythm
analyst's `climax_ms`/`builds_ms`/`drops_ms`). Nothing consumes that material for the matrix's narrative
job beyond F-C's sparse Text. This change adds a Videographer agent that turns it into a video script
for an external video-generation agent, with the resulting footage destined for the matrix.

Three existing facts constrain the design hard:

1. **`build_agent(role, output_type=…)` + `run_agent(agent, prompt, role=…)`** (`models/registry.py`)
   are the only LLM seam, and routing is data-driven from `models/config.yaml`. A new role is a config
   row plus an agent module — no new plumbing.
2. **`estimate_cost()` returns `None` if ANY role with nonzero usage runs on a model with no price row**
   ("unknown ≠ zero", `registry.py`). A new role on an unpriced model would silently turn every
   `xlo report` cost cell for that run into `—`. The role must route to an already-priced model.
3. **The matrix's real resolution is not known to the codebase.** `matrix_text.py:218` reads
   `int(getattr(st, "matrix_height", 0) or _DEFAULT_MATRIX_H)` and nothing anywhere sets
   `st.matrix_height` (grepped across `packages/` and `tests/`), so the hardcoded 50 is always used and
   the probe promised at `matrix_text.py:216` was never built.

## Goals / Non-Goals

**Goals:**
- A validated, time-coded `VideoScript` artifact per song, derived from cached artifacts, that an
  external video agent can execute against without further interpretation.
- Make invented timings structurally impossible, not merely discouraged.
- State the matrix's real technical constraints in the script, or refuse to pretend.
- Work on shows already in the cache, with no regeneration and no xLights write path.
- Zero cost added to runs that do not ask for it.

**Non-Goals:**
- Ingesting the returned video or placing a `Video` effect on the matrix (the return trip — see
  Decision 7 for the seam this leaves).
- Generating video here. No media encoding, no model hosting, no new dependency.
- Replacing or competing with F-C matrix Text; the two will have to be reconciled when placement lands,
  not now.
- A standalone music video, or a shot list for filming the real display. Both were considered and
  explicitly rejected in favor of matrix content.

## Decisions

### D1 — A dedicated `xlo video-script` subcommand, not a `run` stage

The proposal floated "a `--video-script` flag on `xlo run` plus a standalone path". The design picks
**subcommand only**: `xlo video-script --song <path>`, reading the cached `MusicBrief` + `ShowPlan`.

Rationale: in phase 1 **nothing downstream consumes the script**. Threading a stage into `pipeline/run.py`
(and therefore past the refine loop, the splice logic, and `xlo regen`) buys nothing and touches the
highest-risk function in the codebase for no benefit. A subcommand also means every show already in
`data/analyses/orchestrator/` can produce a script immediately, which is the fastest way to find out
whether the output is any good.

*Alternative considered:* a `run --video-script` flag. Deferred to phase 2 — once the script actually
feeds placement, being in-pipeline earns its keep, and by then the stage ordering matters.

### D2 — Shots are bar-relative; code resolves them to milliseconds

The agent never emits a timestamp. For each section it receives the section index, span, and bar count,
and returns shots as `{start_bar_offset, length_bars, …creative fields}`. Code maps bar offsets to ms
through the real bar grid, clamps the last shot to the section end, and drops zero-length shots.

This makes a hallucinated time **unrepresentable** rather than validated-against. It is the same posture
as `matrix_text`'s "only strings already present in the brief can ever appear" — grounding by
construction, not by checking. It also means the shot grid is automatically musical: cuts land on bar
lines, which is where the lights already change.

*Alternatives considered:* (a) the LLM returns ms and code snaps to the nearest bar — rejected, it
permits a shot to be invented in the wrong section entirely and then quietly relocated; (b) exactly one
shot per section — rejected as too coarse, a 60-second chorus is not one image.

### D3 — Real resolution, an explicit override, or refuse — never a silent guess

Resolution is resolved in this order:
1. A live probe: `client.get_model(<matrix>)` → `parm1`/`parm2`, cached per layout fingerprint beside
   the existing `targetable_groups_<fingerprint>.json` precedent.
2. An explicit `--matrix-size WxH`.
3. **Refuse**, with an error naming both remedies.

The script's entire value as a contract rests on real dimensions, so inheriting `_DEFAULT_MATRIX_H = 50`
would produce a confident, wrong instruction to the video agent. Refusing is the honest third branch.
Keeping the override means the command still works with xLights closed, which is the common case for
this kind of offline work.

`matrix_text.py` is then pointed at the same resolved value, which is the first time its font sizing
will reflect reality.

*Alternative considered:* fall back to 50 with a warning. Rejected — a warning in a log does not reach
the external agent, which is the one party that needs the truth.

### D4 — Two serializations, following the `creative_brief` precedent

`video_script.json` (the machine contract, for the downstream agent) and `video_script.md` (readable, for
a human to sanity-check or hand-edit before sending). This mirrors `creative_brief.json`/`.md` already in
the cache dir, so the artifact set stays uniform and `xlo`'s existing cache conventions apply unchanged.

### D5 — A technical header distinct from the creative body

The JSON separates a `constraints` block (resolution, fps derived from the sequence `frame_ms` — 50 ms →
20 fps, never assumed; total duration; per-shot ms; loop points for sections sharing a `repetition_map`
label; a legibility budget; background/compositing intent) from the per-shot creative prose. The split
matters because the two have different authorities: constraints are computed facts the video agent must
satisfy, prose is the agent's latitude. Collapsing them invites a video agent to treat resolution as a
suggestion.

Legibility guidance is derived rather than invented: `MIN_MATRIX_PX = 50` and catalog rule #2 ("no media
effects under ~50px resolution") set the floor, and the contract states what a canvas that size cannot
carry — fine detail, small text, recognizable faces.

### D6 — `videographer` routes to an already-priced planner-tier model

Planner tier, because this is whole-song gestalt judgment (the same reason `director` and `synthesizer`
are). It must point at a model that already has a `pricing` row — otherwise Context fact #2 turns the
entire run's cost reporting to unknown. A test asserts the role's configured model is priced for both
providers, so a future re-point cannot regress `xlo report` silently.

### D7 — Document the return-trip seam; build none of it

The script's `constraints` block is designed to be exactly what a future placement pass needs to validate
a returned file (dimensions, duration, fps, loop points). That is the whole seam. Not built here:
`"Video"` into `direct_settings.DIRECT_TYPES`, a `build_video_settings` hand-authored from a live probe
(there are zero mined `Video` looks — `Video` is in `ASSET_BOUND_TYPES`), reconciliation with F-C Text on
the same prop, and the xLights media-sandbox question ("preview filenames must be bare names that land in
its container"). Each needs live hardware; none needs to block a script you can hand to a video agent
today.

## Risks / Trade-offs

- **[The script reads beautifully and the resulting video looks like mud on a ~50 px canvas]** → The
  honest risk, and not resolvable by any amount of design: it is perceptual, which this repo already
  treats as live-verify-only. Mitigations are conservative contract constraints (D5) and the feature
  being wholly opt-in. Accept that the first real verdict comes from a human watching a render.

- **[A new planner-tier role makes runs quietly more expensive]** → Subcommand-only (D1) means it never
  fires during `xlo run`; usage threads into the existing I1 telemetry so `xlo report` prices it; D6
  guarantees it is priceable.

- **[Agent returns shots that do not tile the section — gaps or overlaps]** → Code owns resolution (D2):
  overlaps are truncated to the next shot's start, trailing gaps extend the final shot to the section
  end, and a section whose shots all resolve to zero length falls back to one section-spanning shot. The
  validated output type plus bar-relative encoding make the pathological cases narrow.

- **[Matrix discovered by name substring]** → `find_matrix` matches the first model containing "matrix"
  (`matrix_text.py:61`). Inherited, not introduced; a layout with two matrices or an oddly-named one gets
  the wrong answer. The `--matrix-size` override (D3) is the escape hatch, and F-E's manifest is the
  real long-term fix.

- **[Phase 1 ships an artifact nothing consumes]** → Deliberate. It is independently useful (hand it to a
  video agent now), and it de-risks the expensive half by letting us judge script quality before building
  asset placement, a Video settings template, and sandbox handling.

## Migration Plan

Additive and reversible. No schema migration, no cache invalidation: the command reads existing cached
artifacts and writes new files alongside them. `ANALYZER_VERSION`/`STRUCTURE_VERSION` are untouched —
nothing here changes analysis or segmentation, so no cache re-derivation is triggered. Rollback is
deleting the subcommand and the role row; previously written `video_script.*` files are inert.

The one behavioral change outside the new feature is `matrix_text.py` consuming a probed matrix height
instead of an unreachable `getattr` (D3). That alters Text font sizing on any layout whose matrix is not
50 px tall, so it regenerates the golden fixture and wants a live look before it is called done.

## Open Questions

- **Will an external video agent actually honor the constraints block?** Unknowable from here, and it
  determines whether the contract needs to be stricter (e.g. an explicit per-shot frame count) or whether
  a validation pass on the returned file is required in phase 2.
- **`Video` vs `Pictures` for playback.** A frame sequence via `Pictures` may sync more reliably on a
  small matrix than a video file via `Video`, whose render cost the catalog calls "heavy" and whose
  behavior is "file-path dependent". This changes nothing about the script, but it decides what phase 2
  builds — worth settling before then.
- **How should Text and video coexist on one matrix?** F-C dims concurrent matrix effects under text for
  legibility; video is a far more aggressive occupant than a wash. Likely a treatment-level decision
  (video only in sections where Text is absent), but it needs a real render to judge.
- **Shot-count bounds.** The design clamps per section, but the right ceiling for a video agent's cost
  and coherence is unknown until we see one execute a script.
