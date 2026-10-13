# Audio analysis as a standalone package

`xlo analyze` runs **only** the audio stage: no LLM key, no xLights. It turns one or more audio
files into a self-contained **analysis bundle** that any downstream LLM orchestration can read.
It runs the same code path as stage 1 of `xlo run` (`pipeline/analysis.py:analyze_song`), so the
bundle holds exactly what the show pipeline sees.

```bash
xlo analyze "mp3/My Song.mp3"                     # → data/bundles/My_Song/
xlo analyze mp3/*.mp3 --out bundles --no-stems    # batch, fast (no separation)
xlo analyze song.mp3 --lyrics song.txt            # align these lyrics instead of fetching from Genius
```

## What's in a bundle

```
<out>/<song-name>/
  manifest.json   versions, plugins used, capabilities present (stems / timed lyrics), degradations, files
  analysis.json   the full SongAnalysis: tempo curve, every beat (with bar position), onsets, key
                  changes, chords, harmonic changes, segments, energy arc, per-stem energy + onsets,
                  per-section instrument shares, timed lyric lines + words + section markers
  summary.json    compact per-section digest sized for a prompt (see below)
  stems/*.mp3     vocals, drums, bass, guitar, piano, other (htdemucs_6s)
```

`summary.json` has only code-derived facts, no interpretation. At the top level it has tempo,
tempo range, beats per bar, key and key changes, counts, the stem list, and a lyric overview.
Each section then lists:

| field | meaning |
| --- | --- |
| `id`, `start`, `end`, `duration` | the section (lyric marker names when lyrics aligned, else algorithmic ids) |
| `energy` | mean RMS normalized 0..1 against this song's own range |
| `beats`, `downbeats`, `onsets_per_s` | rhythmic density |
| `key`, `chords` | key in force; the chord progression with repeats collapsed |
| `dominant`, `instrument_shares` | from stem energy (when stems ran) |
| `lyrics` | the aligned lyric lines that start inside the section |

Hand `summary.json` to an LLM for judgment calls, and keep `analysis.json` for the code that
needs exact timings.

## Where the pieces come from

| feature | engine | Linux | macOS |
| --- | --- | --- | --- |
| tempo, beats/bars, key, onsets, tonal change | qm-vamp-plugins (VAMP) | built from source | Vamp Plugin Pack |
| chords | nnls-chroma / Chordino (VAMP) | built from source | Vamp Plugin Pack |
| structure | Segmentino (VAMP) | built from source | Vamp Plugin Pack |
| energy arc | librosa | pip | pip |
| stems | demucs `htdemucs_6s` | `demucs` (CPU torch) | `demucs-mlx` |
| timed lyrics | Whisper word timestamps on the vocal stem | `faster-whisper` | `mlx-whisper` |
| lyric text | Genius (`GENIUS_ACCESS_TOKEN`) or `--lyrics FILE` | | |

The three VAMP libraries are required, and apt doesn't package them.
`scripts/install-vamp-plugins.sh` compiles them with plain gcc/g++, following the upstream
Vamp Plugin Pack build. Backends are chosen at run time; set `XLO_STEMS_BACKEND={mlx,torch}`
or `XLO_WHISPER_BACKEND={mlx,faster}` to pin one.

## Running it

### 1. Docker (recommended: any container host)

```bash
docker build -f docker/audio-analysis.Dockerfile -t xlights-audio .
docker run --rm -v "$PWD/mp3:/in:ro" -v "$PWD/out:/out" -v xlo-cache:/cache \
    -e GENIUS_ACCESS_TOKEN xlights-audio "/in/My Song.mp3"
```

The image bakes in the VAMP plugins, CPU torch, and the demucs and Whisper weights, so it runs
offline. Genius is the only network call, and you can skip it with `--lyrics` or `--no-lyrics`.
CI (`.github/workflows/audio-image.yml`) builds the image, smoke-tests it, and on `main` pushes
it to `ghcr.io/<owner>/xlights-audio-analysis`. Run it anywhere that runs containers: Cloud Run
jobs, Modal, Fly, ECS, or a GPU box (swap the torch index for a CUDA one).

Expect several minutes on CPU for a 4-minute song. Stem separation is most of that, and the
result is cached by content hash under `/cache`.

### 2. Claude Code on the web (cloud sessions)

Cloud sessions run in a container with no Docker daemon, so install the stack natively:

```bash
bash scripts/setup-cloud-audio.sh      # idempotent; or set it as the environment's setup script
uv run --no-sync xlo analyze "mp3/My Song.mp3"
```

The environment's **network access** must allow these hosts (environment settings → Network
access → Allowed domains, keeping "Allow package managers" ticked):

- `github.com`: VAMP plugin sources
- `download.pytorch.org`: CPU torch
- `dl.fbaipublicfiles.com`: demucs weights, fetched on first run
- `huggingface.co`, `*.hf.co`: Whisper weights, fetched on first run
- `api.genius.com`: optional, for lyric text

### 3. Local macOS (Apple Silicon)

```bash
uv sync && uv pip install -e "packages/xlights-core[audio,lyrics,stems,align]"
```

Install the [Vamp Plugin Pack](https://www.vamp-plugins.org/pack.html), then run `xlo analyze`.
