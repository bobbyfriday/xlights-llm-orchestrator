## Why

The orchestrator's whole purpose is music-reactive sequences, but nothing yet *listens to the song*. This change adds the perception layer: extract a structured `SongAnalysis` (tempo, beats/bars, key, chords, sections, energy) from an audio file. It's the input the future analysis agents interpret into a show plan. xLights can't do this for us (`prepareAudio` is unimplemented), so it lives in our tool — and it's offline, deterministic, and safe (no LLM, no live xLights, no crash surface).

## What Changes

- Add an `audio/` package to `xlights-core` with an `AudioAnalyzer` that produces a `SongAnalysis`.
- **VAMP extractors** (via the `vamp` Python module + librosa for loading): QM Tempo/Beat + Bar-and-Beat (tempo, beats, downbeats/bars), QM Key Detector (key/mode), QM Onset Detector (onsets), QM Segmenter / Segmentino (structural sections), NNLS Chroma + Chordino (chords), QM Tonal Change (harmonic-change/transition points).
- **librosa** complements: per-band RMS/energy arc, spectral features, a self-similarity matrix (repetition).
- **Fusion** into one beat grid + section list, each feature carrying a **confidence**.
- A `SongAnalysis` pydantic schema covering the above, with **reserved optional fields** for the deferred extractors so the schema is stable when they land.
- **Content-hash caching** of analyses to `data/analyses/` (re-runs skip recompute).
- **Graceful degradation**: a missing plugin/feature is skipped with a warning and reported, never aborts.
- MCP tools `xl_analyze_song(path)` and `xl_list_vamp_plugins()`.

**Non-goals (deferred to a fast-follow `add-audio-analysis-enrichment`; schema seams reserved now, not built here):** demucs stem separation; Essentia mood/genre/danceability; AcoustID + MusicBrainz track ID; lyrics (lyricsgenius + forced alignment / whisperX) — all heavy installs / GPU-preferred / token-gated. Also out: xLights timing-track creation, the analysis LLM agents, and the orchestrator.

## Capabilities

### New Capabilities
- `audio-analysis`: Extract a structured, confidence-annotated `SongAnalysis` (tempo, beat/bar grid, key, chords, structural sections, energy arc, onsets, harmonic-change points) from an audio file, deterministically and offline, degrading gracefully when an extractor is unavailable, and caching by audio content.

### Modified Capabilities
<!-- None. Independent of the xLights read/write/preset capabilities. -->

## Impact

- **`xlights-core`** gains `src/xlights_core/audio/` (analyzer, extractors, fusion, schema) and a `data/analyses/` cache dir.
- **New dependencies:** `vamp` (Python VAMP host; uses the system plugins already at `~/Library/Audio/Plug-Ins/Vamp` — qm-vamp-plugins, nnls-chroma, segmentino, beatroot), `librosa`, `soundfile`, `numpy`. (Heavy optional deps — demucs/essentia/whisperx — are NOT added here.)
- **`xlights-mcp`** gains `xl_analyze_song` / `xl_list_vamp_plugins` tools.
- **Verification:** real `.mp3`s exist in the show folder for capture-first testing.
- **Downstream:** `SongAnalysis` is consumed by the future analysis agents; the reserved optional fields are filled by the enrichment fast-follow.
