## Why

You can't judge a light show without the music, can't tell which song a sequence is, and a stray open sequence currently kills the run. Today the orchestrator produces a bare **Animation** sequence (no audio) under a fixed name (`LLM_ORCH_SHOW`), and aborts with `CleanSlateRequired` if a sequence is already open. The animation-only behavior was a workaround for a media-attach hang — but we just proved that hang was a **bad path**, not media: with a valid, sandbox-accessible, no-spaces path, `newSequence(mediaFile=…)` attaches the song cleanly (~1.7s, no crash, duration matches the track). So we can finally produce a real, audio-backed, song-named show and leave it open for a human to play *with sound* and hand-edit.

## What Changes

- **Audio:** copy the song into the show folder under a sanitized no-spaces filename and create a **Media** sequence (`new_sequence(media_file=…)`) — the show plays with sound.
- **Clean-slate auto-close:** create with `force=True` to discard any open sequence instead of raising `CleanSlateRequired` — generation just works even if something is open.
- **Song-based naming:** name the sequence after the song (filename stem, spaces/punctuation → underscores), e.g. `mad russian christmas.mp3` → `mad_russian_christmas`; a CLI `--name` override remains. The fixed `LLM_ORCH_SHOW` is no longer the default.
- **Leave it open** for human critique/editing (already happens).
- **Graceful degradation:** if the song can't be copied/attached, fall back to an audio-less Animation sequence and warn — never break the run.

**Non-goals:** the learn-from-human-edits diff loop (next change — diff the human's saved `.xsq` against the generated baseline → learnings); audio transcoding/normalization (plain copy); effect-generation/quality changes (e.g. the dark-section problem); MCP changes.

## Capabilities

### Modified Capabilities
- `show-orchestration`: the generated sequence now includes the song's audio (a Media sequence that plays with sound), is named after the song (with a manual override), and replaces any already-open sequence instead of aborting — with a graceful fall back to an audio-less sequence if the audio can't be attached.

## Impact

- **`xlights-orchestrator`**: `effect_emitter.apply_instructions` gains an optional `media_file` and uses `force=True` (no more `CleanSlateRequired` on the orchestrator path); `pipeline/run.py` derives the sanitized name + copies the song into the show folder + threads `media_file`; `cli.py` `--name` override (replacing the fixed `--save` default).
- **`xlights-core`**: no change — `client.new_sequence` already supports `media_file` + `force` (verified live).
- **Builds on** `show-orchestration` (apply/render) and the sandbox/media findings in memory `xlights-automation-quirks`. Unblocks the human-in-the-loop editing workflow.
