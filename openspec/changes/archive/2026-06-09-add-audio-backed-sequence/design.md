## Context

Unblocks the human-in-the-loop workflow: a real show needs the music, a recognizable name, and shouldn't abort on a stray open sequence. The hard part — media attach — is already de-risked: `client.new_sequence` supports `media_file` + `force`, and a live test proved `newSequence(mediaFile=<valid no-spaces show-folder path>)` attaches the song cleanly (~1.7s, `len` matches the track). The prior "media crashes" was a bad-path modal hang (spaces → `+` → file-not-found modal) and/or an out-of-sandbox path. See [[xlights-automation-quirks]].

## Goals / Non-Goals

**Goals:** audio-backed Media sequence; song-derived name (+ `--name` override); clean-slate auto-close via `force`; leave open; graceful fall back to Animation if audio can't attach. Hermetic tests + a live play-with-sound check.

**Non-Goals:** the learn-from-edits diff loop (next change); audio transcoding/normalization; effect-generation/quality changes; MCP.

## Decisions

### Copy the song into the show folder under a safe name (then attach that)
xLights is sandboxed — it can read its **show folder** (`getShowFolder` → `/Users/rob/xlights`) but not arbitrary paths, and spaces in a path break attachment (form-encode to `+` → file-not-found modal hang). So `run_pipeline` will: `dest = <show_folder>/<safe_name>.<ext>`; copy the song there if not already present/identical; pass `media_file=str(dest)` to the emitter. The copy is cheap and idempotent (skip if same size already there). This is the single most important decision — **never pass the raw source path** to `newSequence`.

### `safe_name(song_path) -> str`
Pure helper: take the filename stem, lowercase optional, replace any run of non-`[A-Za-z0-9]` with a single `_`, strip leading/trailing `_`, collapse repeats; empty → `show`. `mad russian christmas.mp3` → `mad_russian_christmas`. Used for both the copied media filename and the sequence name. Unit-tested for spaces/punctuation/unicode/edge cases.

### REVISED: audio via an OFFLINE `.xsq` patch, NOT `newSequence(mediaFile)`
The first build passed `media_file` to `new_sequence` — but that **crashes xLights**: `newSequence(mediaFile)` → `LoadAudioData` → a modal inside the HTTP handler → re-entrant crash (CONFIRMED via backtrace; see [[xlights-automation-quirks]]). The crash is specifically **first-time waveform generation**. So we never attach audio through automation. Instead:
1. **Generate as an Animation** via automation (`new_sequence(force=True)`, **no `media_file`**) — clean-slate, no `LoadAudioData`, no crash. Place + render + refine all run on the animation (rendering visuals needs no audio).
2. **At finalize, after `saveSequence`,** patch the saved `.xsq` **offline**: set `<sequenceType>Media`, `<mediaFile>` (the staged show-folder path), `<sequenceDuration>` in the XML (schema proven — `newSequence` wrote these correctly into the .xsq before crashing). The sequence is **closed** first so xLights releases the file and won't overwrite the patch.
3. The result is a complete `<song>.xsq` with audio + effects on disk; **the human opens it once in the GUI** (where `LoadAudioData`'s modal runs in the normal event loop → audio loads, no crash, waveform cached). After that even automation `openSequence` works.

So the emitter stays **animation-only** (no `media_file` threading, no partial) — `new_sequence(force=True)` for clean-slate. `force=True` makes the `CleanSlateRequired` branch unreachable here (class kept for other callers).

### Offline `.xsq` patch (`patch_xsq_media`)
`patch_xsq_media(xsq_path, media_path, duration_s)`: parse/edit the `<head>` — set `<sequenceType>Media`, `<mediaFile>media_path`, `<sequenceDuration>duration_s`. Resolve `xsq_path` from the sandbox container (`~/Library/Containers/org.xlights/Data/<save_as>.xsq`), else `getShowFolder`. Best-effort: on any failure leave the animation `.xsq` intact + warn (graceful). Idempotent.

### Song-based naming with `--name` override
`run_pipeline` derives `save_as = name_override or safe_name(song_path)` (default no longer the fixed `LLM_ORCH_SHOW`). CLI: replace the `--save LLM_ORCH_SHOW` default with `--name` (override) + keep `--no-save`. The saved `.xsq`/`.fseq` (sandbox container) and the cache key are unaffected (cache is keyed by song hash, not name).

### Graceful degradation
Copy/attach is best-effort: if the source song is missing or the copy fails, log a warning and create an **Animation** sequence (no `media_file`) so the run still completes. A media attach that somehow hangs is out of scope to detect mid-call, but the proven path (safe copied name) avoids the known hang; the fallback covers copy-time failures.

## Risks / Trade-offs

- **Show-folder writes** — we drop a copy of each song into `/Users/rob/xlights`. Acceptable (that's where show media lives); idempotent so no dupes. Could prune later.
- **`force=True` discards an open sequence the user was editing** — intended for the generate flow, but worth noting: running generation will replace whatever is open. That's the desired clean-slate behavior; the human-edit workflow happens *after* generation on the produced sequence.
- **Sandbox path assumptions** — `getShowFolder` is the readable location on this install; if a future install differs, the copy target follows `getShowFolder`, so it stays correct.
- **Name collisions** — two different songs sanitizing to the same name would overwrite; rare, and the `--name` override resolves it.

## Open Questions

- Whether to also strip/limit name length for very long titles — defer (xLights tolerates long names).
- Later: clean up copied media for deleted shows — out of scope.
