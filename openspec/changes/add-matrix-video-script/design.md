## Context

`creative_brief.json` is cached for every show and already contains the entire creative substance of a
video script: per section the resolved `start_ms`/`end_ms` plus `look`, `palette`, `motion`,
`transition`, `intensity`, `effect_types` and `rationale`, with show-level `concept`, `experience`,
named `palette` and `key_moments` above them. The boundaries are downbeat-aligned already. A working
prototype of this entire feature is about twenty lines of Python over that file.

An earlier draft of this design proposed a Videographer LLM agent, bar-relative shot subdivision with
overlap/gap reconciliation, a live matrix-geometry probe with a per-model cache, and a new priced model
role — 32 tasks. That was over-built. Nearly all of the machinery existed to support a single choice
(letting a model subdivide sections into sub-shots), and removing that choice removes the machinery with
it. What follows is the smaller design the data actually calls for.

## Goals / Non-Goals

**Goals:**
- Project cached creative direction into a video script a generative video agent can execute against.
- Deterministic: same inputs, same bytes. No model call, no network, no key, no xLights.
- Work on every show already in the cache.
- State the technical constraints a returned video must satisfy, or refuse.

**Non-Goals:**
- Any LLM pass. Deferred on evidence, not on principle (see D6).
- Re-deriving, snapping or validating timings. They are already correct; touching them would only add
  ways to be wrong.
- Probing xLights for anything. Dimensions are an argument.
- Ingesting the returned video or placing a `Video` effect (the return trip).
- Fixing `matrix_text`'s unreachable `matrix_height`. Real bug, unrelated change.

## Decisions

### D1 — A pure export, not a pipeline stage

`xlo video-script --song <path>` reads cached artifacts and writes files. It is not a stage in
`pipeline/run.py` and not a flag on `run`: nothing downstream consumes the script, so being in the
pipeline would buy nothing while touching the refine loop and the regen splice path. As a subcommand it
also runs against the five shows already in the cache, which is how we find out whether the output is
any good.

### D2 — One shot per section; the boundaries are the cut list

Shot spans are copied from the cached section boundaries. No bar arithmetic, no snapping, no clamping,
no overlap reconciliation, no gap closing — none of it is needed, because the sections already tile the
song exactly and are already downbeat-aligned.

This is also better than sub-shots on the merits, not just simpler: the lights change at section
boundaries, so a video that cuts there reads as one gesture with the display. Finer cuts would land
where nothing else changes, which looks like the video is out of sync with the show.

*Alternative considered (and previously chosen):* let a model subdivide sections into bar-relative
shots. Rejected — it was the single source of nearly all the complexity in the first draft, and it
produces cuts the lights do not honor.

### D3 — Optional downbeat-aligned subdivision, for clip limits only

Real sections in the cached show run 7.6 s to 29.3 s; most generative video models cap a clip around
5–10 s. `--max-shot-s N` splits any section longer than N into equal parts, each snapped to the nearest
**downbeat** (`beats[].bar_position == 1` in the cached `song_analysis.json`), with every part carrying
the parent section's description and an explicit part index.

The flag is off by default and the split is mechanical, driven by a tool limitation rather than by
creative judgment. The distinction matters: this is the *only* legitimate reason to cut inside a
section, and keeping it on downbeats means even a technical split lands musically. Every shot states
its duration and frame count, so the need for the flag is visible before it is used.

### D4 — Dimensions are supplied; no probe, and no default

`--matrix-size WxH` is required; without it the command refuses. There is no probe (that was scope
creep toward the unrelated `matrix_height` bug) and deliberately no default, because a confident wrong
resolution reaches the video agent and a refusal does not. `--matrix <name>` is accepted as free-text
metadata recorded in the script for the eventual placement phase; nothing resolves or validates it
here.

### D5 — The contract is computed; the prose is copied

The JSON keeps a `constraints` object separate from the shot list. Constraints are computed facts the
video agent must satisfy: dimensions as supplied, `fps` derived from the sequence frame interval
(50 ms → 20 fps, derived not hardcoded), total duration, per-shot ms and frame counts, loop points for
`repetition_map` labels covering two or more sections, plus two fixed terms — **full-frame and fully
opaque**, and **no rendered words**.

Those two are constants, not suggestions. The matrix is dedicated to video, so there is no underlying
wash to key against and no reason for transparency; and text belongs to the other matrix, so a video
rendering lyrics would duplicate it badly. Keying on a small canvas against a moving wash was the most
likely route to a muddy result, and a reliable key colour is among the things generative video is worst
at — so the field is absent by design, not by omission.

### D6 — No LLM, with the one real gap stated in the contract

The prototype exposes the only genuine weakness of a pure export: `look` is written about the **light
display** — "the yard is barely lit", "the house outline", "arches provide a heartbeat chase", "focal
prop". Rendered literally on a 64×32 matrix that would produce a picture of a yard with arches, which
is not the point.

The export ships one sentence of contract text instead of an agent: *these descriptions are of a light
display; render the imagery and mood they evoke, not the props themselves.* That may be sufficient —
video models are good at taking mood from prose — and it costs nothing to find out. If reading real
exports shows it is not, an opt-in polish pass that rewrites `look` into frame imagery is a small
follow-up, and by then its job is known rather than assumed.

*Alternative considered (and previously chosen):* build the agent now. Rejected on evidence: the cached
`look` text is already vivid and specific, and paying a planner-tier call per song to improve prose
that may already be good enough is the wrong order of operations.

### D7 — Two serializations, following the `creative_brief` precedent

`video_script.json` (machine) and `video_script.md` (human), written into the song's cache directory via
the existing `cache_path` seam, mirroring `creative_brief.json`/`.md`. The Markdown exists because the
first real test of this feature is a person reading it and judging whether a video agent could work
from it.

## Risks / Trade-offs

- **[`look` reads as light-show description, not video imagery]** → The real risk, addressed by D6's
  contract sentence and measured by reading five real exports. If it fails, the fix is a known, small,
  opt-in pass — not a redesign.

- **[Sections are too long for one clip]** → D3's `--max-shot-s`, off by default, splitting on
  downbeats. Deliberately not guessing a default, since the limit depends on the video tool.

- **[Partial data in older caches]** → The oldest cached show has empty `look`/`motion`/`palette`
  (those fields postdate it), and even the newest has occasional blanks. The renderers must tolerate
  missing fields and the export should say plainly which sections carry no description rather than
  emitting confident empty shots.

- **[The contract promises a dedicated prop that nothing enforces]** → Harmless now (no video is
  placed), but the first end-to-end render will still have washes under the video until the placement
  phase excludes that model. Noted for the follow-up, not solved here.

## Migration Plan

Purely additive: a new subcommand and new output files. No schema change, no cache invalidation, no
`ANALYZER_VERSION`/`STRUCTURE_VERSION` bump, nothing existing reads the new files. Rollback is deleting
the module and the subcommand; previously written `video_script.*` files are inert.

## Open Questions

- **Does the contract sentence (D6) do the job?** The question this change exists to answer. Settled by
  reading the exports, not by analysis.
- **What clip length should `--max-shot-s` usually be?** Depends on the video tool; left explicit until
  there is a real one in the loop.
- **`Video` vs `Pictures` for eventual playback.** A frame sequence may sync more reliably on a small
  matrix than a video file, whose render cost the catalog calls "heavy" and whose behavior is
  "file-path dependent". Changes nothing here; decides what the placement phase builds.
