## Why

The last section's end is pinned to the **full audio-file length** (`refine_segments_with_lyrics`
in `audio/structure.py` builds the trailing span out to `duration`, the cap path likewise), and
every effect is then clamped to `section.end_ms` (`pipeline/weave.py`, `pipeline/beats.py`). So the
lights run at **full brightness through the song's trailing decay and any silent tail, then hard-cut
at the file end** — on a real render the effects visibly keep going after the music has stopped. Many
songs (Christmas Canon among them) end on a gradual fade-out; the lights should fade *with* the music,
not stay lit and then snap off.

## What Changes

- Detect the song's **trailing envelope** deterministically from the already-computed `energy_arc`:
  the point where the music's amplitude begins its final sustained decline (`fade_start`) and the
  point where it falls to effective silence (`music_end`). No LLM, no new analysis pass.
- **Stop effects when the music stops.** Effects in the final span SHALL be trimmed so they do not
  extend past `music_end` — lights go dark when the audio goes silent rather than holding to the
  file end.
- **Fade the lights with the music.** Over the trailing region (`fade_start` → `music_end`) the final
  span's effects SHALL carry an opacity fade-out so the lights dim along with the music's actual
  amplitude decay. Songs that end abruptly get a short fade at `music_end`; songs that fade out get a
  fade spanning the real decay.
- **Reuse the existing fade mechanism** — the effect-level `T_TEXTCTRL_Fadeout` keys produced by
  `phrasing.soft_edge_settings`, scaled to the trailing region — rather than inventing a new
  primitive. Scope is the song tail / final section only; earlier sections are unchanged.

## Capabilities

### New Capabilities
<!-- none — this refines existing structure + weaver realization -->

### Modified Capabilities
- `show-orchestration`: section realization gains a deterministic song-end envelope fade — the final
  span's effects are trimmed to the music's last non-silent moment and faded out across the trailing
  amplitude decline, derived in code from the energy envelope.

## Impact

- `packages/xlights-core/src/xlights_core/audio/structure.py` (or a small sibling helper): derive
  `fade_start` / `music_end` from `SongAnalysis.energy_arc`.
- `packages/xlights-orchestrator/src/xlights_orchestrator/pipeline/generate.py`: a deterministic
  post-pass that trims final-span effect ends to `music_end` and applies the trailing fade-out.
- `packages/xlights-orchestrator/src/xlights_orchestrator/pipeline/phrasing.py`: reuse / lightly
  extend `soft_edge_settings` to emit a fade-out scaled to an arbitrary region.
- Tests: a song-end-fade unit test plus golden-pipeline coverage. No schema/CLI changes; back-compat
  (a flat/abrupt envelope yields a short fade, never a regression to the old hard-cut).
