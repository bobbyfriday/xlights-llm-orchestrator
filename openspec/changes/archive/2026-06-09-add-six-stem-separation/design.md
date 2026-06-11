## Context

`audio/extractors/stems.py` runs demucs (mlx → torch → none) and computes per-stem energy + per-section shares, but uses the **4-stem** default and saves no audio. For an orchestral/rock instrumental that means a useless `other 55–72%` every section. The 6-stem `htdemucs_6s` adds **guitar** + **piano**; since `StemFeatures.stem` is a str and `section_instrumentation.shares` is `dict[str,float]`, those names flow into the song description with **no schema change**. Confirmed live: `demucs-mlx` loads `htdemucs_6s` (one-time torch→MLX conversion, cached at `~/.cache/demucs-mlx/htdemucs_6s_mlx.pkl`), torch demucs is the fallback, ffmpeg encodes mp3.

## Goals / Non-Goals

**Goals:** 6-stem by default (configurable), save stems as mp3, fix the positional source order, keep it optional/graceful. Hermetic tests.

**Non-Goals:** stems as xLights media; per-stem effect reactivity; prompt re-tuning; schema changes.

## Decisions

### Default to `htdemucs_6s`, env-overridable
A module-level `_model()` reads `XLO_STEMS_MODEL` (default `"htdemucs_6s"`). Both backends pass it: MLX `Separator(model=_model())`, torch `Separator(model=_model(), device=...)`. The one-time MLX weight conversion already ran and is cached, so subsequent loads are fast. `htdemucs` (4-stem) remains selectable via the env var. 6-stem inference is somewhat slower than 4-stem — acceptable (one run per song, cached in `data/analyses/`).

### Fix `_to_named` positional order for 6 sources
The dict path (`{name: array}`) already works for any stem set. The **positional-sequence** fallback hardcodes the 4-stem `src_order`; extend it to the 6-stem order `["drums","bass","other","vocals","guitar","piano"]` (demucs `htdemucs_6s` source order), chosen by length (4 vs 6). Name-keyed backends are unaffected.

### Save stems as mp3 — modify the EXISTING saver (it already has the path)
`analyzer.py::_persist_stems(separated, sr, key)` **already exists**: it writes each stem as a mono **WAV** to `<cache_dir>/<key>/stems/<name>.wav`. So this is not a new helper — it's a **format switch**. Change it to encode **mp3 via ffmpeg** (pipe normalized float32 PCM: `-f f32le -ar sr -ac 1 -i pipe:0 -codec:a libmp3lame -q:a 4 <dir>/<name>.mp3`), with a **wav fallback** when ffmpeg is absent (so something is always saved and hermetic CI without ffmpeg stays green). Best-effort: any error logs a warning; the analysis is unaffected. The out-dir is already known (cache_dir + key) — no threading needed.

### Re-separate when the cached stem set doesn't match the model (cache-upgrade)
`analyze()`'s augment-and-resave only re-runs separation when `analysis.stems is None`, so a song already cached with 4-stem stems would be returned as-is and never gain guitar/piano. Extend the guard: re-separate when `stems and (analysis.stems is None OR cached stems don't cover the configured model)` — e.g. `htdemucs_6s` requires `guitar`/`piano` among the cached stem names; if absent, re-run the (only) stem step and rewrite the cache. This auto-upgrades existing analyses without recomputing the whole (expensive) analysis. Cleaner than bumping the analysis cache key.

## Risks / Trade-offs

- **6-stem quality/speed:** `htdemucs_6s` is heavier and its guitar/piano split isn't perfect (some bleed), but it's strictly more informative than one `other` bucket. Configurable back to 4-stem if needed.
- **Disk:** 6 mp3s per song (a few MB each) under the analysis cache. Acceptable; prune later.
- **Weight conversion:** first-ever 6s load needs torch (installed) + downloads/converts once (done, cached); a fresh machine pays that cost once. Graceful if it fails (degrade to torch/none).
- **mp3 export coupling to ffmpeg:** already a soft dependency elsewhere (preview clips); best-effort here too.

## Open Questions

- Stem mp3 location — analysis cache (chosen) vs the show folder for easy listening; start with the cache, make it configurable if you want them in the show folder.
- Whether to also expose guitar/piano as first-class reactive channels in generation — future (Stage 2+).
