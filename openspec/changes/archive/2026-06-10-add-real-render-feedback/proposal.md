## Why
Every visual judgment the loop makes (visual critic, coverage metric) runs on our offline dot-splat approximation — and comparing it to the user's real xLights export showed a real fidelity gap (the approximation reads brighter than the truth). The re-test proved `exportVideoPreview` is automatable on MEDIA-ATTACHED sequences (~17s, stable; the old crash was a media-less bitrate-0 null-deref). The loop can now judge the show the human actually sees.

## What Changes
- **`RealRender`**: exports the real xLights render (guarded — only when `getOpenSequence` shows attached media; never on animations), cached by the `.xsq` mtime, with the lead-in offset measured per export (video duration − song duration); serves frames/clips via ffmpeg.
- **Coverage sampler** prefers real frames; the offline renderer remains the fallback; no eyes at all → neutral (unchanged fail-safe).
- **Visual critic** watches real stills/clips when available (offline renderer still picks the brightest moments and remains the fallback).
- The refine loop refreshes the export once per evaluation (after the save), shared by both consumers.
- `client.get_open_sequence()` + `client.export_video_preview()` added properly.

**Non-goals:** exporting media-less sequences (crash — guarded); replacing the offline renderer (it's the fallback + the brightest-frame picker); driving GUI exports.

## Capabilities
### Modified Capabilities
- `show-orchestration`: visual critique and coverage QA judge the real xLights render when available, with the offline approximation as fallback — closing the fidelity gap between what the loop scores and what the human sees.
