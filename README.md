# xLights LLM Orchestrator

Turn an MP3 into a finished [xLights](https://xlights.org) light-show sequence with a pipeline of
LLM agents. Point it at a song; it analyzes the music, designs a show, generates effects across
your props, renders and critiques the result, refines, and saves a playable `.xsq` with the audio
and timing tracks attached.

> Full walkthrough: **[docs/usage.md](docs/usage.md)**. Architecture & diagrams: **[docs/architecture/](docs/architecture/README.md)**.

## What it does

```
MP3 ─▶ analyze ─▶ interpret ─▶ design ─▶ generate ─▶ render+critique ─▶ refine ─▶ save .xsq
       (audio/     (LLM panel   (LLM       (per-section  (real render +    (scoped   (+audio,
        stems/      → brief)     show       effects +     LLM critics +    regen)    timing
        lyrics)                  plan)      cell fabric)   QA gates)                  tracks)
```

The split throughout: **the LLM owns judgment** (themes, palette, section design, effect recipes)
and **code owns realization** (timing from the beat grid, palette → real settings strings, render
order, brightness, sparsity). Musical structure comes from Genius lyric markers (or audio
segmentation for instrumentals); rhythm and accents are placed deterministically from the audio.

## Repository

A [uv](https://docs.astral.sh/uv/) workspace of three installable packages:

| Package | Role |
| --- | --- |
| [`xlights-core`](packages/xlights-core) | Async REST client, audio analysis (VAMP/librosa/stems/lyrics), the mined effect-preset library, layout semantics. No LLM deps. |
| [`xlights-mcp`](packages/xlights-mcp) | A FastMCP server exposing xLights read/edit operations as tools (usable from Claude Code). |
| [`xlights-orchestrator`](packages/xlights-orchestrator) | The LLM pipeline: agents, the deterministic weave/beat/trigger layers, the refine loop, the `xlo` CLI. |

## Quickstart

```bash
uv sync                                   # or: pip install -e packages/*
cp .env.example .env                      # add ANTHROPIC_API_KEY or GEMINI_API_KEY (+ GENIUS_ACCESS_TOKEN for lyrics)

# xLights running, automation listener on, your layout's SEM_ groups built once (see docs)
xlo run --song "mp3/your song.mp3" --refine --auto
```

Open the named sequence in xLights (File → Open Sequence) to play it with audio.

### Targeted fixes: regenerate one section

To redo a single section without re-running the whole show (a targeted fix), use `xlo regen` —
it reloads the cached show, regenerates just that section, and leaves every other section intact:

```bash
xlo regen --song "mp3/your song.mp3" --list                       # list sections (index, time, look)
xlo regen --song "mp3/your song.mp3" --section 4 --note "too busy, calm it down"
```

Use this for a one-off correction; use `xlo run --refine` when you want the automatic
test→judge→refine loop to re-evaluate the whole show.

### Cost & quality report

`xlo report` is a deterministic, offline dashboard over the refine loop's revision logs — no
LLM, no xLights, no network, no key required. It answers cost-per-show, cost-per-objective-point,
churn, reverts, skip-gate rate, and the stop-reason mix. Pre-telemetry runs still report full
quality metrics (their cost cells render `—`).

```bash
xlo report                                # terminal tables over all songs
xlo report --song "mp3/your song.mp3"     # one song
xlo report --html report.html             # a self-contained page (no JS, no external URLs)
xlo report --json                         # the Report model as JSON (A/B harness input)
xlo report --reprice                      # recompute cost from the current price table
```

## Editable show "voice"

Five hand-editable markdown files shape the agents and the deterministic layers — tune them
without touching code:

- `xlights-sequencing-guide.md`, `xlights-effects-catalog.md`, `xlights-layering-rendering-guide.md` — best-practices injected into the agents
- `xlights-scene-cookbook.md` — named multi-prop scene recipes the Director composes from
- `xlights-trigger-cookbook.md` — curated semantic accents (drum-hit shockwaves, guitar-solo lightning, lyric color words) — see [docs/usage.md](docs/usage.md#the-trigger-cookbook)

## Prerequisites

- Python 3.11+ (the repo currently runs on 3.14)
- A running **xLights** with the automation/REST listener enabled (`http://127.0.0.1:49913`)
- One LLM key (`ANTHROPIC_API_KEY` and/or `GEMINI_API_KEY`); optional `GENIUS_ACCESS_TOKEN` for lyrics
- `ffmpeg` (audio encode + preview clips); demucs/torch for stems (optional, auto-skips)

## MCP server

```bash
xlights-mcp        # stdio MCP server: xl_get_models, xl_add_effect_from_preset, xl_render_all, …
```

## Tests

```bash
pytest                 # hermetic unit tests (no live xLights / no LLM calls)
pytest -m live         # opt-in smoke tests against a running xLights
```

## Contributing

Changes are developed as [OpenSpec](openspec/) proposals (propose → design → build → live-verify →
archive) and land via pull request. See [docs/usage.md](docs/usage.md#development) and
`openspec/changes/archive/` for the full history of ~50 changes.
