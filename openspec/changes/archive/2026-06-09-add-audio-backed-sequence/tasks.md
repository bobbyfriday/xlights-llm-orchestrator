> **REVISED:** audio is attached by patching the `.xsq` OFFLINE (not `newSequence(mediaFile)`, which crashes first-time via `LoadAudioData`). Generate an Animation via automation, then patch the saved `.xsq` to Media + the human opens it once. The first build (media→newSequence) is superseded; the spec behavior (audio + naming + clean-slate + graceful) is unchanged.

## 1. Naming + media staging helpers

- [x] 1.1 `safe_name(song_path) -> str` (pure): filename stem, non-`[A-Za-z0-9]` runs → single `_`, strip/collapse, empty → `show` (e.g. `mad russian christmas.mp3` → `mad_russian_christmas`) — DONE
- [x] 1.2 `prepare_media(song_path, show_folder) -> Path | None`: copy the song into `<show_folder>/<safe_name><original_suffix>` (idempotent); return dest or `None` on failure — DONE

## 2. Emitter: animation-only clean-slate (NO media via automation)

- [x] 2.1 `effect_emitter.apply_instructions`: `new_sequence(..., force=True)` (clean-slate auto-close), **animation only — do NOT pass `media_file` to `new_sequence`** (that path crashes). Drop the `media_file` arg / stop using it for newSequence

## 3. Offline `.xsq` audio-patch + pipeline/CLI wiring

- [x] 3.1 `patch_xsq_media(xsq_path, media_path, duration_s)`: edit the `.xsq` `<head>` → `<sequenceType>Media`, `<mediaFile>`, `<sequenceDuration>`; best-effort (warn + leave animation intact on failure); idempotent
- [x] 3.2 `run_pipeline`: stage the song (`prepare_media`) but pass the **plain emitter** (no partial, no media to the emitter → animation). At **finalize, after `saveSequence`**: resolve the `.xsq` (sandbox container `~/Library/Containers/org.xlights/Data/<save_as>.xsq`), **close the sequence**, then `patch_xsq_media(...)`; `media is None`/patch fails → leave animation + warn
- [x] 3.3 `cli.py`: `--name` override + song-derived default (drop fixed `LLM_ORCH_SHOW`); print "open `<name>` in xLights to play with audio"

## 4. Tests & verification

- [x] 4.1 Pure `safe_name`: spaces/punctuation/unicode/multi-separators → single underscores; empty → `show`; idempotent
- [x] 4.2 Emitter: `new_sequence` called with `force=True` and **no `media_file`** (animation); auto-closes an open sequence; never raises `CleanSlateRequired`
- [x] 4.3 `prepare_media`: copies to `<show_folder>/<safe_name>.<ext>`; missing source → `None`; idempotent
- [x] 4.4 `patch_xsq_media`: a synthetic animation `.xsq` → after patch has `<sequenceType>Media` + `<mediaFile>` + `<sequenceDuration>`; malformed/missing file → no raise (graceful); idempotent on re-patch
- [x] 4.5 Pipeline: `media is None` → no patch attempted, run continues + warns; `--name` override respected
- [x] 4.6 Live (gated): `xlo run --song "mp3/mad russian christmas.mp3"` (no refine) → animation generated with effects, saved as `mad_russian_christmas`, `.xsq` patched to Media (audio ref + duration); **opening it in xLights plays with sound** (no crash)

> **Build result (verified live):** REVISED to the offline `.xsq` audio-patch (the original `newSequence(mediaFile)` crashes first-time via LoadAudioData). Emitter is now animation-only (`new_sequence(force=True)`, close-first clean-slate, no media). `prepare_media` stages the song in the show folder (no-spaces); at finalize, after save, the sequence is closed and `patch_xsq_media` rewrites the `.xsq` `<head>` → `<sequenceType>Media` + `<mediaFile>` + `<sequenceDuration>` (best-effort/graceful). `safe_name` song-naming + `--name` override. **122 hermetic tests pass** (incl. patch_xsq_media + emitter animation-only; dropped the partial/media-threading tests). LIVE: `xlo run` produced an Animation with 30 effects, saved as `mad_russian_christmas`, patched to Media — and the patched `.xsq` opens via automation in 3.8s with audio + effects, NO crash. Note: `xlo run` without `--auto` blocks on the interpret checkpoint in a non-TTY; use `--auto` for unattended.
