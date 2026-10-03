# Add a Videographer agent that writes a time-coded video script for the video matrix

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
for a matrix prop dedicated to showing it.

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
- exact pixel dimensions of **the video matrix specifically** (see the two requirements below),
- total duration and per-shot `start_ms`/`end_ms`,
- frame rate derived from the sequence's `frame_ms` (50 ms default → 20 fps), not assumed,
- loop points for shots covering repeated sections (`repetition_map`),
- low-resolution legibility guidance — a ~50 px canvas cannot carry fine detail, faces, or text,
- full-frame, fully opaque footage: the video matrix is **dedicated to video**, so there is no
  chroma-key, no compositing over an underlying wash, and no instruction to render words (text lives on
  a different matrix and is F-C's job).

**Target the right matrix, and refuse when that is ambiguous.** This layout has more than one matrix —
the cached targetable groups include a plural `Matrixes` group, used as `G2-CANVAS`/`G2-HERO` in real
scene adaptations — and text and video are now on different ones. But `find_matrix(model_names)` returns
"the first name containing 'matrix', case-insensitive" (`matrix_text.py:61`), so on a multi-matrix layout
F-C Text already lands on whichever model `get_model_names()` happens to return first. Which one that is
cannot be determined offline, because the individual model names are not cached anywhere (that cache
holds *groups*). The video path therefore takes an explicit model name (flag or configured default),
uses the sole candidate when there is only one, and **refuses, listing every candidate, when the choice
is ambiguous** — a video rendered for the wrong prop's dimensions, destined for the prop meant to be
showing text, is exactly the failure worth being loud about. `find_matrix` additionally warns with all
candidates named when Text falls through to first-match, making a long-standing arbitrary choice visible
without changing it.

**Discover the video matrix's real resolution (a prerequisite, and a latent bug).**
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
- A standalone `xlo video-script --song <path>` subcommand that works off a cached show, so existing
  shows produce a script with nothing regenerated. Deliberately NOT a stage inside `xlo run`: nothing
  downstream consumes the script in phase 1, so a new planner-tier call never fires during a normal run
  (design.md D1).
- The agent's `RunUsage` threads into the existing token telemetry (I1) so `xlo report` prices it like
  every other role rather than it becoming invisible cost.

**Explicitly NOT in this change — the return trip.** Ingesting the finished video file and placing it
as an xLights `Video` effect on the matrix is deliberately out of scope here, and the design documents
the seam rather than building it. It is a materially different body of work with its own live-hardware
dependencies: `Video` is in `ASSET_BOUND_TYPES` (`constants.py:9`) so there are **zero mined Video
looks** (verified: 0 hits in `presets/looks.json`), meaning its settings template must be hand-authored
from a live xLights probe exactly as the Faces template was; `direct_settings.py:23` would need `"Video"`
added to `DIRECT_TYPES` plus a `build_video_settings`; xLights' sandbox constrains media paths
(`docs/usage.md` troubleshooting: "preview filenames must be bare names that land in its container"),
which is an unanswered question for a generated file; and the video matrix's **dedication has to be
enforced** by excluding that model from the pipeline's normal targeting, for which the existing
subtractive-ensemble pattern (`SEM_ALL_LESS_FOCAL`, "the bed goes on everything except the feature") is
the obvious mechanism. Phase 1 ships something useful on its own — a script you can hand to a video
agent today — and keeps that risk out of it.

## Capabilities

### New Capabilities
- `video-script`: Generating a time-coded video script from a show's cached artistic direction — the
  Videographer agent role and its validated output type, the authority rule that timings come from the
  beat grid and section boundaries rather than the LLM, identification of which matrix the video is for
  (with refusal rather than a guess when several exist), the technical contract the script must state
  for a returned video to be usable on that prop (resolution, frame rate, durations, loop points,
  legibility limits, and full-frame opacity on a dedicated matrix), discovery of that matrix's real
  pixel dimensions with explicit behavior when they cannot be determined, the serialized artifact and
  its cache location, and the opt-in invocation plus cost accounting.

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
- A matrix-role/geometry module: resolve *which* matrix is the video prop (explicit name → configured
  default → sole candidate → refuse) and probe its real dimensions, written so `matrix_text.py` can
  consume the same probe for its own matrix.
- Script serialization into the per-song cache dir beside `creative_brief.md` / `show_plan.json`,
  in both a machine form (JSON, for the downstream agent) and a readable form (Markdown, for a human).

**Modified code**
- `cli.py` (the new `video-script` subcommand with `--matrix`/`--matrix-size`), `matrix_text.py`
  (consume the probed height instead of the unreachable `getattr`, and warn when its matrix choice is
  ambiguous), the token-telemetry wiring, and `models/registry.py` routing for the new role. No change
  to `pipeline/run.py` — the design deliberately keeps this out of the run pipeline.

**Dependencies** — none new. No xLights write path, no new audio or media dependency; the probe uses the
existing read client, and the script is a file.

**Cost** — one additional planner-tier call per run when the flag is set; zero when it is not.

**Risk** — the honest one is that the script reads well and the video it yields still looks wrong on a
~50 px canvas. A second, narrower one: the contract promises the video agent a dedicated prop, but
nothing enforces that until the placement phase excludes the matrix from normal targeting, so the first
end-to-end render will not be a fair test of the contract unless that is done by hand. That is a perceptual question this repo already treats as live-verify-only
(`docs/usage.md`: "anything perceptual… is verified by a live render and, ideally, a human watch"), so
the design keeps the contract's constraints conservative and the whole feature opt-in.
