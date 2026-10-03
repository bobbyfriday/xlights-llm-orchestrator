## 1. Models and timing

- [ ] 1.1 `video_script.py`: `VideographerOut{logline, motifs[], beats[{section_index, title, imagery, action, camera, lighting, motifs[], continuity, draws_on}]}` (no time fields) and the resolved `VideoScript{song, constraints, logline, motifs, shots[]}`.
- [ ] 1.2 `resolve_beats(out, sections, lyrics, fps)`: spans from cached boundaries, frame counts, lyric lines attached by start time, missing sections inherit the previous beat, out-of-range indexes dropped.
- [ ] 1.3 `split_long_shots(shots, max_shot_s, downbeats_ms)` on cached `beats[].bar_position == 1`; identity when no max.
- [ ] 1.4 Tests for 1.2–1.3 per spec scenarios, including Christmas Canon's 8-plan vs 16-brief section mismatch (labels by time overlap, `repetition_map` values are start_ms).

## 2. The Videographer agent

- [ ] 2.1 `videographer` role in `models/config.yaml` (planner tier, already-priced models) + price-coverage test.
- [ ] 2.2 `agents/videographer.py`: `render_input()` built from lyrics, narrative, themes, sentiment, mood, featured lines, labeled sections with energy, climax, palette, concept; song identity from cached lyrics title/artist or filename. Test that no `look`/`motion`/`effect_types`/`target_groups` text appears in the input.
- [ ] 2.3 `agents/prompts/videographer.md`: a centerpiece film that tells this song's story; commit to motifs up front; one beat per given section with continuity; cite what each beat draws on; no timestamps; no on-screen words; harmonize with palette and energy, never depict the light display.
- [ ] 2.4 Hermetic `TestModel` test: stub output → complete `VideoScript`; invalid output → no file.

## 3. CLI and output

- [ ] 3.1 `xlo video-script --song --matrix-size WxH [--max-shot-s N] [--cache-dir]`; refuse without size or cached artifacts; never touches `pipeline/run.py`.
- [ ] 3.2 Write `video_script.json` + readable `video_script.md` to the song's cache dir; record usage under `videographer`.
- [ ] 3.3 CLI wiring tests (size parsing, refusals write nothing).

## 4. Prove it

- [ ] 4.1 ruff, mypy, pytest green with CI's fresh-resolve invocations.
- [ ] 4.2 Generate storyboards for the cached songs at 1024x768 and read them: does each tell a story specific to its song, hang together, and avoid depicting the house? Paste Christmas Canon in the PR.
- [ ] 4.3 Document in `docs/usage.md`; PR to `main` from `feat/matrix-video-script`.
