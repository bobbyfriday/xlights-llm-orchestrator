## Context

The perception layer. Independent of the xLights capabilities (no live xLights, no LLM). Grounded this session:
- VAMP plugins present at `~/Library/Audio/Plug-Ins/Vamp` (28), incl. **qm-vamp-plugins** (tempo/beat, bar-and-beat, key, onset, segmenter), **nnls-chroma** (chroma + Chordino), **segmentino** (structure), **beatroot** (beats). The `vamp` Python module auto-discovers this standard macOS path.
- Real test audio in `/Users/rob/xlights/*.mp3`.
- xLights itself uses these QM plugins for timing marks, so our grid will align with xLights' own.
- **PROVEN end-to-end this session** (Python, arm64): `pip install vamp` builds a `vamp-1.1.0` wheel; on `01 - Baby Shark….mp3` (librosa-loaded, mp3 decode worked with no ffmpeg) — `qm-tempotracker` → tempo curve (110→126 bpm), `qm-barbeattracker` → 187 beats with bar positions, `chordino` → 59 chords, `segmentino` → 4 segments. So the required-plugins approach is de-risked, and the plugin output shapes are known.

## Goals / Non-Goals

**Goals:**
- A deterministic, offline `AudioAnalyzer(path) -> SongAnalysis` (measurements + confidences).
- Robust to missing plugins (degrade, report) and stable schema for later enrichment.
- Verified against real songs (capture-first).

**Non-Goals:**
- Stems (demucs), mood (Essentia), track-id (AcoustID/MB), lyrics — deferred enrichment.
- Section labelling / theme / mood interpretation (the agents' job).
- Timing-track creation in xLights; the orchestrator.

## Decisions

### `vamp` Python module against the system plugin dir
Use the `vamp` PyPI module which loads native VAMP plugins; it auto-discovers `~/Library/Audio/Plug-Ins/Vamp`. librosa loads the audio to a mono float array + sample rate, fed to `vamp.collect(y, sr, key, output=...)`. **Proven to build and run** (see Context). **Alternative:** `sonic-annotator` CLI — rejected (extra binary, clunkier than in-process).

### Plugins are REQUIRED — fail fast, no fallback
The core plugins are central and proven, so the analyzer **requires** them: at startup it checks the required plugin keys are discoverable and raises a clear error naming any missing ones. There is **no librosa-only degraded mode** — librosa is a *complement* (audio load + energy/spectral), not a substitute for the VAMP features. This removes a silent-degradation footgun and keeps results trustworthy. **Alternative (rejected per user):** skip-and-continue graceful degradation.

### Plugin → feature map (proven keys/outputs)
- `qm-vamp-plugins:qm-tempotracker` (output `tempo`) → tempo curve (labeled bpm at timestamps).
- `qm-vamp-plugins:qm-barbeattracker` (output `beats`) → beats; label = bar position (1=downbeat).
- `qm-vamp-plugins:qm-keydetector` → key/mode over time (this one provides a confidence-like value).
- `qm-vamp-plugins:qm-onsetdetector` → onsets.
- `segmentino:segmentino` (output `segmentation`) → structural segments; label = algorithmic id (A/B/N…). (`qm-vamp-plugins:qm-segmenter` available as an alternative.)
- `nnls-chroma:chordino` (output `simplechord`) → chord progression (label = chord, e.g. `Ebm7`); `nnls-chroma:nnls-chroma` → chroma.
- `qm-vamp-plugins:qm-tonalchange` → harmonic-change points.
Outputs are `(timestamp, label)` lists — **mostly no confidence field** (only some plugins provide one). Each extractor normalizes its plugin output to the schema and attaches a confidence **only when the plugin supplies one** (no fabrication). A required plugin that errors at runtime raises (not skipped) — failures are surfaced, not hidden.

### librosa complements (not a fallback)
RMS/energy arc (per-band via mel/STFT), spectral centroid/contrast — things VAMP doesn't give directly — plus the audio loader (`librosa.load`, mono). A self-similarity matrix may be computed **internally** for repetition analysis but is **not** part of `SongAnalysis` (it's an N×N matrix — large and non-JSON; agent-facing output stays lean).

### Fusion → one grid + confidences
`fusion.py` reconciles VAMP + librosa into a single beat grid and section list. Prefer VAMP beats (xLights-aligned); fall back to librosa beat tracking if VAMP beats are missing. Attach a per-feature confidence (from plugin outputs where available, else a heuristic such as beat-interval regularity). Output is measurements only.

### `SongAnalysis` schema (pydantic) — stable, enrichment-ready
Core fields: `tempo` (map/bpm + confidence), `beat_grid` (times + downbeat flags), `key` (map + confidence), `chords` (timed), `segments` (start/end + raw descriptor, no labels), `energy_arc` (timed series, maybe per-band), `onsets`, `harmonic_changes`, and `features_present`/`features_skipped`. **Reserved optional fields (unpopulated now):** `stem_energies`, `mood`, `track_id`/`genre`, `lyrics`. Adding the enrichment extractors later only fills these — no contract change.

### Content-hash caching
Key = hash of audio bytes (+ an analyzer version tag so cache invalidates when the pipeline changes). Cache file `data/analyses/<hash>.json`. `analyze(path, *, use_cache=True)`.

### Offline + deterministic
No LLM, no network (the core extractors are all local). Heavy CPU work (VAMP/librosa) runs synchronously here; the future orchestrator will offload it to a process pool — out of scope for this change.

### Keep the MCP server light: audio behind an extra
`librosa`+`numba`+`scipy`+`vamp` are heavy. To avoid bloating the read-only MCP server, the audio deps live under an **`xlights-core[audio]` optional extra**; `xlights-mcp` declares it, and the audio tools (`xl_analyze_song`/`xl_list_vamp_plugins`) **lazy-import** the audio module and register/run only if it's installed (clear error otherwise). The core read/write/preset tools never pull the audio stack.

## Risks / Trade-offs

- **`vamp` install on arm64** → RETIRED (built `vamp-1.1.0` wheel + ran plugins this session). Pin the working build approach (needs setuptools/wheel/Cython/numpy at build).
- **mp3 decode** → worked via librosa this session with no ffmpeg. Keep `soundfile` as the backend; if a codec ever fails, surface a clear error (don't silently mangle).
- **Plugin output shapes** → known now (`(timestamp, label)` lists); pin parsers to these.
- **Segmentation/key accuracy varies by song** → confidences exposed where available; the agent layer interprets/overrides later. Not this layer's job to be perfect.
- **Large/long audio = slow** → content-hash caching makes re-runs instant.
- **Required-plugins strictness** → if a user lacks the plugins, analysis hard-fails. Mitigation: a clear error naming the missing plugins + where to get them (they ship with xLights); `xl_list_vamp_plugins` helps diagnose.

## Open Questions

- Whether `qm-segmenter` or `segmentino` gives better sections for this corpus — both installed; default to `segmentino` (proven output), keep `qm-segmenter` as a config option.
- Energy arc granularity (per-beat vs fixed hop) — default to a fixed hop + per-section aggregation; revisit from downstream agent needs.
- Which plugins expose a usable confidence (key detector does; barbeat/chordino/segmentino don't) — record per-feature; leave confidence absent where unavailable.
