# Plan the centerpiece film across media: Veo for the few shots that need it, procedural for the rest

## Why

`xlo video-script` writes a storyboard as if every shot will be filmed. Nothing can film it. The one
generative video source we have — **Veo through the Gemini API** — gives **8-second clips, about 10 a
day**: 80 seconds of footage per day against songs of 160–260 seconds with 8–12 shots of 7–57 seconds
each (every cached storyboard). Covering one song would take 20–33 clips; a show of a dozen songs
would take weeks of quota, and the storyboards are written in a register (wrinkled hands giving way
to small hands; a traveler silhouetted on the snow) that only Veo can deliver.

The alternative renderer costs nothing and has no quota: **procedural** footage — snow, embers, light
through a window, the moon, fog, geometric motifs, slow drift over a generated still — written as code
and rendered locally, frame-exact to the sequence's 20 fps. It is very good at atmosphere and very
bad at people, faces, hands, animals and anything that must be recognized while it moves.

So the film has to be **planned across media**, and the planning has to happen **before the
Videographer writes**: a beat written for Veo and then downgraded to procedural loses its subject,
while a beat written for procedural films fine on Veo. Today's pipeline has no notion of a medium, a
clip, a quota or a day.

## What Changes

- **A deterministic media planner runs before the Videographer.** From signals already cached
  (section energies and the climax, which sections carry featured lines, repeated section labels,
  durations) plus a clip budget, it stamps each section **filmed** or **procedural**, groups repeated
  sections (the choruses) so they share one filmed asset, computes clips needed per filmed section at
  the configured clip length, and ranks filmed sections by value so the budget is spent on the climax
  and the hero moments first. No LLM counts anything.
- **The Videographer writes for the medium.** Its section list now carries each section's medium and
  asset group. The prompt gains a **procedural vocabulary** (what procedural renders do well, what is
  forbidden in a procedural beat — people, faces, hands, animals, readable objects in motion) and a
  **motif rule**: a character may appear only in filmed beats, and must be carried through procedural
  beats by a proxy object (the lantern stands for the hands). Filmed beats also carry a short
  **procedural stand-in**, so a clip that never gets rendered still has a story. A deterministic lint
  rejects a procedural beat that names a person and asks the model once for a rewrite.
- **A project-wide Veo ledger** records every clip generated (day, song, shot, seconds) at the cache
  root, so remaining quota is known across songs, not per song. The planner reads it; the renderer (a
  later change) appends to it. `--veo-clips N` caps below the ledger; `--no-veo` plans all-procedural.
- **The storyboard is written against a campaign budget, not today's quota.** The story must not
  change from day to day; which filmed shots get *rendered* today does. The plan carries a promote
  order so a later `render --promote` spends each day's quota on the next most valuable shot while
  the film is complete (procedural) from day one.
- **Clip-length splitting applies to filmed sections only**, defaulting to the configured clip length
  (8 s) and allowing a bounded retime (a 24 fps Veo clip played at 20 fps runs 9.6 s). Procedural
  sections are never split: they render any length, frame-exact.
- **Media prices as data.** A `video:` pricing block (Veo per-second rate, image model per-image rate,
  clip length, daily clip quota, quota-reset timezone) in `models/config.yaml`, so the plan states its
  Veo seconds and estimated spend and `xlo report` can price video later without a code change.
- Output: `media_plan.json` beside `video_script.json`; the Markdown script shows each shot's medium,
  asset group, clips and promote rank; a per-shot Veo prompt and procedural brief composed by code
  from the beat fields (the hand-off to the renderers).

## Capabilities

### New Capabilities
- `video-media-plan`: Deciding, before the storyboard is written and without an LLM, which sections
  of the centerpiece film are filmed (Veo) and which are procedural; grouping repeated sections to
  share a filmed asset; budgeting clips at the configured length against a campaign budget and a
  project-wide daily-quota ledger; ranking filmed shots for promotion; persisting the plan and the
  per-shot renderer hand-off; pricing the planned media spend.

### Modified Capabilities
- `video-script`: the Videographer's input gains each section's medium and asset group plus the
  procedural vocabulary and motif rule; procedural beats SHALL NOT depict people (linted, one retry);
  filmed beats SHALL carry a procedural stand-in; clip-length splitting applies to filmed sections
  only and defaults to the configured clip length. (The base spec lives in the still-open
  `add-matrix-video-script` change — archive it before this one so the delta applies cleanly.)

## Impact

- **New:** `media_plan.py` (budget, planner, reuse groups, value ranking, clip math, promote order,
  Veo/procedural hand-off text), `veo_ledger.py` (append-only JSONL at the cache root, day boundary in
  the configured timezone, remaining-quota query), tests for both.
- **Modified:** `video_script.py` (`Beat.procedural_stand_in`, `Shot.medium/asset_group/clips/
  promote_rank`, split-filmed-only, Markdown columns), `agents/videographer.py` (medium per section,
  asset groups, stand-in requirement, person-lint as an output validator), `agents/prompts/
  videographer.md` (vocabulary + motif rule), `pipeline/video.py` (plan → prompt → script → plan file),
  `models/config.yaml` (`video:` block), `cli.py` (`--veo-clips`, `--no-veo`, `--filmed-sections`),
  `docs/usage.md`.
- **Cost:** still one planner-tier LLM call per script. Zero Veo spend: this change plans and writes;
  it generates no video.
- **Out of scope (follow-up changes):** the Veo client and the ledger writer (`add-veo-render`), the
  procedural renderer and film assembly at 20 fps (`add-procedural-render`), placing a `Video` effect
  on the matrix. The ledger format, the promote order and the per-shot hand-off are defined here so
  those changes consume rather than invent them.
