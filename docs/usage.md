# Usage Guide

How to install, configure, run, and tune the xLights LLM Orchestrator.

- [Install](#install)
- [Configure (.env)](#configure-env)
- [One-time layout setup (SEM_ groups)](#one-time-layout-setup-sem_-groups)
- [Run a show](#run-a-show)
- [What the pipeline does](#what-the-pipeline-does)
- [Outputs & caching](#outputs--caching)
- [Tuning the show's voice](#tuning-the-shows-voice)
  - [The trigger cookbook](#the-trigger-cookbook)
- [Model routing & cost](#model-routing--cost)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

---

## Install

A [uv](https://docs.astral.sh/uv/) workspace; Python 3.11+ (developed on 3.14).

```bash
uv sync
# or:
python -m venv .venv && . .venv/bin/activate
pip install -e packages/xlights-core -e packages/xlights-mcp -e packages/xlights-orchestrator
```

System deps:
- **ffmpeg** — required (audio encode for the offline media patch; preview clip extraction).
- **demucs + torch** — optional, for stem separation (per-instrument analysis, lyric alignment, the trigger detectors). Without them the pipeline still runs; stem-dependent features auto-skip.
- xLights' bundled **VAMP plugins** are auto-discovered for beat/tempo/key analysis; librosa is the fallback.

## Configure (.env)

Copy `.env.example` to `.env`. Keys:

| Variable | Purpose |
| --- | --- |
| `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` | At least one required. The model registry routes each agent role to whichever provider is active. |
| `XLO_PROVIDER` | `anthropic` (default) or `gemini` — switches all roles' provider without code changes. |
| `GENIUS_ACCESS_TOKEN` | Optional. Enables lyric fetch → timed alignment → lyric-derived song sections + color-word triggers. |
| `XLIGHTS_BASE_URL` | xLights automation endpoint (default `http://127.0.0.1:49913`; instance "B" is `49914`). |
| `XLO_CACHE_DIR` | Where analysis/plan artifacts cache (default `data/analyses`). |
| `XLO_REFINE_SKIP_OBJECTIVE` | Skip the `--refine` loop (no Judge/critic/regen spend) when the first-pass objective score is ≥ this (default `88`). Set `101` to disable and always iterate. Saves cost on drafts that are already good. |
| `XLO_STEMS` | `1` to force stem separation on; otherwise the CLI requests it by default. |
| `XLO_STEMS_MODEL` / `XLO_STEMS_BACKEND` | Override the demucs model/backend. |
| `XLO_SEQUENCING_GUIDE`, `XLO_EFFECTS_CATALOG`, `XLO_LAYERING_GUIDE`, `XLO_SCENE_COOKBOOK`, `XLO_TRIGGER_COOKBOOK` | Override the path to each guide/cookbook (defaults are the repo-root `.md` files). |

> **The `.env` is gitignored — never commit real keys.**

## One-time layout setup (SEM_ groups)

The orchestrator targets **semantic groups** (`SEM_FOCAL`, `SEM_ARCHES`, `SEM_SIDE_LEFT`,
`SEM_SNOWFLAKES`, `SEM_ALL`, …) it derives from your xLights layout — props classified by role and
position. These are written into your `xlights_rgbeffects.xml` once, and xLights loads them on the
next restart.

`xlights_core.knowledge.layout_semantics` plans the groups and patches their settings
(`build_sem_groups`, `patch_sem_gridsize`, `patch_view`) — but classifying props into roles and
writing the SEM_ modelGroups into `rgbeffects.xml` is a manual/agent step today, following
[`xlights-layout-semantics-spec.md`](../xlights-layout-semantics-spec.md). Do it once with xLights
**closed** (so it doesn't overwrite the file on exit), then restart xLights. Re-do it after adding
props. (A guided `xlo init-layout` command that automates classification, group creation, and
validation is planned — see [`roadmap-2026-07.md`](roadmap-2026-07.md).)

Without SEM_ groups the run still works but targets whatever groups exist; the curated layers
(rhythm pool, accents, peak fill) assume the SEM_ set.

## Singing faces (lip-sync)

When a song has **timed lyrics** (Genius text aligned to the vocals — needs `GENIUS_ACCESS_TOKEN`) and
your layout has a **singing-face prop with a node face definition** (a `faceInfo` with the
`Mouth-AI/E/FV/L/MBP/O/U/WQ/etc/rest` shapes — the standard for HD singing props), the pipeline
automatically:

- generates phonemes from each lyric word (CMU dictionary, with a letter-based fallback),
- writes a three-layer **`Faces` timing track** (phrases / words / phonemes) into the `.xsq`, and
- places an xLights **Faces** effect on each face prop, reading that track, with the mouth resting
  during instrumental passages (`SuppressWhenNotSinging`) and eyes on Auto.

Install the optional `lyrics` extra for accurate phonemes (`uv sync --extra lyrics`); without it the
faces still sing using the heuristic fallback. Instrumental songs (no timed lyrics) place no faces.

## Matrix narrative text

When your layout has a **matrix model** (any model whose name contains "matrix"), the pipeline places
sparse narrative **Text** effects on it — the matrix is the show's storyteller, not just another wash
canvas. Text is treated as **punctuation, not captioning** (a matrix that talks all night is a chyron):

- a **title card** in the intro (the song's title, plus the artist if it fits), and
- up to **4 featured lyric phrases** — the ones the panel curated as the song's signature lines,
  each snapped to its aligned lyric line so it lands on the audio, at least 20 s apart, at most one
  per section, and **never in the peak section** (the peak belongs to the composite payoff).

**Grounded by construction:** only text already present in the brief (the song identity or a curated
featured line) can ever appear — section labels ("CHORUS"), invented captions, and full lyric
captioning never do. A featured line that doesn't fuzzy-match an aligned lyric line is dropped rather
than shown at a guessed time. Text rides on top with a `Max` blend in the section's lightest color,
and the matrix's own background is dimmed under each phrase so the glyphs stay legible; other props are
never touched. Instrumental songs get the title card only; layouts with no matrix place no text. The
caps live in `pipeline/tuning.py` (`MAX_TEXT_MOMENTS`, `TEXT_SPACING_MS`) and an advisory QA finding
fires if a future author pushes past them.

## Run a show

```bash
xlo run --song "mp3/your song.mp3" --refine --auto
```

Then in xLights: **File → Open Sequence → your song**. It opens as a Media sequence with the audio
and reference timing tracks attached.

### Flags

| Flag | Effect |
| --- | --- |
| `--song PATH` | (required) the audio file. |
| `--name NAME` | sequence name (default: derived from the filename). |
| `--refine` | run the test → critique → judge → regenerate loop (recommended). |
| `--auto` | unattended: take the Judge's verdict, skip the human review checkpoints. |
| `--no-browser` | attended run **without** the live browser surface (terminal checkpoints only). |
| `--max-iterations N` | cap on refine iterations (default 3). |
| `--no-save` | generate but don't save (leave the sequence open). |
| `--no-cache` | ignore cached analysis/brief/instructions and recompute. |
| `--no-timing-tracks` | skip patching reference timing tracks into the `.xsq`. |
| `--no-log` | disable the per-iteration revision log. |

**Attended vs `--auto`:** without `--auto`, the run pauses at checkpoints — after interpreting
the song (shows `description.md`), after the creative brief (shows `creative_brief.md`), on each
refine iteration, and at final save — so you can stop and hand-edit before generation. With `--auto`
it runs straight through.

### Run-mode matrix

| Mode | Command | Live browser | Checkpoints answered via |
| --- | --- | --- | --- |
| **Attended + browser** (default) | `xlo run --song … --refine` | yes — opens a local page (stage timeline, section grid, QA sparkline, refine log) | the browser (approve / edit / stop), never parking the event loop; a stdout line mirrors the URL |
| **Attended + terminal** | `xlo run … --refine --no-browser` | no | the original blocking terminal prompts — byte-for-byte the pre-F-I behavior |
| **Unattended** | `xlo run … --refine --auto` | no | the Judge's verdict (no human gate) |

The live surface is a stdlib-only HTTP server bound to `127.0.0.1` on an ephemeral port (no
framework, no CDN, zero external resources). A reopened/reconnected page replays missed events via
SSE `Last-Event-ID`. It exposes no state-changing GET route; checkpoint tokens are single-use.

## What the pipeline does

1. **Analyze** (`xlights-core/audio`) — tempo, beat grid, bars, key, chords, onsets, per-band energy; optional demucs stems → per-stem energy/onsets; optional Genius lyrics → forced-aligned timed words/lines. Cached by song hash.
2. **Lyric/instrumental structure** — Genius `[Verse]/[Chorus]` markers become beat-snapped, labeled song sections; instrumentals fall back to audio segmentation, subdividing long sections at harmonic seams.
3. **Interpret** — a parallel panel of analyst agents (structure, rhythm, harmony, lyrics) → a synthesizer → a `MusicBrief` (`description.md`).
4. **Design** — the Director agent → a `ShowPlan`: per-section look, palette, effect types, scene choice, rhythmic intent, key moments (`creative_brief.md`).
5. **Generate** — per section, a Generator agent emits effect instructions **and** a few `CellRecipe`s; a deterministic **weaver** expands those into beat-snapped motion cells across the props. Then code adds: the beat-accent layer, instrument-feature layer, peak fill, and the **trigger** layer.
6. **Render + critique** — the real xLights render is exported; deterministic QA (sync, placement rules, coverage, motion share) plus LLM critics (visual, technical) feed a Judge → a score + scoped revisions.
7. **Refine** — flagged sections regenerate (bounded, with an anti-oscillation ledger and objective-regression revert) until convergence or the iteration cap.
8. **Finalize** — save; offline-patch the `.xsq` to a Media sequence (attach audio), set canonical render order, and add reference timing tracks (Sections/Beats/Bars/Onsets/Chords/Lyrics).

## Outputs & caching

Under `data/analyses/`:
- `<song-hash>.json` — the cached `SongAnalysis` (+ stems under `<song-hash>/stems/`).
- `orchestrator/<song-key>/` — `song_description.json`, `creative_brief.json` (+ `.md` renders), `instructions.json`, `revision_log.{jsonl,md}`, `visual_review/iterN/` (stills/clips the critic saw).

The saved `.xsq` lands in your xLights show folder. Re-running reuses caches; `--no-cache` forces a
recompute. To re-plan only, delete the relevant `orchestrator/<song-key>/*.json` stage files.

## Resilience & degradations

**Transient-failure retry (I2).** A run makes ~10–20 LLM requests and hundreds of xLights REST
calls; a single 429/529 or a momentary connection blip used to drop an analyst or abort a whole
stage. Both seams now self-heal with bounded exponential backoff + jitter (a shared, stdlib-only
`with_retry` primitive):

- **LLM calls** retry provider overload/rate-limit/timeout classes only (HTTP 408/429/500/502/503/529
  and escaping transport/timeout errors) — never schema/auth/bad-request errors (those repeat
  identically at full token cost). Run-fatal roles (director, synthesizer, generator, judge) get 3
  attempts; best-effort roles (panel analysts, visual critic, section redesigner) get 2.
- **xLights transport**: reads retry on connection failure *and* timeout; mutations retry on
  connection failure *only*, inside the write lock (ordering preserved), and never double-apply. The
  long-running `renderAll`/`exportVideoPreview` are excluded. The retry budget is a client constructor
  knob (`retry_attempts`, default 3; `0`/`1` disables — used in tests). Constants-first: no env knob in
  v1.

The `lyricsgenius` fetch keeps its own internal `retries=1` and is intentionally **not** wrapped
(no double-retry).

**Degradations summary (I5).** Best-effort enrichments (lyrics, stems, the visual critic, the real
render, timing tracks, caching) fail gracefully — but a lost capability is no longer silent. Every
best-effort block logs at least at DEBUG; a *whole-capability* loss logs at WARNING, so
`grep -i warning` over a run log is a complete degradation list. A per-run collector aggregates them
and the run ends with a summary block; a degraded run also writes `degradations.json` beside
`revision_log.jsonl`. The closed capability taxonomy:

| Key | Meaning |
| --- | --- |
| `audio:lyrics` | lyric fetch/attach failed → no timed lines |
| `audio:stems` | all stem-separation backends failed → no per-section instruments |
| `audio:instrumental-refine` | instrumental section subdivision failed |
| `groups:probe` | targetability probe failed → using the full group list |
| `emit:view` | the SEM Master render-order view wasn't loaded → default view |
| `qa:coverage-blind` | coverage sampling failed → the objective can't see darkness |
| `qa:render-flush` | the pre-QA `.fseq` save / real-render refresh failed |
| `visual:critique` | the multimodal visual critic couldn't run this iteration |
| `visual:real-render` | the real xLights render/export was unavailable |
| `refine:redesign` | a section redesign escalation failed |
| `refine:analyst-drop` | a panel analyst was dropped after its retry |
| `generate:triggers` | one or more trigger detectors failed |
| `finalize:media` | the show folder / media staging was unavailable |
| `finalize:timing-tracks` | reference timing tracks couldn't be patched into the `.xsq` |
| `finalize:xsq-patch` | the offline `.xsq` patch step failed |
| `cache:post-refine` | persisting the revised brief/instructions failed |

Reading a summary: `stems failed` + `qa:coverage-blind` explains "the show looks off and the
objective looked fine" — the coverage QA had no `.fseq` to sample. A failed *group listing* (as
opposed to the targetability probe) is fatal by design — it raises before any LLM spend rather than
poisoning the Director prompt with an empty group list.

> **Project convention:** every new best-effort `except` block must log (at least DEBUG), record a
> `degradations.note(...)`, or re-raise — never a silent `pass`. A structural AST audit test
> (`tests/test_log_audit.py`) enforces this.

## Tuning the show's voice

Five hand-editable markdown files (repo root) — edits take effect on the next run, no code:

| File | Shapes |
| --- | --- |
| `xlights-sequencing-guide.md` | musical best-practices injected into the Director/Generator/critics. |
| `xlights-effects-catalog.md` | the effect menu, energy bands, duration classes, placement rules. |
| `xlights-layering-rendering-guide.md` | layering, blend modes, render-style (per-model vs group canvas). |
| `xlights-scene-cookbook.md` | named multi-prop scene recipes the Director casts onto your groups. |
| `xlights-trigger-cookbook.md` | curated semantic accents (below). |

### The trigger cookbook

`xlights-trigger-cookbook.md` defines **curated "when X happens, do Y" accents** placed sparingly
over the show. Each trigger is a `## ` block of `- field: value` lines; a bad/unknown entry is
skipped (logged), never fatal. Fields:

- **detector** — what finds the events: `drum_onsets` | `guitar_solo` | `lyric_color` | `instrument_entrance`
- **effect** — the xLights effect (`Shockwave`, `Lightning`, `On`, …; `stem_default` maps per stem)
- **render** — `per_model` (each prop, scaled to it) | `whole_house` (one gesture across the layout)
- **groups** — per-model target pool: `rhythm` (arches/canes/mini-trees) | `accents` (snowflakes/spinners) | `focal`
- **sections** — eligibility: `any` | `drum_prominent` | `sparse_beat` (strong beat, low overall energy) | `has_guitar_solo` | `peak`
- **select** — `all` | `rotate` (only the top-energy subset of eligible sections — keeps it sparse)
- **density** — events per selected section (`per_onset` = every qualifying hit, or a number)
- **magnitude** — `any` | `top:<pct>` (only the strongest hits, e.g. `top:6`)
- **color** — `anchor_alternate` (two contrast colors) | `lyric` | `section` | `fixed:<name>`
- **direction** — `none` | `out` | `in` | `alternate` (for Shockwave, expand/collapse)
- **enabled** — `true` | `false`

Example — radiating shockwaves on the snowflakes/spinners on each drum hit, only in sparse
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

Trigger accents render **on top, opaque** (they punch through the fabric) and survive the refine
loop. Tuning is pure markdown: change `density`, `magnitude`, `groups`, `color`, or flip `enabled`.

## Model routing & cost

`packages/xlights-orchestrator/src/xlights_orchestrator/models/config.yaml` maps each agent **role**
(director, generator, analyst, synthesizer, judge, visual_critic) to a model per provider. Defaults
route the high-volume worker roles (generator, analyst) to a cheap tier and the judgment-heavy roles
(director, synthesizer, judge, visual_critic) to a planner tier. Switch provider with
`XLO_PROVIDER`; change individual roles by editing the YAML.

Cost levers already in place: the Generator prompt carries trimmed guide extracts (not the full
guides), the refine loop stops on a plateau, and cheap tiers handle the bulk of calls. A full
refined run is a few-minutes / modest-token operation.

## Troubleshooting

- **"No LLM key found"** — set `ANTHROPIC_API_KEY` or `GEMINI_API_KEY` in `.env`.
- **Connection error / `XLightsConnectionError`** — xLights isn't running or the automation listener is off (Preferences → enable the xFade/REST port).
- **`CleanSlateRequired`** — a sequence is open in xLights; close it before generating.
- **Sequence opens as Animation with no audio** — that's an intermediate; the finished `.xsq` is patched to Media at finalize. If you opened a copy before finalize, reopen it. (The offline patch happens after the pipeline closes the sequence.)
- **Timing tracks / SEM_ groups missing** — they're written to the `.xsq` / `rgbeffects.xml` offline; reopen the sequence / restart xLights to load them.
- **Stems skipped** — demucs/torch not installed; per-stem features (instrument triggers, prominence) degrade gracefully.
- **429 / spend cap** — provider billing; switch `XLO_PROVIDER` or top up.
- **`exportVideoPreview` fails on an absolute path** — xLights is sandboxed; preview filenames must be bare names that land in its container (the pipeline already does this).

## Development

Work is structured as [OpenSpec](https://github.com/openspec) changes: propose → design → spec →
build → live-verify → archive, one feature per change, landed via pull request. Archived changes
(~50) live in `openspec/changes/archive/` and are the project's design history.

```bash
pytest                 # hermetic unit tests — no live xLights, no LLM/network calls
pytest -m live         # opt-in smoke tests against a running xLights
```

Conventions: code-owns-realization / LLM-owns-judgment; deterministic layers are hermetically
tested; anything perceptual (does an effect *read* on the props) is verified by a live render and,
ideally, a human watch — pixel counts and objective scores don't capture "looks good."
