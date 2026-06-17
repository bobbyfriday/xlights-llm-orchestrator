## Context

`SongAnalysis.energy_arc` (`audio/fusion.py:31,49`, via `loudness.energy_arc`) already gives a
per-frame amplitude/energy envelope for the whole track. Section structure
(`refine_segments_with_lyrics` / `cap_long_segments` in `audio/structure.py`) builds the final span
out to `duration = len(y)/sr` — the literal end of the audio file — and every downstream effect is
clamped to `section.end_ms` (`weave.py:399-424`, `beats.py:336,380`, composite `weave.py:497`).
Mood-aware fades already exist at the *cell* level (`phrasing.soft_edge_settings` emitting
`T_TEXTCTRL_Fadein/Fadeout`, applied in `weave.py:350` and `beats.py:327`), but nothing fades the
*song tail* — so the final span renders at full brightness through the music's decay and trailing
silence, then hard-cuts.

## Goals / Non-Goals

**Goals:**
- Lights stop when the music stops: no effect in the final span extends past the music's last
  non-silent moment.
- Lights fade with the music: the final span's effects dim across the trailing amplitude decline,
  mirroring a real fade-out and degrading gracefully to a short fade on abrupt endings.
- Fully deterministic, derived from `energy_arc`; reuse the existing fade keys; touch only the song
  tail.

**Non-Goals:**
- No per-section or mid-song envelope tracking (that's the broader "VU/envelope" space — out of
  scope here; this is strictly the song-end fade).
- No change to section *count* or boundaries elsewhere; no new LLM prompt or schema/CLI field.
- No re-analysis pass or new audio dependency.

## Decisions

**1. Derive two times from `energy_arc`: `music_end` and `fade_start`.**
A small deterministic helper (in `audio/structure.py` or a sibling `audio/envelope.py`) scans the
envelope's tail:
- `music_end` = the last frame whose energy exceeds a silence floor (a small fraction of the track's
  peak/robust-max, e.g. `SILENCE_FRAC` of the 95th-percentile energy), converted to seconds. If the
  track never goes quiet, `music_end == duration` (no trim — correct).
- `fade_start` = the start of the final sustained decline leading into `music_end`: walk back from
  `music_end` while energy is monotonically (within tolerance) below a "still loud" threshold, bounded
  by a max fade window (`MAX_TAIL_FADE_S`, e.g. 6s) and a min (`MIN_TAIL_FADE_S`, e.g. 0.5s). Abrupt
  endings collapse to the min window; gradual fade-outs expand toward the real decay.

*Alternative considered:* fixed last-N-seconds fade. Rejected per the product decision — it can't tell
a fade-out song from an abrupt one and mis-times both. Envelope-derived handles both with one path.

**2. Apply as a deterministic post-pass in `generate.py`, after effects are realized.**
After the per-section realization and global post-processing (so it sees the final instruction set),
a `apply_song_end_fade(instructions, music_end_ms, fade_start_ms)` pass:
- **Trim:** for every instruction whose `end_ms > music_end_ms`, set `end_ms = music_end_ms` (drop any
  instruction left with non-positive duration, respecting the existing min-duration clamp).
- **Fade:** for every instruction overlapping `[fade_start_ms, music_end_ms]`, merge a fade-out into
  its `extra_settings` via the reused `soft_edge_settings` path, with the fade-out length scaled to
  `min(effect_tail_in_region, music_end_ms - fade_start_ms)`. Fade-*in* keys are left untouched.

*Alternative considered:* clamp at the structure layer (rewrite the final segment's `end`). Rejected —
section boundaries feed the Director and timing tracks; silently shortening the section would ripple.
Keeping structure intact and trimming at realization localizes the change to the effect layer.

**3. Reuse `soft_edge_settings` rather than a new key emitter.**
The fade keys (`T_TEXTCTRL_Fadeout`, optionally a dissolve-out for wash/fill families) are exactly the
mood-fade primitive. Extend it minimally to accept an explicit fade-out length so the same code emits
both per-cell legato fades and the song-end fade. Effects that already carry a fade-out keep the
longer of the two.

## Risks / Trade-offs

- [Silence floor mis-set → trims too early or never] → Use a relative floor (fraction of robust peak),
  not an absolute dB; clamp `music_end` to `[last_section_start + MIN_SECTION_S, duration]` so a noisy
  tail can't collapse the final section to nothing. Cover with a fixture-based unit test.
- [Reverb/applause tail counted as "music"] → Acceptable: if it's audible energy, fading with it still
  reads correctly; we only need lights off once it's *below* the floor.
- [Final span has only a section-spanning bed (no woven cells)] → The post-pass operates on raw
  instructions, so the bed itself is trimmed and faded; no dependency on cell structure.
- [Cached instructions predating this pass] → The pass is idempotent and runs at realization time, so a
  re-run applies it; no migration needed.

## Open Questions

- Exact constants (`SILENCE_FRAC`, `MAX_TAIL_FADE_S`, percentile for robust-max) — pick sane defaults
  in code, tune against the Christmas Canon render during implementation; expose as module constants,
  not config.
