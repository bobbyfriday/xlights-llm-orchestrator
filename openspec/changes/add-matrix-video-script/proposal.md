# Export a time-coded video script from the show's existing creative direction

## Why

The matrix is the show's storyteller (`xlights-scene-cookbook.md` SC-08), and of its real vocabulary —
"Text/Pictures/Video/Shaders" (`xlights-effects-catalog.md`) — only Text has shipped (F-C,
`pipeline/matrix_text.py`). The rest were deferred together in `docs/craft-roadmap.md` §8 for one
reason: "Pictures/Video/Shaders need asset management → OUT for now." Generative video has since made
the *content* half cheap; what stays expensive is knowing what to ask for, when, and within what
constraints.

**The pipeline already knows all three, and already writes them down.** `creative_brief.json` is cached
for every show and carries, per section, exactly the `SectionPlan` field set — resolved `start_ms`/
`end_ms`, plus `look`, `palette`, `motion`, `transition`, `intensity`, `effect_types`, `scene_id` and
`rationale` — above which sit the show-level `concept`, `experience`, named `palette`, and
`key_moments`. The `look` field is documented in `show_plan.py:40` as "PLAIN-language: what a viewer
sees here (no music theory)", and in practice reads like this, from a real cached show:

> §0 0.00s → 15.21s — "A quiet, freezing night. The yard is barely lit with a frosty blue glow, while
> slow, gentle snow falls softly across the display." · motion: *Slow, drifting, and falling down* ·
> palette: deep blue, ice blue, lavender, cool white · in: *Fade in*

That is already a shot. The timings are already resolved and already downbeat-aligned (PR #28/#29 plus
the #68 self-heal). The section boundaries are already the cut list — and because the lights change
there too, a video that cuts on them reads as one gesture with the display instead of fighting it.

So this change is an **export**, not a new pipeline stage: project cached data into a script a video
agent can execute. A prototype of the whole idea is ~20 lines and produces usable output today.

## What Changes

**A deterministic `xlo video-script` subcommand.**
- Reads the cached `creative_brief.json` (plus `song_analysis.json` for the beat grid) and writes
  `video_script.json` (machine) and `video_script.md` (human) into the song's cache directory.
- **No LLM call.** Free, offline, reproducible, hermetically testable, and it works on every show
  already in the cache. No new agent role, no `models/config.yaml` change, no token spend, and no
  effect on `xlo report`'s cost accounting.

**One shot per section, by default.**
- Shot spans come verbatim from the cached section boundaries. Nothing re-derives, re-snaps or
  re-invents a timestamp, because nothing needs to — the boundaries are already correct.
- `--max-shot-s N` optionally subdivides a long section for tools with clip-length limits, splitting on
  **downbeats** from the cached beat grid (`beats[].bar_position == 1`), so even a mechanical split
  lands musically. Off by default; the script always states each shot's duration and frame count, so
  the limit can be judged before reaching for the flag.

**A technical contract beside the creative prose.**
- Target pixel dimensions (`--matrix-size WxH`), frame rate derived from the sequence frame interval
  (50 ms → 20 fps, never assumed), total duration, per-shot `start_ms`/`end_ms` and frame counts, and
  loop points for recurring sections.
- Full-frame, fully opaque footage, and no rendered words: the video matrix is **dedicated to video**,
  and text lives on a different matrix (F-C's job). There is deliberately no chroma-key or compositing
  field — keying against an underlying wash on a small canvas is the most likely route to mud, and a
  reliable key colour is among the things generative video is worst at.
- Dimensions are supplied, never guessed: with no `--matrix-size` the command **refuses**, because a
  confident wrong resolution is worse than an error.

## Capabilities

### New Capabilities
- `video-script`: Exporting a time-coded video script from a show's cached creative direction — one
  shot per section with spans taken verbatim from the cached boundaries, optional downbeat-aligned
  subdivision for clip-length limits, the technical contract a returned video must satisfy (supplied
  dimensions, derived frame rate, durations, frame counts, loop points, full-frame opacity, no rendered
  text), both serializations and their cache location, and the requirement that the export is
  deterministic and makes no model call.

### Modified Capabilities

None. The export reads existing cached artifacts and writes new files; no existing requirement changes.

## Impact

**New code** — one module (`video_script.py`: the models, the projection, both renderers), one
subcommand in `cli.py`, one test file.

**Modified code** — `cli.py` only.

**Dependencies, cost, cache** — none, zero, untouched. No xLights connection, no network, no key, no
`ANALYZER_VERSION`/`STRUCTURE_VERSION` bump.

**Risk** — the honest one is visible in the prototype output: `look` describes the **light display**
("the yard", "the house outline", "arches provide a heartbeat chase"), but a 64×32 matrix should carry
the *imagery* (a freezing night, drifting snow), not a depiction of a yard with arches on it. The cheap
mitigation ships here: one line in the contract telling the video agent that these describe a light
show and to render the mood rather than the props. Whether that is enough is an empirical question,
answered by generating scripts for the five cached songs and reading them — not by more design.

## Deferred, deliberately

- **A Videographer LLM agent.** Considered and *not* built. Its only real value-add over the export is
  translating light-language into video-imagery, and the contract instruction above may cover that for
  free. If reading the exported scripts shows otherwise, adding an opt-in polish pass is a small,
  contained follow-up — and by then we will know what it has to fix instead of guessing.
- **The return trip** (ingest the finished video, place a `Video` effect on the matrix): `Video` is in
  `ASSET_BOUND_TYPES` so there are zero mined looks and its settings template needs hand-authoring from
  a live probe; `direct_settings.DIRECT_TYPES` needs `"Video"`; xLights' media sandbox constrains paths;
  and the matrix's dedication must be enforced by excluding that model from normal targeting (for which
  `layout_semantics.py`'s subtractive ensembles are the ready-made mechanism).
- **The `matrix_height` bug.** `matrix_text.py:218` reads `getattr(st, "matrix_height", 0)` and nothing
  ever sets it, so the hardcoded 50 is always used and the probe promised at line 216 was never built.
  Real, and worth fixing — but unrelated to this export, which takes dimensions as an argument.
  Bundling it here was scope creep; it belongs in its own small change.
