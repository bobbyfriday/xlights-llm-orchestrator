# xLights LLM Orchestrator

Turn an MP3 into a finished [xLights](https://xlights.org) light-show sequence by talking it
through with [Claude Code](https://claude.com/claude-code). Claude reads an analysis of the song,
discusses it with you, and writes a creative brief. A deterministic `xlo` command-line toolkit
turns that brief into thousands of beat-aligned effects across your props, places them in the
running xLights, and saves a playable `.xsq` with the audio and timing tracks attached.

> Full walkthrough: **[docs/usage.md](docs/usage.md)**. Architecture & diagrams: **[docs/architecture/](docs/architecture/README.md)**.

## What it does

```
MP3 ─▶ analyze ─▶ design ─────▶ realize ─▶ apply ─▶ review ─▶ finalize
       (audio,     (Claude +     (brief →   (live     (you      (save .xsq
        stems,      you write     effects,   xLights,  watch,    + audio
        lyrics,     the creative  QA; no     clean     Claude    + timing
        digest)     brief)        model)     slate)    edits the tracks)
                                                       brief) ──┐
                                  ▲─────────────────────────────┘
```

The split throughout: **Claude Code owns judgment** (what the song is, where the peak is, the
palette, each section's look, what to change after watching) and **code owns realization**
(timing from the beat grid, palette → real settings strings, layering, render order, brightness,
sparsity, triggers). The one artifact in between is `creative_brief.json`: Claude writes it, a
validator checks it, and every later stage reads it. Musical structure comes from Genius lyric
markers (or audio segmentation for instrumentals); rhythm and accents are placed deterministically
from the audio.

## Repository

A [uv](https://docs.astral.sh/uv/) workspace of three installable packages, plus the Claude Code
skills and commands under `.claude/`:

| Package | Role |
| --- | --- |
| [`xlights-core`](packages/xlights-core) | Async REST client, audio analysis (VAMP/librosa/stems/lyrics), the mined effect-preset library, layout semantics, the offline preview renderer. |
| [`xlights-mcp`](packages/xlights-mcp) | A FastMCP server exposing xLights read/edit operations as tools (usable from Claude Code). |
| [`xlights-orchestrator`](packages/xlights-orchestrator) | The `xlo` stage CLI: digest, brief validation, the deterministic weave/beat/trigger/scene layers, QA, stills, finalize, video planning. **No LLM dependency.** |

| `.claude/` | Role |
| --- | --- |
| `skills/xlo-*` | What Claude knows: `xlo-brief` (the brief file and its loop), `xlo-sequencing`, `xlo-scenes`, `xlo-layout`, `xlo-video`. Each points at the hand-editable guides below. |
| `commands/xlo/*` | What Claude does: `/xlo:analyze`, `/xlo:design`, `/xlo:realize`, `/xlo:apply`, `/xlo:review`, `/xlo:finalize`, `/xlo:video`, `/xlo:init-layout`, `/xlo:show`. |

## Quickstart

```bash
uv sync --all-packages --extra preview       # or: pip install -e packages/*
cp .env.example .env                         # optional GENIUS_ACCESS_TOKEN for lyrics
```

With xLights running (automation listener on) and your layout's `SEM_` groups built once
(`/xlo:init-layout`, see the docs), open Claude Code in this repo and run:

```
/xlo:show mp3/your-song.mp3
```

Claude analyzes the song and shows you its structure, writes and validates the brief and presents
it section by section (it waits for your edits), then realizes and applies it into xLights and
stops so you can watch. When it looks right, `/xlo:finalize` saves the `.xsq`; open it in xLights
(File → Open Sequence) to play it with audio.

Every stage is also a plain command you can run by hand. Each one reads and writes files in the
song's cache dir, so you can stop and resume anywhere:

```bash
xlo analyze        --song "mp3/your song.mp3"   # analysis + analysis_digest.md
xlo groups         --song "mp3/your song.mp3"   # targetable groups → vocab.json + brief schema
#   … write creative_brief.json (Claude, or by hand against creative_brief.schema.json) …
xlo validate-brief --song "mp3/your song.mp3"   # validation.json; exit 1 on errors
xlo realize        --song "mp3/your song.mp3"   # instructions.json
xlo qa             --song "mp3/your song.mp3"   # qa.json
xlo apply          --song "mp3/your song.mp3"   # into xLights → applied.json (--render for the .fseq)
xlo finalize       --song "mp3/your song.mp3"   # save + audio + timing tracks
```

### The review cycle

You watch the show in xLights and say what to change, in your words: "section 4 is too busy",
"redo 1:05 to 1:30, bluer", "less white overall". `/xlo:review` turns that into edits to the brief
(splitting a section when your time range falls inside one), validates, re-realizes and re-applies
the whole show, and summarizes what changed. With a rendered apply it also looks at per-section
still images and the QA coverage findings first. Nothing reviews automatically: you decide.

### Video for the centerpiece matrix

`/xlo:video` has Claude write a short film that tells the song's story (a logline, recurring
motifs, one beat per section) and `xlo video-plan` time it to the show's section cuts and plan
which sections are filmed and which are rendered procedurally. See
[docs/usage.md](docs/usage.md#video-for-the-centerpiece-matrix).

## Editable show "voice"

Five hand-editable markdown files at the repo root are the single source of craft. The skills
point Claude at them, and the deterministic layers read the cookbooks directly, so edits take
effect on the next design without touching code:

- `xlights-sequencing-guide.md`, `xlights-effects-catalog.md`, `xlights-layering-rendering-guide.md` — best practices Claude designs by
- `xlights-scene-cookbook.md` — named multi-prop scene recipes a section can cast onto your groups
- `xlights-trigger-cookbook.md` — curated semantic accents (drum-hit shockwaves, guitar-solo lightning, lyric color words) — see [docs/usage.md](docs/usage.md#the-trigger-cookbook)

The skills (`.claude/skills/xlo-*/SKILL.md`) and commands (`.claude/commands/xlo/*.md`) are plain
markdown too; change them to change how Claude works.

## Prerequisites

- Python 3.11+ and [uv](https://docs.astral.sh/uv/)
- [Claude Code](https://claude.com/claude-code) for the conversational flow (the `xlo` stages run without it)
- A running **xLights** with the automation/REST listener enabled (`http://127.0.0.1:49913`)
- **No model API key.** Optional `GENIUS_ACCESS_TOKEN` for lyrics (timed lyrics, lyric-derived sections, singing faces)
- `ffmpeg` (audio patching, preview clips); demucs for stems (optional, auto-skips)

## MCP server

```bash
xlights-mcp        # stdio MCP server: xl_get_models, xl_add_effect, xl_render_all, …
```

Register it with Claude Code for live read/edit operations the `xlo` stages don't cover.

## Tests

```bash
pytest                 # hermetic unit tests (no live xLights, no network)
pytest -m live         # opt-in smoke tests against a running xLights
```

## Contributing

Changes are developed as [OpenSpec](openspec/) proposals (propose → design → build → live-verify →
archive) and land via pull request. See [docs/usage.md](docs/usage.md#development) and
`openspec/changes/archive/` for the design history.
