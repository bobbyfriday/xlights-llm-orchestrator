# Add a Videographer agent that writes a time-coded video script for the matrix

## Why

The matrix is the show's storyteller — `xlights-scene-cookbook.md` SC-08 says so outright, and the
effects catalog lists its real vocabulary as "Text/Pictures/Video/Shaders" (`xlights-effects-catalog.md`
§Video: "Narrative content, complex animated imagery where Pictures falls apart… Best on: High-density
matrix/panels"). F-C shipped the first of those four: sparse narrative **Text**
(`pipeline/matrix_text.py`). The other three were deferred together in `docs/craft-roadmap.md` §8 for
one reason — "Pictures/Video/Shaders need asset management → OUT for now" — not because they lack value.

Meanwhile the pipeline already derives an unusually complete, time-coded account of what the show should
*look* like, and throws none of it at the matrix's narrative job. `SectionPlan.look` is documented in
`show_plan.py:40` as "PLAIN-language: what a viewer sees here (no music theory)" — which is, almost
exactly, a shot description. Beside it per section sit `palette`, `motion`, `transition`, `phrasing`,
`treatment`, `intensity`, `scene_id` and `rationale`, all bounded by real `start_ms`/`end_ms`. Above
that the brief carries `identity`, `candidate_themes`, `key_mood`, `narrative_or_journey`,
`narrative_summary`, `sentiment`, `featured_lines` and `featured_lyric_moments`
(`music_brief.py:52-69`), and the rhythm analyst contributes `climax_ms`, `builds_ms`, `drops_ms` and
`accents_ms` (`music_brief.py:80-87`). Every artifact is cached per song under `XLO_CACHE_DIR`, so this
material is already sitting on disk for every show ever generated.

Generative video has become the cheap half of this problem; the expensive half is knowing *what* to
ask for, *when*, and *within what constraints*. That is precisely what this repo already computes. So
the opportunity is narrow and well-posed: emit a **video script** — a time-coded creative brief plus a
hard technical contract — that an external video-generation agent can execute against, producing footage
destined for the matrix.

## What Changes

**The Videographer agent (new LLM role).**
- Add a `videographer` role to `agents/` and `models/config.yaml` alongside the existing six
  (`director`, `generator`, `analyst`, `classifier`, `synthesizer`, `judge`), with a prompt under
  `agents/prompts/videographer.md`. Planner tier: this is gestalt creative judgment over the whole song.
- It receives the `MusicBrief` + `ShowPlan` + section timings and returns a structured `VideoScript`
  (a pydantic `output_type`, so malformed output fails validation rather than reaching a file).

**Code owns timing; the LLM owns the imagery.**
- The agent never invents a timestamp. Shot boundaries are supplied to it as the real section spans and
  the brief's `transition_cues_ms` / `climax_ms` / `builds_ms` / `drops_ms`, and its output is
  **re-snapped** to the beat grid on the way out. This mirrors the split the repo already enforces
  everywhere else (`README.md`: "the LLM owns judgment… code owns realization").
- Shot durations are clamped to section boundaries so a shot can never straddle a cut the lights honor.

**The script is a contract, not just prose.** Each script carries a technical header the returned video
must satisfy, so the footage actually drops onto the matrix:
- exact matrix pixel dimensions (see the resolution requirement below),
- total duration and per-shot `start_ms`/`end_ms`,
- frame rate derived from the sequence's `frame_ms` (50 ms default → 20 fps), not assumed,
- loop points for shots covering repeated sections (`repetition_map`),
- low-resolution legibility guidance — a ~50 px canvas cannot carry fine detail, faces, or text,
- background/chroma-key intent, since the catalog notes "Chroma key lets footage composite over lower
  layers" and the matrix also has focal duties the video must not simply obliterate.

**Discover the matrix's real resolution (a prerequisite, and a latent bug).**
`matrix_text.py:218` reads `int(getattr(st, "matrix_height", 0) or _DEFAULT_MATRIX_H)` and
**nothing in the codebase ever sets `st.matrix_height`** — verified by grep across `packages/` and
`tests/`. So the hardcoded `_DEFAULT_MATRIX_H = 50` is always what is used, and the "a live
`client.get_model("Matrix")` probe (parm1/parm2) is the interim" noted at `matrix_text.py:216` was never
built. Matrix Text has therefore been sizing fonts against an assumption since F-C shipped. Text
tolerates that; a video contract cannot — you cannot tell an external agent to render at the matrix's
resolution without knowing it. This change adds the probe (`get_model` already returns "that model's
full attributes" per the `xlights-read-access` spec), which fixes `matrix_text`'s font sizing as a
side effect.

**Opt-in and accounted for.**
- A `--video-script` flag on `xlo run` (plus a standalone path that works off a cached show, so existing
  shows can produce a script without regenerating anything). Off by default — a new planner-tier agent
  is real per-run spend.
- The agent's `RunUsage` threads into the existing token telemetry (I1) so `xlo report` prices it like
  every other role rather than it becoming invisible cost.

**Explicitly NOT in this change — the return trip.** Ingesting the finished video file and placing it
as an xLights `Video` effect on the matrix is deliberately out of scope here, and the design documents
the seam rather than building it. It is a materially different body of work with its own live-hardware
dependencies: `Video` is in `ASSET_BOUND_TYPES` (`constants.py:9`) so there are **zero mined Video
looks** (verified: 0 hits in `presets/looks.json`), meaning its settings template must be hand-authored
from a live xLights probe exactly as the Faces template was; `direct_settings.py:23` would need `"Video"`
added to `DIRECT_TYPES` plus a `build_video_settings`; and xLights' sandbox constrains media paths
(`docs/usage.md` troubleshooting: "preview filenames must be bare names that land in its container"),
which is an unanswered question for a generated file. Phase 1 ships something useful on its own — a
script you can hand to a video agent today — and keeps that risk out of it.

## Capabilities

### New Capabilities
- `video-script`: Generating a time-coded video script from a show's cached artistic direction — the
  Videographer agent role and its validated output type, the authority rule that timings come from the
  beat grid and section boundaries rather than the LLM, the technical contract the script must state
  for a returned video to be usable on the matrix (resolution, frame rate, durations, loop points,
  legibility and compositing intent), discovery of the matrix's real pixel dimensions with explicit
  behavior when they cannot be determined, the serialized artifact and its cache location, and the
  opt-in invocation plus cost accounting.

### Modified Capabilities

None. Two notes, since the absence is deliberate rather than an oversight:

- The capability that owns matrix content behavior is `matrix-text`, declared by **`add-narrative-props`,
  which is implemented but not yet archived** — so it does not exist in `openspec/specs/` and cannot
  take a delta. The matrix-resolution requirement therefore lands in `video-script` (which is what
  *needs* it), and `matrix_text.py` inherits the fix as an implementation improvement, not a spec change.
- The placement-side capabilities that *would* change — `asset-placement` and `xlights-sequence-editing`
  — change only in the deferred return trip described above, so their deltas belong to that change.

## Impact

**New code**
- `agents/videographer.py` + `agents/prompts/videographer.md`; a `VideoScript` model (section/shot
  records, technical header) beside the existing `show_plan.py` / `music_brief.py` models.
- A `videographer` entry in `models/config.yaml` (both providers, planner tier).
- A matrix-geometry probe, written so `matrix_text.py` can consume the same value.
- Script serialization into the per-song cache dir beside `creative_brief.md` / `show_plan.json`,
  in both a machine form (JSON, for the downstream agent) and a readable form (Markdown, for a human).

**Modified code**
- `cli.py` (the `--video-script` flag and the cached-show path), `pipeline/run.py` (stage invocation),
  `matrix_text.py` (consume the probed height instead of the unreachable `getattr`), the token-telemetry
  wiring, and `models/registry.py` routing for the new role.

**Dependencies** — none new. No xLights write path, no new audio or media dependency; the probe uses the
existing read client, and the script is a file.

**Cost** — one additional planner-tier call per run when the flag is set; zero when it is not.

**Risk** — the honest one is that the script reads well and the video it yields still looks wrong on a
~50 px canvas. That is a perceptual question this repo already treats as live-verify-only
(`docs/usage.md`: "anything perceptual… is verified by a live render and, ideally, a human watch"), so
the design keeps the contract's constraints conservative and the whole feature opt-in.
