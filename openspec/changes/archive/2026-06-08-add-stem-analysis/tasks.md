> **Build result (verified on a real song):** schema + `stems.py` (mlx→torch→none backend, per-stem energy/onsets, per-section prevalence with silent/empty guards) + analyzer augment-and-resave + inspectable stem wavs. **60 hermetic tests pass** (10 new). Live: `demucs-mlx` separated 'Baby Shark with Jaws Intro' in ~5s (torch-free inference; one-time [convert] for weight conversion) — per-section prevalence reads the Jaws intro as drums+bass and the vocal hook section as vocals-dominant; 4 stem wavs persisted. Cached re-run 0.13s.

## 1. Deps + schema

- [x] 1.1 Add `[stems]` extra (`demucs-mlx`, default/no-torch) + `[stems-torch]` extra (`demucs`, fallback) to `xlights-core` pyproject; document `XLO_STEMS` flag + `XLO_STEMS_BACKEND`
- [x] 1.2 `audio/schema.py`: add `StemFeatures` (stem, energy_arc[], onsets[]) + `SectionInstrumentation` (segment_id, start_ms, end_ms, shares{}, dominant[]); add `stems` + `section_instrumentation` (optional) to `SongAnalysis`; remove the placeholder `stem_energies`; bump `ANALYZER_VERSION` 1→2
- [x] 1.3 Update `tests/test_audio.py:24` (drop the `stem_energies is None` assertion → assert `stems`/`section_instrumentation is None` on a no-stems analysis)

## 2. Stem separation + features

- [x] 2.1 `audio/extractors/stems.py` `separate(path, sample_rate) -> dict[str, ndarray] | None`: pluggable backend — default `demucs_mlx.Separator` (htdemucs), fallback `demucs.api.Separator` (MPS→CPU); resolve mlx→torch→none (honor `XLO_STEMS_BACKEND`). **Normalize output:** key by source name (`vocals/drums/bass/other`, not positional), each stem → numpy float32, stereo→mono (channel mean), resample to `sample_rate`. All imports guarded + try/except → `None` on missing dep / failure / timeout (logged)
- [x] 2.2 Per-stem features: RMS energy arc (same frame grid as full-mix) + `librosa.onset.onset_detect` → `StemFeatures[]`
- [x] 2.3 Per-section prevalence (pure): integrate each stem's energy over each `SongAnalysis` segment → normalized shares + dominant instrument(s) → `SectionInstrumentation[]`. **Guards:** silent window (total≈0) → `shares={}, dominant=[]` (no divide-by-zero); empty `segments` → `section_instrumentation=[]`

## 3. Analyzer integration

- [x] 3.1 `AudioAnalyzer.analyze(path, *, stems=False)` (also `XLO_STEMS=1`): run separation, persist stem wavs to `…/analyses/<hash>/stems/<name>.wav` (inspectable), attach `stems` + `section_instrumentation`; cache derived features in the analysis JSON
- [x] 3.2 **Cache/stems augment-and-resave:** on `stems=True`, if the cached analysis has `stems is None`, run only the separation/feature step, attach, and rewrite the same cache file (never return a stale stem-less analysis to a `stems=True` caller); `stems=False` returns cache as-is. Cache key unchanged (path+version) — VAMP/librosa core not recomputed
- [x] 3.3 Confirm `stems=False` leaves the existing analysis byte-for-byte unchanged (core path untouched)

## 4. Tests & verification

- [x] 4.1 Pure: per-section prevalence from synthetic per-stem energy arrays (drums-dominant vs vocal-dominant windows) → asserts shares + dominant; **plus a silent window → `shares={}, dominant=[]`** and **empty `segments` → `section_instrumentation=[]`**
- [x] 4.2 Graceful: monkeypatch demucs import to raise → `analyze(stems=True)` returns valid `SongAnalysis` with `stems is None`; analysis still complete
- [x] 4.3 Wiring: monkeypatch the separator to return tiny synthetic stems → `StemFeatures` + `section_instrumentation` populated and stem wavs persisted to the cache dir
- [x] 4.4 **Cache/stems regression:** `analyze(stems=False)` then `analyze(stems=True)` on the same path (separator monkeypatched) → the second call yields `stems is not None` (augment-and-resave worked, not a stale cache hit)
- [x] 4.5 Slow/opt-in (`-m stems`, gated): real demucs on a short clip → 4 stems produced and cached; reused on second run
