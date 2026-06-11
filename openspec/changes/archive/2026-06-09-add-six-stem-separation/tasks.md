> **Build result (verified live):** stems now use `htdemucs_6s` by default (env `XLO_STEMS_MODEL`); `_to_named` 6-stem order; `stem_features`/`section_instrumentation` iterate the ACTUAL stems (latent bug the tests caught — guitar/piano were being dropped); `_persist_stems` writes mp3 via ffmpeg (wav fallback); analyze() cache-upgrade guard re-separates a cached 4-stem analysis under a 6-stem model. **122 hermetic tests pass** (6 new). LIVE: re-analyzed mad russian in 35s → 6 stems + section_instrumentation transformed (flat 'other 55–72%' → piano-led intro 44%, guitar/piano verses ~30/30, orchestral choruses) + 6 stem mp3s saved. Minor: stale 4-stem .wav files from the prior run linger alongside the new .mp3s (cosmetic; could add cleanup).

## 1. 6-stem model

- [x] 1.1 `stems.py`: `_model()` reads `XLO_STEMS_MODEL` (default `"htdemucs_6s"`); `_separate_mlx` → `Separator(model=_model())`, `_separate_torch` → `Separator(model=_model(), device=...)`
- [x] 1.2 `_to_named` positional-sequence branch: pick `src_order` by length — 6 → `["drums","bass","other","vocals","guitar","piano"]`, else the existing 4-stem order (dict/name-keyed path unchanged)

## 2. Save stems as mp3 + cache upgrade

- [x] 2.1 **Modify the existing** `analyzer.py::_persist_stems` (currently writes WAV): encode **mp3 via ffmpeg** (`-f f32le -ar sr -ac 1 -i pipe:0 -codec:a libmp3lame -q:a 4 <dir>/<name>.mp3`) per stem to `<cache_dir>/<key>/stems/`; **wav fallback when ffmpeg absent**; best-effort (warn, never raise)
- [x] 2.2 **Cache-upgrade guard** in `analyze()`: re-separate when `stems and (analysis.stems is None OR cached stem names don't cover the configured model)` (6s ⇒ require guitar/piano) → re-run the stem step + rewrite cache; auto-upgrades already-analyzed songs

## 3. Tests & verification

- [x] 3.1 `_to_named`: a 6-element positional sequence → `["drums","bass","other","vocals","guitar","piano"]`; a 4-element one → the 4-stem order; a name-keyed dict passes through unchanged
- [x] 3.2 `_persist_stems`: writes N stem files from synthetic arrays — mp3 when ffmpeg present, **wav fallback** when absent; never raises. **Update the existing `test_attach_stems_wiring` `.wav` assertion → `stems/drums.*`**
- [x] 3.3 `section_instrumentation` over stems including `guitar`/`piano` → shares keyed by those names (no schema change)
- [x] 3.4 `separate()` honors `XLO_STEMS_MODEL` (passes the configured model to the backend)
- [x] 3.4a **Cache-upgrade guard:** a cached 4-stem analysis under a 6-stem model re-separates (gains guitar/piano); a matching cached set is returned as-is
- [x] 3.5 Live (gated): analyze mad russian with `htdemucs_6s` → `stems/{drums,bass,other,vocals,guitar,piano}.mp3` written + `section_instrumentation` shows guitar/piano shares (not all "other"); re-interpret → the description's per-section instrumentation distinguishes guitar/piano
