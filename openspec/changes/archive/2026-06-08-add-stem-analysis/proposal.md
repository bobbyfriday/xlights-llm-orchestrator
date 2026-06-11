## Why

The analysis layer currently measures the song as a single mixed signal. But *which instruments* drive a section is a strong lighting cue — a drum-driven drop wants strobes/pulses, a vocal-forward verse wants singing props and warm washes, a bass breakdown wants low-prop throb. Separating the mix into stems (vocals/drums/bass/other) and measuring each one lets us tell, **per section, which instruments are prevalent and high-energy** — a signal the interpretation panel (⑥) and generation (⑦) can use. This change adds that to the DSP layer, *before* ⑥ consumes it.

## What Changes

- **Stem separation (demucs, MLX-first):** split the mix into **vocals / drums / bass / other**, when available. Default backend is **`demucs-mlx`** (Apple-Silicon-native, runs on **MLX — no PyTorch**, ~2.6× faster than PyTorch-MPS, bit-exact parity), with the PyTorch `demucs` as an optional fallback for non-Apple platforms. Optional, feature-flagged, and **graceful** — missing dependency / model / timeout → analysis proceeds without stems.
- **Per-stem features:** for each stem, an **energy (RMS) arc** and **onset times** (so drum hits, bass pulses, vocal entries are individually visible).
- **Per-section instrument prevalence:** for each existing analysis segment, aggregate each stem's energy → **per-stem share + the dominant instrument(s)** for that section.
- **Inspectable stems:** persist the separated stem audio files to the analysis cache dir so they can be listened to / inspected.
- **Caching:** on Apple Silicon separation is fast (~3s/song via MLX, ~7s via PyTorch-MPS) but still worth caching — the separated stems and derived features are **cached by audio content hash** so re-runs skip recomputation (and CPU-only fallback is much slower).
- These extend `SongAnalysis` (the reserved `stem_energies` slot is realized as structured per-stem + per-section data); the field is **optional** (absent when stems weren't run).

**Non-goals (later):** per-stem beat/tempo tracking and full per-stem feature parity (key/chroma/segments per stem); using the stem signal inside the LLM panel/generation (that wiring lands in ⑥/⑦, which simply read the new fields when present); forced-aligned lyrics (④b).

## Capabilities

### Modified Capabilities
- `audio-analysis`: Additionally separate the mix into instrument stems and measure each (energy + onsets), then derive per-section instrument prevalence — all optional, cached, and gracefully degrading, leaving the existing measurements unchanged.

## Impact

- **`xlights-core`** `audio/` gains a `stems.py` extractor and stem/instrumentation fields on `SongAnalysis` (`audio/schema.py`); `analyzer.py` gains an optional stems pass.
- **New optional dep:** `demucs-mlx` (MLX, **no PyTorch**) behind a `[stems]` extra — base install stays light; one-time model-weight conversion on first run. PyTorch `demucs` is an optional secondary backend (non-Apple/Linux). **Off by default**, enabled per-run.
- **Latency:** ~3s/song (MLX) / ~7s (PyTorch-MPS) on Apple Silicon; one-time weight conversion on first ever run; **cached** thereafter (stems + features persisted under the analysis cache dir, keyed by audio hash).
- **Feeds** ⑥/⑦: the panel's analysts and the generator can read per-section instrument prevalence when present; this change only produces the data, it does not consume it.
- **Keeps the offline/deterministic property** of `audio-analysis`: demucs is a local model (no network at analysis time) and deterministic; it's heavy, so it's optional — distinct from the **required** VAMP plugins (core measurements).
