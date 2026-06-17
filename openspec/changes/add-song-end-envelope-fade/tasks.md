## 1. Envelope analysis: derive music_end and fade_start

- [x] 1.1 Add a pure helper `song_tail_envelope(energy_arc, duration_s) -> (fade_start_s, music_end_s)` (in `audio/structure.py` or a new `audio/envelope.py`). `music_end` = last frame above a relative silence floor (`SILENCE_FRAC` × robust peak, e.g. 95th-percentile energy); `fade_start` = onset of the final sustained decline walking back from `music_end`, bounded by `[MIN_TAIL_FADE_S, MAX_TAIL_FADE_S]`. Define `SILENCE_FRAC`, `MIN_TAIL_FADE_S`, `MAX_TAIL_FADE_S` as named module constants.
- [x] 1.2 Clamp `music_end` to `[last_section_start + MIN_SECTION_S, duration_s]` so a noisy/short tail cannot collapse the final section; when the envelope never drops below the floor, return `music_end == duration_s`.
- [x] 1.3 Hermetic test on synthetic envelopes: gradual fade-out → `fade_start` at the decline onset, `music_end` before `duration`; abrupt ending → `fade_start == music_end - MIN_TAIL_FADE_S`; flat-to-end → `music_end == duration`, no trim; clamp prevents sub-`MIN_SECTION_S` final section.

## 2. Fade primitive: emit a fade-out over an explicit region

- [x] 2.1 Extend `phrasing.soft_edge_settings` (or add a sibling `tail_fade_settings(effect_type, fade_len_s) -> dict`) so the existing fade path can emit a `T_TEXTCTRL_Fadeout` (and dissolve-out for wash/fill families) scaled to an explicit fade length, not only a cell-length-derived one. Keep the legato cell path unchanged.
- [x] 2.2 Hermetic test: a line/chase effect yields `T_TEXTCTRL_Fadeout = fade_len`; a wash/fill effect yields a dissolve-out; an effect that already carries a longer fade-out keeps the longer value (merge = max).

## 3. Realization post-pass: trim + fade the song tail

- [x] 3.1 Add `apply_song_end_fade(instructions, fade_start_ms, music_end_ms) -> instructions` in `pipeline/generate.py` (or a small sibling module). Trim: any instruction with `end_ms > music_end_ms` → `end_ms = music_end_ms`; drop instructions left below the existing min-duration clamp. Fade: any instruction overlapping `[fade_start_ms, music_end_ms]` gets a fade-out (via task 2) scaled to `min(its tail in the region, music_end_ms - fade_start_ms)`, merged into `extra_settings`.
- [x] 3.2 Call `apply_song_end_fade(...)` once in `generate.py` AFTER per-section realization and global post-processing, passing ms-converted `fade_start`/`music_end` from `song_tail_envelope` on `st.song_analysis`. Confirm it runs in both the initial generate path and the refine rebuild path (so a regenerated final section is still trimmed/faded).
- [x] 3.3 Confirm idempotence: running the pass twice on the same instructions yields identical output (trim is a clamp; fade merge is max).

## 4. Hermetic tests

- [x] 4.1 Unit-test `apply_song_end_fade`: an effect ending past `music_end` is trimmed; an effect entirely before `fade_start` is untouched; an effect overlapping the region gains a scaled fade-out; an effect collapsing below min-duration is dropped.
- [x] 4.2 Extend the golden pipeline test (`tests/test_golden_pipeline.py` / `golden_instructions.json`) so the final section's instructions reflect the trim + fade-out keys; update the golden fixture intentionally.
- [x] 4.3 Run the full hermetic suite (`pytest`) and confirm no regressions in `test_weave`, `test_render_order`, `test_vu_meter`.

## 5. Live verification

- [ ] 5.1 Run `xlo run --song "mp3/christmas canon.mp3"` and confirm in xLights that the final section's effects fade out with the music and go dark at the music's end rather than holding to the file end and hard-cutting.
- [ ] 5.2 Tune `SILENCE_FRAC`, `MIN_TAIL_FADE_S`, `MAX_TAIL_FADE_S` against the live render; verify a hard-stop song (e.g. Ghostbusters) still gets a clean short fade and no premature trim.

## 6. Land

- [ ] 6.1 Note the song-end envelope fade in the relevant rendering guide if it documents tail/realization behavior.
- [ ] 6.2 Open a PR per the project workflow; do not commit to `main` directly.
