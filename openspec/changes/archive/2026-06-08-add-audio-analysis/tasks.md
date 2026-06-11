> **Build result:** all tasks done, verified offline. Full pipeline runs end-to-end on a real show .mp3: 96s → ~117bpm, Eb major, 187 beats (47 downbeats), 59 chords, 4 segments, 400-pt energy arc. 42 tests pass. MCP `xl_analyze_song`/`xl_list_vamp_plugins` registered (lazy). Benign stderr noise from Qt helper libs in the VAMP dir (harmless; real plugins load).

> **Pre-verified this session (capture-first):** `vamp 1.1.0` builds on arm64 (needs
> setuptools/wheel/Cython/numpy at build time); `librosa` loads the show `.mp3`s (mp3 decode,
> no ffmpeg); and `qm-tempotracker`/`qm-barbeattracker`/`chordino`/`segmentino` all return real
> data on `01 - Baby Shark….mp3`. Plugin outputs are `(timestamp, label)` lists. Plugins are
> **required** (no librosa fallback).

## 1. Deps (pin the proven build)

- [x] 1.1 Add audio deps under an `xlights-core[audio]` **extra**: `vamp`, `librosa`, `soundfile`, `numpy` (keeps the base/MCP install light). Document the build prerequisites (setuptools/wheel/Cython/numpy) that made `vamp` compile.
- [x] 1.2 Add a required-plugin check: verify `qm-vamp-plugins`, `nnls-chroma`, `segmentino` are discoverable; raise a clear error naming any missing ones.

## 2. Schema

- [x] 2.1 `audio/schema.py`: `SongAnalysis` (tempo curve, beat_grid w/ downbeats, key, chords, segments[algorithmic id only — no human labels], energy_arc, onsets, harmonic_changes) — JSON-friendly (lists of floats/strings; **no self-similarity matrix in the output**)
- [x] 2.2 Per-feature confidence is **optional** (present only when the plugin provides one; never fabricated)
- [x] 2.3 Reserved optional enrichment fields (unpopulated): `stem_energies`, `mood`, `track_id`/`genre`, `lyrics`

## 3. Extractors (required; pinned to known output shapes)

- [x] 3.1 `extractors/vamp_host.py`: `load_audio(path)` (librosa mono), `list_plugins()`, `run(key, output, y, sr)` over the `vamp` module
- [x] 3.2 VAMP extractors → normalized features: tempo (qm-tempotracker), beats+downbeats (qm-barbeattracker), key (qm-keydetector, w/ confidence), onsets (qm-onsetdetector), segments (segmentino), chords (nnls-chroma:chordino), harmonic-change (qm-tonalchange). A required plugin that errors **raises** (surfaced, not skipped).
- [x] 3.3 `extractors/librosa_ext.py`: energy arc (per-band RMS) + spectral features (complement, not a fallback). Self-similarity, if used, stays internal — not in `SongAnalysis`.

## 4. Fusion + analyzer

- [x] 4.1 `fusion.py`: reconcile VAMP + librosa into one beat grid (VAMP beats authoritative) + section list; attach confidences only where available
- [x] 4.2 `analyzer.py`: `AudioAnalyzer.analyze(path, *, use_cache=True) -> SongAnalysis`; run the required-plugin check first (fail fast if missing)
- [x] 4.3 Content-hash caching to `data/analyses/<hash>.json` (+ analyzer-version tag for invalidation)

## 5. MCP tools (lazy — don't bloat the base server)

- [x] 5.1 `xl_analyze_song(path)` and `xl_list_vamp_plugins()` **lazy-import** the audio module; if the `[audio]` extra isn't installed, return a clear "audio extra not installed" error
- [x] 5.2 Declare the `xlights-core[audio]` extra on `xlights-mcp` so audio tools work when installed; the read/write/preset tools never pull the audio stack

## 6. Tests & verification

- [x] 6.1 Unit: schema validity incl. absent enrichment fields + absent confidence; cache hit/miss by content hash (no live deps)
- [x] 6.2 Unit: required-plugin check raises a clear, named error when a required plugin is reported missing (stubbed `list_plugins`)
- [x] 6.3 Integration over a real show `.mp3`: plausible tempo, non-empty ordered beat grid with downbeats, ≥1 section, populated energy arc; assert segments carry only algorithmic ids (no verse/chorus labels)
- [x] 6.4 Confirm a second analysis of the same file is served from cache (no recompute)
