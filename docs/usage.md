# Usage Guide

How to install, configure, and make a show with the xLights LLM Orchestrator: a Claude Code
session for the creative work, and the deterministic `xlo` stage commands for everything else.

- [Install](#install)
- [Configure (.env)](#configure-env)
- [How a show is made](#how-a-show-is-made)
- [The Claude Code commands](#the-claude-code-commands)
- [The `xlo` stage commands](#the-xlo-stage-commands)
- [The song's cache dir (file contract)](#the-songs-cache-dir-file-contract)
- [The creative brief](#the-creative-brief)
- [Review feedback patterns](#review-feedback-patterns)
- [Layout onboarding (SEM_ groups)](#layout-onboarding-sem_-groups)
- [Singing faces and matrix captions](#singing-faces-and-matrix-captions)
- [Video for the centerpiece matrix](#video-for-the-centerpiece-matrix)
- [Tuning the show's voice](#tuning-the-shows-voice)
  - [The trigger cookbook](#the-trigger-cookbook)
- [Degradations](#degradations)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

---

## Install

A [uv](https://docs.astral.sh/uv/) workspace; Python 3.11+.

```bash
uv sync --all-packages --extra audio --extra preview   # everything a show needs
# or:
python -m venv .venv && . .venv/bin/activate
pip install -e "packages/xlights-core[audio]" -e packages/xlights-mcp -e "packages/xlights-orchestrator[preview]"
```

A plain `uv sync` is enough for the `xlo` CLI and the stages from `groups` through `finalize`
(brief validation, realize, apply, QA over the instructions, finalize, video planning). The extras
add: `audio` (VAMP/librosa — `xlo analyze`), `preview` (numpy/zstandard/pillow — `xlo stills` and
the rendered-coverage QA findings). Further extras on `xlights-core`: `lyrics` (CMU dictionary for
accurate singing-face phonemes), `stems` (demucs-mlx, Apple Silicon) or `stems-torch` (PyTorch
demucs). Nothing calls a model API, so there is no API key to set.

System deps:
- **ffmpeg**: audio patching at finalize, preview clips.
- **demucs**: optional, for stem separation (per-instrument energy, lyric alignment, the trigger
  detectors). Without it the stages still run; stem-dependent features skip.
- xLights' bundled **VAMP plugins** are auto-discovered for beat/tempo/key analysis; librosa is the
  fallback.
- **Claude Code**, opened in this repo, for the `/xlo:*` commands. The `xlo` stages run without it.

## Configure (.env)

Copy `.env.example` to `.env`. **No model API key is needed**: the creative work happens in your
Claude Code session, and no `xlo` command calls a model.

| Variable | Purpose |
| --- | --- |
| `XLIGHTS_BASE_URL` | xLights automation endpoint (default `http://127.0.0.1:49913`; instance "B" is `49914`). |
| `XLO_CACHE_DIR` | Root of the song caches (`.env.example` sets `data/analyses`; each song gets `$XLO_CACHE_DIR/orchestrator/<song-slug>--<hash>/`). |
| `GENIUS_ACCESS_TOKEN` | Optional. Lyric fetch → timed alignment → lyric-derived sections, color-word triggers, singing faces, matrix captions. |
| `XLO_STEMS` / `XLO_STEMS_BACKEND` / `XLO_STEMS_MODEL` | Force stems on; pick the demucs backend (`mlx`, `torch`) or model (default `htdemucs_6s`). |
| `XLO_FSEQ_METRICS` | `0` disables the rendered-pixel coverage metrics in `xlo qa`. |

> **The `.env` is gitignored. Never commit real keys.**

## How a show is made

```
/xlo:init-layout   once per layout: SEM_ groups + layout manifest
        │
/xlo:analyze  ──▶ /xlo:design ──▶ /xlo:realize ──▶ /xlo:apply ──▶ /xlo:review ──┐
  structure        brief, until      instructions     into xLights     your        │
  you confirm      you approve       + QA proposals   (watch it)       feedback    │
                        ▲                                                          │
                        └──────────── edit brief → validate → realize → apply ◀───┘
                                                                          │
                                                                /xlo:finalize ──▶ .xsq
```

`/xlo:show <mp3>` chains analyze → design → realize → apply and pauses twice: after the brief is
presented (for your edits and approval) and after the show is applied (to watch it). `/xlo:video`
is a side branch once the brief exists.

Claude does the judgment in conversation: reading the analysis digest with you, writing the brief,
turning your feedback into brief edits. Code does the rest, deterministically: the same brief
always realizes the same effects.

## The Claude Code commands

Project-local commands in `.claude/commands/xlo/`. Each loads the skills it needs, runs `xlo`
stages through Bash, reads the files they write, and talks to you in viewer language (what the
display does), never in JSON. Commands that take a song accept an mp3 path; without one they use
the song from earlier in the conversation, or ask.

| Command | Runs | Reads | Then |
| --- | --- | --- | --- |
| `/xlo:analyze <mp3>` | `xlo analyze`, `xlo groups` | `analysis_digest.md`, `vocab.json` | Summarizes the sections (m:ss, energy, dominant stems), lyric hooks, entrances and your layout's group families. **Waits** for you to correct the structure. If xLights isn't running, says so and continues without the group probe. |
| `/xlo:design` | `xlo validate-brief` (until clean) | digest, vocab, schema, `validation.json` | Loads `xlo-brief`, `xlo-sequencing`, `xlo-scenes`, `xlo-layout`; settles the concept, palette and peak; writes `creative_brief.json`; fixes every validation error; presents the brief section by section. **Waits** for your edits. |
| `/xlo:realize` | `xlo realize`, `xlo qa` | `qa.json` (`validation.json` on refusal) | Reports QA findings grouped by section as proposed brief edits. **Waits.** Without a render, QA has no coverage series and says so. |
| `/xlo:apply` | `xlo apply` (`--render` on request) | `applied.json` | Reports placed/skipped and the advice for target-missing skips. Tells you to watch it in xLights. **Waits.** |
| `/xlo:review` | `xlo stills` + `xlo qa` (when rendered), then `validate-brief`, `realize`, `apply` | stills PNGs, `qa.json` | Asks what you saw, turns it into brief edits, re-applies the whole show, summarizes what changed. **Waits.** One round per invocation; there is no automatic critique loop. |
| `/xlo:finalize` | `xlo finalize --name <seq>` | | Reports the `.xsq` path and that audio and timing tracks were patched in. |
| `/xlo:video` | `xlo video-plan --plan-only`, then `xlo video-plan --matrix-size WxH` | `media_plan.json`, `video_script.md` | Loads `xlo-video`; writes `video_story.json` for the planned media; presents the storyboard. |
| `/xlo:init-layout [show folder]` | `xlo init-layout --dry-run`, then (on your word) `xlo init-layout` | `layout_review.json` | Loads `xlo-layout`; classifies the unresolved props into `layout_overrides.json`; shows the membership diff. **Waits** before the write. |
| `/xlo:show <mp3>` | the four above in order | | Pauses after the brief and after apply. |

The skills in `.claude/skills/` are the knowledge the commands load:

| Skill | Covers | Points at |
| --- | --- | --- |
| `xlo-brief` | every brief field, the treatment table, fabric, scene casting, key moments, the validate loop, presenting the brief, applying feedback | `show_plan.py`, `creative_brief.schema.json` |
| `xlo-sequencing` | effect families by moment, energy → intensity/treatment/phrasing, accent budgets, palette and LED contrast | the sequencing guide, effects catalog, layering guide |
| `xlo-scenes` | when to cast a cookbook scene, `scene_cast`, how the brief steers the trigger layer | the scene and trigger cookbooks |
| `xlo-layout` | the `SEM_` vocabulary, the layout manifest, classifying unresolved props | `xlights-layout-semantics-spec.md` |
| `xlo-video` | the story rules and `video_story.json` shape | the video-script models |

## The `xlo` stage commands

Every stage is file-in, file-out over the song's cache dir. Name the song with `--song <mp3>`
(the cache dir is found by content hash) or `--cache <dir>`. Each prints a short summary, writes
its real output to files, and exits:

- **0**: done;
- **1**: refused or failed (validation errors, xLights refusing a clean slate, a bad story);
- **2**: a prerequisite file is missing; the message names it and the stage that makes it,
  e.g. `missing instructions.json: run xlo realize first`.

No stage calls a model. `groups`, `apply` and `finalize` talk to the running xLights; the rest are
offline.

| Command | Does | Notable flags |
| --- | --- | --- |
| `xlo analyze` | Audio analysis (beats, bars, tempo, key, chords, onsets, per-band energy; stems; timed lyrics), instrumental subdivision, and the bounded `analysis_digest.md`. Prints the song dir. | `--no-cache` re-analyzes; `--cache <dir>` alone only regenerates the digest. |
| `xlo groups` | Probes which groups xLights accepts effects on; writes `vocab.json` (groups, placeable and cellable effect types, scene ids, stems, colors, blends), the per-song `creative_brief.schema.json`, and `layout.json` (show folder, model names). | |
| `xlo validate-brief` | Checks `creative_brief.json` against the vocabulary and the song; writes `validation.json`. Exit 1 on errors. | |
| `xlo realize` | Brief → `instructions.json`: every deterministic layer (scenes, beds, fabric, accents, triggers, flashes, phrase curves, composites, faces, matrix captions, layer clamp). Refuses (exit 1) an invalid brief. | `--show-folder` (default from `layout.json`). |
| `xlo apply` | Closes any open sequence, creates a clean one, emits every instruction; writes `applied.json`. A full re-emit every time. | `--render` also renders and saves (writes the `.fseq` for `stills` and `qa`); `--name`. |
| `xlo qa` | Deterministic QA (sync, placement, variety, musicality; rendered coverage, dark and static sections when an `.fseq` exists) → `qa.json`. Nothing gates. | `--name`, `--show-folder`. |
| `xlo stills` | One preview PNG per section from the rendered `.fseq` → `stills/`. Prints a hint and exits 0 when there is no render. | `--name`, `--show-folder`. |
| `xlo finalize` | Saves and closes the open sequence, then patches the `.xsq` offline: audio, canonical render order, timing tracks. | `--name`; `--no-timing-tracks`. |
| `xlo video-plan` | `--plan-only`: the media plan from the brief. Then: validates and times `video_story.json` → `video_script.json` + `.md`. | `--matrix-size WxH` (required for the full run), `--veo-clips`, `--no-veo`, `--filmed-sections`, `--max-shot-s`, `--frame-ms`, `--allow-inherit`. |
| `xlo init-layout` | Classifies the layout's props and writes the `SEM_` groups + `layout_semantics.json`. Needs xLights **closed** to write. | `--show-folder`, `--dry-run`, `--yes`, `--invert-x`, `--no-validate`. |
| `xlo cache-rename` | Renames old hash-only cache dirs to `<song-slug>--<hash>`. Dry run unless `--apply`. | `--songs DIR`. |

## The song's cache dir (file contract)

`$XLO_CACHE_DIR/orchestrator/<song-slug>--<hash>/`, e.g.
`data/analyses/orchestrator/carol-of-the-bells--cfb62d6a5dcd3b13/`. The hash is the identity: a
renamed or copied MP3 reuses the same dir. Because every stage reads and writes files here, any
stage can be re-run on its own and a session can pick up where the last one stopped.

| File | Written by | Read by |
| --- | --- | --- |
| `song_analysis.json` | `xlo analyze` | every later stage |
| `analysis_digest.md` | `xlo analyze` | Claude (`/xlo:analyze`, `/xlo:design`, `/xlo:video`) |
| `vocab.json` | `xlo groups` | Claude, `validate-brief`, `realize`, `qa`, `stills` |
| `creative_brief.schema.json` | `xlo groups` | Claude; your editor (the brief's `$schema`) |
| `layout.json` | `xlo groups` | `realize`, `qa`, `stills`, `finalize` (show folder, model names) |
| `creative_brief.json` | **Claude** (`/xlo:design`, `/xlo:review`) or you | `validate-brief`, `realize`, `qa`, `stills`, `finalize`, `video-plan` |
| `validation.json` | `xlo validate-brief`, `xlo realize` | Claude (the fix loop) |
| `instructions.json` | `xlo realize` | `apply`, `qa` |
| `applied.json` | `xlo apply` | Claude (`/xlo:apply`), `qa` (placement) |
| `qa.json` | `xlo qa` | Claude (`/xlo:realize`, `/xlo:review`) |
| `stills/NN-<label>.png` | `xlo stills` | Claude (`/xlo:review`) |
| `media_plan.json` | `xlo video-plan` | Claude (`/xlo:video`), `video-plan` |
| `video_story.json` | **Claude** (`/xlo:video`) | `xlo video-plan` |
| `video_script.json`, `video_script.md` | `xlo video-plan` | Claude, the video renderers |

Outside the song dir: the targetable-groups probe caches per layout under
`$XLO_CACHE_DIR/orchestrator/`; stems sit beside the analysis; `layout_semantics.json` and
`layout_overrides.json` live in the xLights show folder, as does `layout_review.json` (written by
`init-layout --dry-run`). The saved `.xsq` and `.fseq` land in the show folder.

Old caches from before readable names (bare hashes) still resolve; `xlo cache-rename --songs DIR`
previews the renames and `--apply` performs them. Caches from the earlier agent pipeline keep
their analysis; their `m-xxxxxxxx/` subdirs are never read, so each such song needs one
`/xlo:design`.

## The creative brief

`creative_brief.json` is the one judgment artifact: the show's sections and what each should look
like. Claude writes it; you can edit it by hand too (VS Code validates it against
`creative_brief.schema.json` through its `$schema` key). The full field reference, defaults, a
worked section and the validate loop are in the **`xlo-brief` skill**
(`.claude/skills/xlo-brief/SKILL.md`); the essentials:

- **Show level**: `experience` and `concept` (prose for people), `palette`, `group_motifs`, and
  `key_moments` (`climax`/`accent`/`drop`/`hit` become a white flash on `SEM_ALL`; `kind: "lyric"`
  with a `text` becomes a matrix caption).
- **Sections** tile the song in order, in integer milliseconds. Each has a `label` (recurring
  labels like `chorus 1`, `chorus 2` rhyme and escalate), `target_groups` in priority order,
  `effect_family` plus up to three `effect_types`, `intensity` (0–1, tracking the digest's energy),
  `look` (what a viewer sees), a 3–5 color `palette`, `phrasing` (legato/staccato), and a
  `treatment` that decides which layers run (`full`, `pulse`, `feature`, `gesture`, `rest`; blank
  means by energy).
- **Fabric**: `fabric: {carrier, alternation, cell_beats, blend}` designs the beat carrier, the
  cell weave that walks the rhythm props: what moves (a cellable effect such as SingleStrand, Bars,
  Wave), how it alternates across the pool (`chase`, `pingpong`, `all`, `sparse`), how many beats
  each cell holds (1–8), and how it blends over the bed (`Max` by default). Two more knobs steer
  every directional effect in the section: `direction_change` (`hold`, `phrase`, `bar`, `beat`;
  blank = by energy) and `mirror` (right side moves opposite the left; on by default). All are optional;
  empty means code chooses. **An explicit `fabric.carrier` weaves even under `pulse` and
  `feature`** (`pulse` gets carrier + texture, `feature` the carrier alone), which those
  treatments otherwise withhold; leave `carrier` out to keep them fabric-free. `rest` never weaves.
- **Scenes**: `scene_id` casts a named recipe from the scene cookbook (`SC-01` … `SC-19`); its
  stack table replaces the section's generic base rows. **`scene_cast`** maps each of the scene's
  archetype rows to one real group, e.g.
  `{"G2-HERO": "SEM_FOCAL", "G2-RHYTHM": "SEM_ARCHES", "G0-ALL-LESS-HERO": "SEM_ALL_LESS_FOCAL"}`.
  Leave it `{}` and code casts by role (hero → `SEM_FOCAL`, rhythm → the section's rhythm pool,
  accent → snowflakes, canvas → the matrix group…). `scene_adaptation` is the same cast in prose for
  the reader. Details in the `xlo-scenes` skill.
- **Rhythmic intent**: `pulse_groups` (who walks the beat; also makes a quiet section rhythmic),
  `follow_stem` (whose onsets the hero follows), `accent_effect`, `pulse_on`.

`xlo validate-brief` writes `validation.json` as `{ok, errors: [{path, message, allowed}],
warnings: [{path, message}]}`. Errors (unknown names, unordered or uncovered sections, intensity
out of range, a non-cellable carrier, an unknown blend) block `realize`; each names the JSON path
and, for vocabulary errors, the allowed values. Warnings (a boundary off the downbeat, a section
longer than 32 s, the same family as the previous section) are advice.

## Review feedback patterns

Feedback always becomes a brief edit, then validate → realize → apply. `instructions.json` is never
edited by hand, and sections you didn't mention stay exactly as they were.

| You say | Claude changes |
| --- | --- |
| "Section 4 is too busy, calm it down" | that section only: intensity down a step, `treatment` to `feature` or `gesture`, fewer `effect_types`, `legato`, a longer `cell_beats` or `sparse` alternation |
| "Redo 1:05 to 1:30, bluer" (inside one section) | splits the section at 1:05 and 1:30 (snapped to downbeats; it tells you the exact times), copies the parent into each piece with the same label, makes only the middle piece bluer |
| "The second chorus should hit harder" | that section's intensity and treatment (`full`), maybe broader `target_groups` or a carrier |
| "Less white everywhere" | palettes across the show; reports which sections changed |
| "The arches never light" | checks `applied.json` for target-missing skips and `vocab.json`, swaps the group |
| A QA finding (`visual:dark`, `visual:static`) | proposes the finding's fix (raise intensity, broaden groups, add a moving carrier) and waits for your yes |

Each `/xlo:review` re-emits the whole show (seconds to a minute). Add `--render` to the apply when
you want stills and coverage QA for the next round.

## Layout onboarding (SEM_ groups)

The brief targets **semantic groups** (`SEM_FOCAL`, `SEM_ARCHES`, `SEM_SIDE_LEFT`,
`SEM_SNOWFLAKES`, `SEM_ALL`, …) derived from your xLights layout: props classified by role and
position, written into `xlights_rgbeffects.xml` once.

Run `/xlo:init-layout /path/to/show` in Claude Code, or by hand:

```bash
xlo init-layout --show-folder /path/to/show --dry-run    # membership diff + layout_review.json; layout untouched
xlo init-layout --show-folder /path/to/show              # write (xLights must be CLOSED)
```

1. **Analyze**: every model in the default preview gets a role from DisplayAs, tree pixel count,
   name heuristics and your own group names; then bands, sides, sweep order, mirror pairs and focal
   flags (`--invert-x` if your preview is mirrored).
2. **Resolve the tail**: props the rules can't place are left for review. `--dry-run` lists them
   in `layout_review.json` in the show folder (name, DisplayAs, node count, position, your group
   names, the current guess and the candidate roles). In `/xlo:init-layout`, Claude classifies
   them using the `xlo-layout` skill (asking you about any it can't justify) and writes
   `layout_overrides.json` in the show folder: `{"Prop Name": {"role": "OUTLINE"}}`. An override is
   a human decision and always wins; the next run drops it from the review list. By hand, `--yes`
   accepts the suggestions instead.
   Exit codes: `--dry-run` exits 0 whether or not props still need review; the write exits 1 when
   xLights is running, when there is no show folder / `xlights_rgbeffects.xml`, or when it wrote
   the groups with props still unreviewed (0 otherwise).
3. **Write**: the `SEM_` groups are created idempotently, your own groups untouched, a timestamped
   `.bak` taken. xLights must be **closed** (it rewrites the file from memory on exit); the command
   refuses while xLights answers its port. `/xlo:init-layout` stops for your go-ahead first.
4. **Manifest**: `layout_semantics.json` (per-prop role, capability, geometry) in the show folder.
5. **Validate**: offline structural checks plus a sweep-direction check.

Then restart xLights; the next `xlo groups` probes the new groups. Re-run after adding props.
Without `SEM_` groups a show still works, but the curated layers (rhythm pool, accents, peak fill,
scene casting) assume the `SEM_` set. Full rules: [`xlights-layout-semantics-spec.md`](../xlights-layout-semantics-spec.md).

## Singing faces and matrix captions

When a song has **timed lyrics** (needs `GENIUS_ACCESS_TOKEN`) and your layout has a singing-face
prop with a node face definition, `xlo realize` automatically generates phonemes per lyric word
(CMU dictionary with the `lyrics` extra, a letter-based fallback without) and places an xLights
**Faces** effect on each face prop; `xlo finalize` writes the matching three-layer `Faces` timing
track. Mouths rest during instrumental passages.

When your layout has a **matrix** (a model whose name contains "matrix"), the brief can put lyric
lines on it as captions: a `key_moments` entry with `kind: "lyric"` and the line as `text`. Code
snaps each caption to the aligned lyric line that matches, and drops one that matches nothing
(never a guessed time). At most 4 captions, at least 20 s apart, one per section, never in the
peak section. Text rides on top in the section's lightest color with the matrix's background
dimmed underneath.

## Video for the centerpiece matrix

`/xlo:video` writes a **storyboard** for the high-resolution video matrix: a short film that tells
the song's story while the rest of the display plays the lights. It never touches xLights.

1. `xlo video-plan --plan-only` decides, from the brief and the analysis, which sections are
   **filmed** (generated video clips: 8 s each, about 10 a day) and which are **procedural**
   (rendered by code: snow, embers, window light, fog, geometry, slow drift over a still; free, any
   length, but no people, faces, hands or animals). The climax, sections carrying lyric hooks and
   the opening rank highest; returning sections (chorus, refrain) share one filmed asset.
2. Claude writes `video_story.json` under the `xlo-video` skill: a logline, recurring motifs (a
   proxy object carries a character through procedural beats), and exactly one beat per section,
   written for its medium, with a `procedural_stand_in` on every beat. No time fields, no on-screen
   text, nothing that depicts the light display.
3. `xlo video-plan --matrix-size 1024x768` validates the story, times each beat to the brief's
   section cuts on the beat grid, splits long filmed shots on downbeats, assigns the sung lyrics,
   and writes `video_script.json`, `video_script.md` and `media_plan.json`.

| Flag | Effect |
| --- | --- |
| `--matrix-size WxH` | (required for the full run) the matrix resolution. Never guessed. |
| `--veo-clips N` | the campaign clip budget the plan may assume will be filmed (default: one day's quota). |
| `--no-veo` | an all-procedural film. |
| `--filmed-sections I,J` | sections to film first; the rest of the budget is spent by value. |
| `--max-shot-s N` | filmed clip length override (default 8 s × 1.2 retime). Procedural shots never split. |
| `--frame-ms N` | sequence frame interval (default 50 → 20 fps). |
| `--allow-inherit` | accept a story missing some beats (they hold the previous beat). |

The renderers (the clip generator, the procedural renderer, film assembly) are follow-up work that
consumes `media_plan.json` and `video_script.json`.

## Tuning the show's voice

Five hand-editable markdown files at the repo root. The skills tell Claude which to read for which
decision, and the cookbooks are also read by the deterministic layers, so an edit takes effect at
the next `/xlo:design` (and, for the cookbooks, the next `xlo realize`). No code changes.

| File | Shapes |
| --- | --- |
| `xlights-sequencing-guide.md` | musical best practices: phrasing, dynamics, the structure playbook, color. |
| `xlights-effects-catalog.md` | the effect menu, energy bands, duration classes, placement rules. |
| `xlights-layering-rendering-guide.md` | layering, blend modes, render styles. |
| `xlights-scene-cookbook.md` | named multi-prop scene recipes a section casts with `scene_id` + `scene_cast`. |
| `xlights-trigger-cookbook.md` | curated semantic accents (below). |

The skills and commands themselves (`.claude/skills/xlo-*/SKILL.md`, `.claude/commands/xlo/*.md`)
are markdown too: change them to change how Claude designs, presents or reviews.

### The trigger cookbook

`xlights-trigger-cookbook.md` defines **curated "when X happens, do Y" accents** placed sparingly
over the show by `xlo realize`. The brief never lists triggers; it only steers the beat layer they
sit on. Each trigger is a `## ` block of `- field: value` lines; an unknown entry is skipped and
logged, never fatal. Fields:

- **detector**: what finds the events: `drum_onsets` | `guitar_solo` | `lyric_color` | `instrument_entrance`
- **effect**: the xLights effect (`Shockwave`, `Lightning`, `On`, …; `stem_default` maps per stem)
- **render**: `per_model` (each prop, scaled to it) | `whole_house` (one gesture across the layout)
- **groups**: per-model target pool: `rhythm` (arches/canes/mini-trees) | `accents` (snowflakes/spinners) | `focal`
- **sections**: eligibility: `any` | `drum_prominent` | `sparse_beat` (strong beat, low overall energy) | `has_guitar_solo` | `peak`
- **select**: `all` | `rotate` (only the top-energy subset of eligible sections)
- **density**: events per selected section (`per_onset` or a number)
- **magnitude**: `any` | `top:<pct>` (only the strongest hits, e.g. `top:6`)
- **color**: `anchor_alternate` (two contrast colors) | `lyric` | `section` | `fixed:<name>`
- **direction**: `none` | `out` | `in` | `alternate` (for Shockwave, expand/collapse)
- **enabled**: `true` | `false`

Example: radiating shockwaves on the snowflakes/spinners on each drum hit, only in sparse
strong-beat sections:

```markdown
## Drum Shockwaves on Accents
- detector: drum_onsets
- effect: Shockwave
- render: per_model
- groups: accents
- sections: sparse_beat
- select: all
- density: per_onset
- color: anchor_alternate
- direction: out
- enabled: true
```

Trigger accents render **on top, opaque**: they punch through the fabric.

## Degradations

Best-effort enrichments (lyrics, stems, the group probe, render-order view, coverage sampling,
timing tracks, media staging) fail gracefully, but never silently: each stage ends with a summary
of what it lost, printed to stderr after its own summary. Reading one: `audio:stems` plus a QA run
with no coverage series explains "the show looks off and QA looked fine". The keys you are most
likely to see:

| Key | Meaning |
| --- | --- |
| `audio:lyrics` | lyric fetch/alignment failed → no timed lines (no lyric sections, faces or captions) |
| `audio:stems` | stem separation failed → no per-section instruments or stem triggers |
| `audio:instrumental-refine` | instrumental section subdivision failed |
| `groups:probe` | the targetability probe failed → the full group list is used |
| `emit:view` | the render-order view wasn't loaded → default view |
| `generate:triggers` | one or more trigger detectors failed |
| `qa:coverage-blind` | coverage sampling failed → QA can't see darkness |
| `finalize:media` | the show folder / audio staging was unavailable |
| `finalize:timing-tracks` | timing tracks couldn't be patched into the `.xsq` |
| `finalize:xsq-patch` | the offline `.xsq` patch failed |

> **Project convention:** every new best-effort `except` block must log (at least DEBUG), record a
> `degradations.note(...)`, or re-raise; never a silent `pass`. `tests/test_log_audit.py` enforces
> it.

## Troubleshooting

- **xLights not running** (connection error from `groups`, `apply` or `finalize`): start xLights
  and enable the automation listener (Preferences → Output → xFade port). `/xlo:analyze` carries on
  without the group probe; design needs it.
- **`apply refused`**: xLights couldn't give a clean slate (an open sequence it couldn't close).
  Close it in xLights and run `xlo apply` again.
- **xLights crashed during apply**: restart it and run the same `xlo apply`. Nothing is lost:
  `instructions.json` is on disk and apply always starts from a clean slate.
- **Target-missing skips** in `applied.json` (`XLightsTargetMissing`): the brief named a group
  xLights won't place on (often a stale or nested group). Swap it for a same-role group from
  `vocab.json` and re-run validate → realize → apply. If whole families are missing, re-run
  `xlo groups` (the probe is cached per layout) or `/xlo:init-layout`.
- **Validation errors**: read `validation.json`; each error has the JSON `path` and, for names,
  the `allowed` list. `xlo realize` refuses until it is clean. Warnings never block.
- **Exit 2 `missing <file>: run xlo <stage> first`**: run the stage it names (for
  `creative_brief.json`, run `/xlo:design`).
- **No `.fseq` for stills** (`no rendered .fseq … run: xlo apply --render`): the last apply didn't
  render. Run `xlo apply --render`, then `xlo stills`. Use the same `--name` throughout if you
  named the sequence. Stills and coverage QA also need the `preview` extra and a known show folder
  (from `xlo groups`, or `--show-folder`).
- **The sequence plays with no audio**: apply builds it without media on purpose (`newSequence`
  with media hangs xLights), then saves it, patches the `.xsq` to Media offline and reopens it, so
  it should open with the song (`applied.json` `audio: true`). When that step fails (song file
  moved, no show folder) the show is still saved: reopen the `.xsq`, or run `xlo finalize`.
- **Timing tracks / SEM_ groups missing**: both are written offline; reopen the sequence / restart
  xLights to load them.
- **Stems skipped**: demucs isn't installed (the core package's `stems` extra) or it failed;
  per-stem features degrade gracefully.
- **Exports to absolute paths fail**: xLights is sandboxed; the stages already use bare names that
  land in its container.

## Development

Work is structured as [OpenSpec](https://github.com/openspec) changes: propose → design → spec →
build → live-verify → archive, one feature per change, landed via pull request. Archived changes
live in `openspec/changes/archive/` and are the project's design history.

```bash
pytest                 # hermetic unit tests: no live xLights, no network
pytest -m live         # opt-in smoke tests against a running xLights
```

Conventions: Claude owns judgment, code owns realization; every deterministic layer is
hermetically tested (the golden fixture brief, the fabric canary); anything perceptual (does an
effect *read* on the props) is verified by a live render and a human watch. Pixel counts and QA
scores don't capture "looks good".
