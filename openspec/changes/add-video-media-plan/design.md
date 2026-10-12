## Context

`xlo video-script` (add-matrix-video-script) produces a storyboard: one beat per cached section, timed
by code, written by a Videographer that sees only story material. It assumes an unlimited filmed
medium. The real media are:

| Medium | Source | Cost shape | Limits | Good at | Bad at |
| --- | --- | --- | --- | --- | --- |
| **filmed** | Veo via the Gemini API | per clip-second | 8 s clips, ~10 clips/day, 24 fps | people, faces, real rooms, weather on a street | exact length, exact fps, continuity across clips |
| **procedural** | code (numpy/OpenCV/ffmpeg), optionally over a generated still | ~0 | none | snow, embers, light, moon, fog, geometry, flat silhouettes, slow drift | people, faces, hands, animals, recognizable objects in motion |

Cached storyboards: 8–12 shots of 7–57 s over 160–260 s. 10 clips/day = 80 s of film: roughly a
third of one song per day. Veo cannot carry a song; the plan is which few shots it carries.

The user's position, adopted here: **write the storyboard for the medium**. A people-beat downgraded to
procedural loses its subject; a procedural-friendly beat films fine. So the media decision precedes
the Videographer, and the renderers (later changes) consume the plan rather than re-deciding.

## Goals / Non-Goals

**Goals:** a deterministic, testable media plan from cached structure and a clip budget; a storyboard
whose procedural beats are renderable and whose filmed beats earn their clips; continuity across the
two media; a project-wide daily-quota ledger the renderers will honour; a promote order so the film is
complete on day one and improves daily; media prices as data.

**Non-Goals:** calling Veo; rendering procedural footage; assembling the film; placing it on the
matrix; multi-model video (only Veo is budgeted); per-shot sub-beat media mixes (a section is one
medium).

## Decisions

### D1 — Media are decided before the storyboard, from structure, by code
Every signal the planner needs is cached before the LLM call: per-section energy and the climax
(ShowPlan), which sections carry `featured_lines` (MusicBrief lines × section spans), section labels
(MusicBrief by overlap), durations (boundaries), today's ledger. So `media_plan.plan()` is a pure
function `(sections, labels, energies, featured_hits, durations, budget, ledger_state) → MediaPlan`
run before `render_input`.

*Value score per section*, highest first: climax (+3), carries a featured line (+2 each, capped),
first section (+1: the film's opening), energy (+energy). Ties → earlier section. Deterministic, so
the same cache + budget always yields the same plan and the storyboard is reproducible.

*Alternative rejected:* letting the Videographer choose media or count clips. The agent would allocate
badly and the story would wander with the arithmetic; the existing contract (code owns every number)
already says no.

*Alternative rejected:* storyboard first, plan second, rewrite third (two LLM calls). Costs double and
still produces beats that have to be rewritten away from their subject.

### D2 — Repeated sections share one filmed asset
Sections with the same **chorus-family** label (chorus, pre-/post-chorus, refrain, hook, drop; chorus
×5 in Carmina Burana) form an **asset group**. Verses and bridges are never grouped: four sections
labeled "verse" are four different verses (first-pass output on Christmas Canon gave one "verse"
asset four different beats). A filmed group
consumes clips once; its members all reuse the asset (re-timed, mirrored or cut to each span by the
renderer). The Videographer is told which sections form a group and writes them as one shot that
returns ("give them the same imagery and action; the camera and light may vary"). Code takes the
group's first beat as the asset's prompt. Procedural sections may also be grouped so recurring
sections rhyme, but nothing is saved by it, so grouping stays label-based for both.

### D3 — Clip math, filmed only
A filmed section of `d` seconds needs `ceil(d / (clip_s × max_stretch))` clips, `clip_s = 8`,
`max_stretch = 1.2` (a 24 fps clip played frame-for-frame at 20 fps is 9.6 s; no interpolation).
Filmed shots are split on cached downbeats at that effective length by the existing
`split_long_shots`, now applied to filmed shots only; procedural shots are never split (they render
any length frame-exact). `--max-shot-s` becomes an override of the filmed clip length and never
touches procedural shots.

### D4 — Campaign budget vs today's quota
Two numbers, deliberately separate:

- **Campaign budget** (`--veo-clips N`, default = one day's quota, `--no-veo` ⇒ 0): how many clips the
  *storyboard* may assume will eventually exist. Filmed sections are chosen greedily by value score
  until their asset groups' clips exhaust it. This is fixed at script time so the story does not change
  from day to day.
- **Today's remaining quota** (ledger): how many clips a renderer may generate *now*. The plan carries
  a **promote order** (filmed assets by value score) so a future `render --promote` renders the next
  assets that fit today's remainder. Until an asset is rendered, its shots play their procedural
  stand-in; the film is complete from day one.

Default when the ledger says zero remain today: the plan is unchanged (the budget is campaign-level);
only the printed "renderable today" count drops to zero. The user chose this over all-procedural-when-
starved: the story stays better and the stand-in exists anyway.

### D5 — The ledger is project-wide, append-only, day-bounded
`cache_root()/veo_ledger.jsonl`, one line per generated clip: `{ts, day, clip_id, song_key, asset,
seconds, model}`. `day` is computed in the configured quota-reset timezone (config default
`America/Los_Angeles`; **unverified** against Google's reset — a config value, not code).
`remaining_today(limit) = limit − count(lines with day == today)`. Lives at the cache root because the
quota is per Gemini project, not per song. This change ships the model, reader and an `append()` API
with tests; the Veo renderer (later) is the only writer.

### D6 — The Videographer writes for the medium
`render_input` adds to each section line `· FILMED (asset A, 3 clips)` or `· PROCEDURAL`, and a line
listing asset groups. `videographer.md` gains:

- a **procedural vocabulary**: do (snow, embers, candle/lantern/window light, moon and stars, fog,
  aurora, water, geometric and abstract motifs, flat silhouettes of objects and landscapes, slow
  camera drift or parallax over a still) and **forbidden in procedural beats** (people, faces, hands,
  animals, crowds, vehicles, readable objects that must be recognized while moving, text);
- a **motif rule**: motifs must survive both media; a character may appear only in filmed beats and is
  carried through procedural beats by a proxy object;
- **`procedural_stand_in`** required on filmed beats (one sentence, procedural-vocabulary only).

A deterministic **person-lint** (a word list: person/people/man/woman/child/hands/face/eyes/figure/
dancer/crowd/traveler…) runs as a PydanticAI output validator over procedural beats' `imagery`/
`action` and every `procedural_stand_in`; a hit raises `ModelRetry` naming the beat and the word, once.
The lint is a list in code so a false positive is a one-line fix, and the test asserts the retry path.

### D7 — The plan is persisted and the hand-off is text composed by code
`media_plan.json` beside `video_script.json`: budget, ledger state at plan time, per-section medium /
asset group / value score / clips, per-asset promote rank, and per-shot **renderer text** — a Veo
prompt (imagery + action + camera + lighting, contract notes, no text) for filmed shots and a
procedural brief (the beat or its stand-in, palette, span, frame count) for procedural shots. Code
composes these so neither renderer parses prose, and so a future prompt tweak is one function.
`Shot` grows `medium`, `asset_group`, `clips`, `promote_rank`; Markdown shows them per shot and a media
summary (filmed sections, clips, Veo seconds, estimated spend, renderable today) under the contract.

### D8 — Prices and quota as data
`models/config.yaml` gains `video: {veo: {model, per_second_usd, clip_s, max_stretch, daily_clips,
quota_reset_tz}, still: {model, per_image_usd}}`. The planned spend is `Σ clips × clip_s ×
per_second_usd` (unknown ⇒ `None`, never 0, matching `estimate_cost`). Per-second and per-image rates
ship as TODO rows to be filled from Google's price page; the plan prints "unpriced" until then.

## Risks / Trade-offs

- **[Value score picks the wrong hero shots]** → scores and weights are data in one function; the
  Markdown shows each section's score; `--filmed-sections 3,6` lets the user pin sections and the
  planner fills the rest.
- **[Procedural beats still read as a slideshow]** → the motif rule and asset groups give recurring
  shapes; continuity across media comes from one generated still per motif used both as Veo's first
  frame and as the procedural plate (renderer changes; the plan already names the motif per shot).
- **[Person-lint false positives / misses]** → a word list, one retry, logged; misses surface when the
  procedural renderer gets a beat it cannot draw — the brief carries the stand-in so it falls back.
- **[Quota reset boundary wrong]** → configurable timezone; worst case the renderer is refused by the
  API, which the renderer treats as "day exhausted" — never a crash.
- **[Campaign budget never reached]** → the film is complete from day one by construction; unrendered
  filmed shots play stand-ins indefinitely.
- **[Reuse makes every chorus identical]** → the renderer may re-time/mirror; the agent may vary camera
  and light within a group. Accepted for v1.

## Migration Plan

Additive. Existing `video_script.json` files lack the new `Shot` fields (defaulted) and have no
`media_plan.json`; re-running `xlo video-script` regenerates both. Archive `add-matrix-video-script`
first so the `video-script` delta spec applies to a base spec.

## Open Questions

- Veo 3.x clip-length menu (4/6/8 s) and whether shorter clips cost less: affects clip math for
  short sections (a 6.9 s bridge). v1 budgets every clip at `clip_s`.
- Whether one generated still per motif (image model) belongs in this plan's budget or in the
  renderers'. v1 prices it but does not plan it.
