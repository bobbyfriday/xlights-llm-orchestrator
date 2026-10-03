# Generate a story-driven video script for the centerpiece matrix

## Why

The show gains a high-resolution matrix (~1024×768) that can carry real pictures and video. It is not
another prop in the yard — it is the **centerpiece**, and its job is to **tell a story** that goes with
the song: for *Christmas Canon*, snow falling past a lit window, a Christmas tree glowing in a dark
room, a vigil kept across generations — imagery that sets the song's mood, not a re-description of
what the arches and outline are doing.

The pipeline already holds the raw material for that story, cached per song:

- `song_analysis.json` → the full **lyrics** with line- and word-level timing.
- `song_description.json` (the cached MusicBrief) → `narrative_or_journey`, `candidate_themes`,
  `sentiment`, `key_mood`, `featured_lines`, `repetition_map`, labeled sections.
  For *Christmas Canon* that is: "a dream passed down from a central figure to younger generations…
  a vigil or state of anticipation"; themes *Legacy and Remembrance*, *Generational Continuity*,
  *Faith and Hope*; featured lines "This dream he had each child still knows", "We are waiting".
- `creative_brief.json` (the cached ShowPlan) → section boundaries (downbeat-aligned), per-section
  energy, the show's named palette and `concept`.

What it does **not** hold is the story itself. Turning themes and lyrics into a sequence of images
with a through-line is genuine creative invention, so this needs an LLM pass — a **Videographer** agent.

An earlier draft of this change exported the cached per-section `look` text directly. That was wrong
for this goal: `look` describes the light display ("pulses dart across the arches", "the yard returns
to a dark wash"), so the output could only ever replicate the house.

## What Changes

- **`xlo video-script --song <path> --matrix-size 1024x768`** — an opt-in subcommand over cached
  artifacts. No pipeline re-run, no xLights, never runs during `xlo run`.
- **A Videographer agent** (planner tier, routed to an already-priced model) receives the song's
  story material — lyrics with timing, narrative, themes, sentiment, mood, featured lines — plus the
  section structure, energy arc and show palette. It returns a **storyboard**: a logline, recurring
  visual motifs, and one story beat per section (subject, action, camera, lighting/colour, continuity
  from the previous beat, and the lyric it lands on, if any).
- **The agent is deliberately not given the lights' per-section `look`/`motion`/effect lists.** It
  gets the show's palette and energy so the film *harmonizes* with the house, but it cannot copy it.
- **Code owns timing.** Beats are keyed by section; code fills in the cached boundaries, frame counts
  and (optionally, `--max-shot-s`) downbeat-aligned splits for video tools with clip-length limits.
  The model never writes a timestamp.
- **A technical contract** beside the story: supplied resolution, frame rate derived from the sequence
  frame interval, durations, frame counts, full-frame opaque footage, and no rendered words (lyrics and
  titles live on the separate text matrix).
- Output `video_script.json` + `video_script.md` in the song's cache directory; token usage recorded in
  the existing telemetry so `xlo report` prices it.

## Capabilities

### New Capabilities
- `video-script`: Generating a story-driven storyboard for the centerpiece matrix from a song's cached
  story material — the Videographer agent and its validated output, the rule that it tells a story
  rather than replicating the lights, code-owned timing from cached section boundaries with optional
  downbeat-aligned splitting, the technical contract, both serializations, and opt-in invocation with
  cost accounting.

### Modified Capabilities

None.

## Impact

- **New:** `video_script.py` (models, timing resolution, renderers), `agents/videographer.py`,
  `agents/prompts/videographer.md`, a `videographer` row in `models/config.yaml`, tests.
- **Modified:** `cli.py` (subcommand), telemetry wiring.
- **Cost:** one planner-tier call per script, only when asked for. Zero otherwise.
- **Out of scope:** generating the video, ingesting it, placing a `Video` effect on the matrix, and
  enforcing that the matrix carries nothing else. Those follow once scripts prove worth filming.
