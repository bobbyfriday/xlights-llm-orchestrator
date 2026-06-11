## Why

"What's powerful when" is only as good as the stems. The 4-stem model (vocals/drums/bass/**other**) lumps guitars, keys, strings, and orchestral content into one bucket — so for an orchestral/rock instrumental like *Mad Russian's Christmas* every section reads `other 55–72%`, which tells the song description (and the Director) almost nothing. The **6-stem model (`htdemucs_6s`)** breaks **guitar** and **piano** out of `other`, turning that flat bucket into real instrumentation. And saving the stems as mp3 lets a human actually *hear* what's driving each section.

Confirmed feasible this session: `demucs-mlx` loads `htdemucs_6s` (one-time torch→MLX weight conversion, cached) → sources `[drums, bass, other, vocals, guitar, piano]`; torch demucs is installed as a fallback; ffmpeg is present for mp3. And because `StemFeatures.stem`/`section_instrumentation.shares` are **name-keyed**, guitar/piano flow into the per-section `stem_shares` and the song description automatically — **no schema change**.

## What Changes

- **6-stem by default:** stem separation uses `htdemucs_6s` (vocals/drums/bass/other/guitar/piano) on both the MLX and torch backends, with the model **configurable** via `XLO_STEMS_MODEL` (default `htdemucs_6s`) so 4-stem stays selectable.
- **Save stems as mp3:** each separated stem is encoded to an mp3 (via ffmpeg) under a `stems/` folder in the song's analysis cache.
- **Positional fallback order fixed** for the 6-stem source order (`[drums,bass,other,vocals,guitar,piano]`); name-keyed backends are unaffected.
- **Still optional + graceful:** the existing mlx → torch → none degrade chain stays; mp3 export is best-effort and never fails the analysis.

**Non-goals:** using the stems inside xLights / as attached media; per-stem effect reactivity in generation (future); re-tuning the song-description prompts (it already consumes shares — guitar/piano just appear); any schema change.

## Capabilities

### Modified Capabilities
- `audio-analysis`: stem separation defaults to a 6-stem model (vocals/drums/bass/other/guitar/piano, configurable) and saves the separated stems as mp3 files — best-effort and still optional/graceful — so per-section instrument prevalence distinguishes guitar/piano instead of a single `other` bucket.

## Impact

- **`xlights-core`**: `audio/extractors/stems.py` (`separate()` passes `htdemucs_6s`; `_to_named` 6-stem order; a new best-effort mp3-export helper); the analyzer writes the stems under the analysis cache.
- **No schema change** — `StemFeatures`/`section_instrumentation` are name-keyed; guitar/piano propagate to `music-interpretation`'s `stem_shares` for free.
- **Builds on** `audio-analysis` (the stems extractor) and feeds `music-interpretation`'s rich song description (⑫). Weights/ffmpeg already in place. Note: 6-stem is somewhat slower than 4-stem (cached per song).
