## Context

Extends the `audio-analysis` DSP layer with optional stem separation, sequenced **before** ⑥ so the panel can consume per-section instrument prevalence. Default backend is **`demucs-mlx`** (Apple-Silicon-native MLX, **no PyTorch**, ~2.6× faster than PyTorch-MPS — ~3s for a 3-min track, bit-exact parity per its README); the PyTorch `demucs` is an optional fallback. Stems are still **off by default, cached, and graceful** — distinct from the **required** VAMP plugins that produce the core measurements. This change *produces* the data only; ⑥/⑦ consume it.

Grounded: the audio layer already has `AudioAnalyzer.analyze` with content-hash caching to `data/analyses/` (`XLO_CACHE_DIR`), VAMP + librosa extractors, and a `SongAnalysis` with a reserved `stem_energies` field. Platform is Apple-Silicon (no CUDA) → demucs runs on MPS or CPU. See [[preset-corpus]]/[[value-curves]] are unrelated; relevant memory is the audio analyzer's content-hash cache.

## Goals / Non-Goals

**Goals:** demucs stems (vocals/drums/bass/other); per-stem energy + onsets; per-section instrument prevalence; persisted/inspectable stems; cached by audio hash; optional + graceful; hermetic tests that don't run torch.

**Non-Goals:** per-stem beat/tempo; full per-stem feature parity (key/chroma/segments per stem); consuming the signal in the LLM panel/generation (⑥/⑦); forced-aligned lyrics (④b).

## Decisions

### Stem separation (`audio/extractors/stems.py`) — pluggable backend
A `separate(path) -> dict[str, ndarray] | None` seam with a selectable backend; both expose the same `Separator().separate_audio_file(path) -> (origin, stems)` shape, so the rest of the code is backend-agnostic:
- **Default: `demucs-mlx`** (`from demucs_mlx import Separator`; verified `Separator(model="htdemucs").separate_audio_file(path) -> (origin, {name: (2,N) float32 ndarray})`) — Apple-Silicon-native MLX, torch-free **at inference**; `htdemucs` model. **One-time caveat (verified):** the first-ever run converts htdemucs→MLX and that conversion needs `demucs-mlx[convert]` (pulls torch *once*); it caches a ~160MB MLX checkpoint to `~/.cache/demucs-mlx/`, after which inference needs no torch and a full song separates in ~5s here. Stems return stereo channels-first → `_normalize` downmixes to mono.
- **Fallback: PyTorch `demucs`** (`demucs.api.Separator`, device MPS→CPU) — for non-Apple/Linux or if the MLX port misbehaves; selected when `demucs_mlx` isn't importable or via `XLO_STEMS_BACKEND=torch`.
Backend resolved at call time (try mlx → torch → none). Separation is **blocking** → run via `asyncio.to_thread`/executor so it never stalls an event loop. **Graceful:** all imports guarded (`[stems]` extra); ImportError / model-load failure / timeout → log + return `None`. **Maturity note:** `demucs-mlx` is a community single-maintainer port — pin the version; the torch fallback is the safety net.

**Output normalization (contract).** Backends differ in dtype/shape, so `separate()` normalizes before returning: convert each stem to a **numpy float32** array, **downmix stereo→mono** (mean of channels), and **resample to `SongAnalysis.sample_rate`** so the per-stem grid matches the full-mix `energy_arc`. Index stems **by source name** (`vocals/drums/bass/other`) — never by positional order (demucs' source order is `drums,bass,other,vocals`). Expect first-ever-run **weight-conversion** chatter on stderr (MLX) — not a failure.

**Rejected alternative — spectral-band proxy.** Instead of source separation, approximate instrument prevalence from per-band spectral energy (low≈bass/kick, high≈cymbals/vocals-air) straight from the existing librosa path — no demucs. Rejected as the primary path: it can't separate vocals from other mid-band content, so "vocal-forward vs other-forward" (a key cue) is unreliable. Noted as a possible future *degraded* fallback when neither backend installs.

### Per-stem features
Reuse the librosa path (`librosa_ext`): per stem, RMS energy arc (same frame grid as the full-mix `energy_arc`) + `librosa.onset.onset_detect` (times). New schema type `StemFeatures{ stem: str, energy_arc: list[EnergyPoint], onsets: list[float] }`.

### Per-section instrument prevalence (pure, testable)
For each existing `SongAnalysis` segment `[start,end]`: integrate each stem's energy over the window, normalize across stems → **shares** summing to 1; `dominant` = the top stem (or top-k if near-tied). New type `SectionInstrumentation{ segment_id, start_ms, end_ms, shares: dict[stem,float], dominant: list[str] }`. This is the directly-useful "what drives this section" signal; it's plain math over the energy arrays → unit-testable without demucs.

**Edge guards (load-bearing):** (a) **silent window** — if the total stem energy in `[start,end]` is ≈0 (silent intro/outro), emit `shares={}, dominant=[]` rather than dividing by zero (no NaN shares). (b) **no segments** — if `SongAnalysis.segments` is empty (Segmentino returned none on a short/odd clip), `section_instrumentation` is `[]` and the per-stem `StemFeatures` are still attached. Both are covered by tests, not just convention.

### Schema additions (`audio/schema.py`)
`SongAnalysis` gains `stems: list[StemFeatures] | None` and `section_instrumentation: list[SectionInstrumentation] | None` (both `None` when stems weren't run). The reserved `stem_energies` field is realized by these (remove the placeholder). **Regression:** `tests/test_audio.py:24` asserts `sa.stem_energies is None` — update it (assert `stems`/`section_instrumentation is None` instead). `SongAnalysis` is `extra="forbid"`, so an old cached JSON carrying `stem_energies` would fail validation — **bumping `ANALYZER_VERSION` (1→2) is what makes the removal safe**: it changes the `_content_key` cache filename so stale files are never re-read. Existing measurements untouched.

### Analyzer integration + persistence
`AudioAnalyzer.analyze(path, *, stems=False)` (also honored via `XLO_STEMS=1`): after the core analysis, if `stems` → separate, persist each stem wav to `…/analyses/<hash>/stems/<name>.wav` (inspectable), compute features + instrumentation, attach to `SongAnalysis`.

**🔴 Cache/stems interaction (the bug to avoid).** Today `_content_key(path)` = `sha1(v{ANALYZER_VERSION} + file bytes)` — it has **no `stems` component**. So a naive `if cache_file.exists(): return cached` (analyzer.py:36) would return a previously-cached **stem-less** analysis to a `stems=True` caller. Fix without re-running VAMP: **augment-and-resave** — on `stems=True`, if the cached analysis is missing stems (`stems is None`), run *only* the separation/feature step, attach, and rewrite the same cache file; then return. On `stems=False`, return the cache as-is (harmless if it already carries stems). The cache key stays `path+version` (no stems suffix) so we never recompute the expensive VAMP/librosa core — only the first `stems=True` pays for separation. The core (non-stem) analysis is byte-for-byte unchanged when `stems=False`.

### Packaging / flag
`[stems]` optional-dependency extra on `xlights-core` = **`demucs-mlx`** (default; no torch); a separate `[stems-torch]` extra pulls PyTorch `demucs` for the fallback. Off by default; enabled per-run (`stems=True` / `XLO_STEMS=1` / a future `xlo --stems`); backend override via `XLO_STEMS_BACKEND`. No stems extra installed → import guard returns no stems (graceful), tests still pass.

### Testing (hermetic, no torch)
- **Pure:** per-section prevalence from synthetic per-stem energy arrays (drums-dominant window, vocal-dominant window) → assert shares + dominant.
- **Graceful:** monkeypatch the demucs import to raise → `analyze(stems=True)` returns a valid `SongAnalysis` with `stems is None`.
- **Wiring:** monkeypatch the separator to return tiny synthetic stem signals → assert `StemFeatures` + `section_instrumentation` populated and persisted to the cache dir.
- **Slow/opt-in (`-m stems`):** real demucs on a short clip → 4 stems produced; gated off normal runs.

## Risks / Trade-offs

- **Dep / latency** → `demucs-mlx` is MLX-only (no PyTorch), ~3s/song on Apple Silicon; optional extra, off by default, cached. CPU-only fallback (non-Apple) is much slower — the cache and graceful-skip cover it.
- **Community-port maturity** (`demucs-mlx`, single maintainer) → pin the version; PyTorch `demucs` fallback behind the same seam; bit-exact-parity claim reduces correctness risk but is vendor-stated, so the fallback stays.
- **Memory** (full-song separation) → htdemucs streams in segments internally; acceptable for show-length songs. If a song OOMs, the graceful path logs and skips.
- **Stem bleed** (demucs isn't perfect — vocals leak into "other", etc.) → fine for *energy/prevalence* (we want relative dominance, not clean isolation); we don't claim isolated transcription.
- **Cache size** (4 stem wavs/song) → under the analysis cache dir, keyed by hash; a future cleanup/`--no-persist-stems` can drop them. Persisting is deliberate (user wants to inspect stems).
- **ANALYZER_VERSION bump invalidates existing analysis cache** → acceptable one-time recompute; core analysis is fast (VAMP/librosa), only stems are slow and they're new.

## Open Questions

- Exact `demucs-mlx` `Separator` surface + first-run weight-conversion flow (`[convert]` extra), and whether parity holds on this Mac's chip — verify/benchmark at build; default model `htdemucs`.
- Whether to also expose stems as MCP-readable (an `xl_get_stems`/inspection tool) — defer; out of scope here.
