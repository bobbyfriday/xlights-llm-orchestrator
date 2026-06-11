> **Build result (verified live):** `pipeline/timing.py` — `TimingMark/TimingTrack`, builders (Section from `music_brief.sections` + index fallback; Beat labeled beat-in-bar; Bar derived every-4-beats; per-prominent-stem Onset ranked by mean ENERGY not onset count — so the demucs vocals-noise stem on an instrumental is correctly dropped; Chords/Lyrics conditional; `_tile` clamps the last mark) + `patch_xsq_timing_tracks` (offline ET into DisplayElements+ElementEffects, NO ids, ATOMIC temp+os.replace, IDEMPOTENT same-name replace, best-effort). Wired into finalize (best-effort, `--no-timing-tracks`). **155 hermetic tests pass** (8 new). LIVE on mad russian: built Sections(4)/Beats(617)/Bars(155)/Onsets(guitar,bass,drums — vocals noise dropped by energy)/Chords(193); patched the real .xsq; it re-parses valid; **xLights OPENS the patched .xsq with no error/crash** (acceptance proven). Idempotent re-patch = no dupes.

## 1. Track builders (from SongAnalysis + plan)

- [x] 1.1 `TimingMark{label,start_ms,end_ms}` + `TimingTrack{name,marks}`; a `_tile(times, end)` pairing sorted `t_i→t_{i+1}`; clamp the LAST mark to `LAST_MARK_MS≈500` (or end if nearer)
- [x] 1.2 **Section** track from `st.music_brief.sections` (LabeledSection label+ms; index-label fallback); **Beat** track (beat grid, label beat-in-bar `(i%BPB)+1`); **Bar** track (group beats by `BEATS_PER_BAR`=4, derived)
- [x] 1.3 **Onset (per prominent stem)** tracks: prominent = stems by onset count/share, EXCLUDING `other`/combined, capped to a small configurable set (drums + lead/bass); one track each `name="Onsets (<stem>)"`; intensity label l/m/h if available else ""
- [x] 1.4 **Chords** track only if chord spans exist in SongAnalysis; **Lyrics** track only if timed words exist; else skip

## 2. Offline patcher

- [x] 2.1 `patch_xsq_timing_tracks(xsq_path, tracks) -> bool` (sibling of `patch_xsq_media`): `ET.parse` → find/create `<DisplayElements>` + `<ElementEffects>` → per track append display `<Element type="timing" name visible=1 collapsed=0 active=1/>` + effects `<Element type="timing" name><EffectLayer><Effect label startTime endTime/>…</EffectLayer></Element>` (NO ids); skip empty tracks
- [x] 2.2 Best-effort + safe write: wrap in try/except (log+return False on error); write atomically (`tree.write` temp + `os.replace`) so a mid-write failure never corrupts the original `.xsq`

## 3. Wiring (finalize)

- [x] 3.1 In finalize, after `save_sequence`/`patch_xsq_media`: build tracks from `st.song_analysis` + `st.show_plan.sections`, call `patch_xsq_timing_tracks` — best-effort, never raises
- [x] 3.2 Toggleable (`timing_tracks` flag / `--no-timing-tracks`); prominent-stem set configurable

## 4. Tests & verification

- [x] 4.1 Patcher: builds correct XML — parse it back; marks have label/startTime/endTime; the track is present in BOTH `<DisplayElements>` and `<ElementEffects>`; patched `.xsq` re-parses as valid XML
- [x] 4.2 Builders from a synthetic SongAnalysis: Section labels from music_brief (index fallback when absent); Beat/Bar marks at the right times; last mark clamped; Bars = every-4-beats; Beat labels cycle 1..4; per-prominent-stem onset selection EXCLUDES near-silent stems + any combined/`other` track; marks tile (no gaps)
- [x] 4.3 Chords/Lyrics skipped when absent (instrumental → no lyric track)
- [x] 4.4 Best-effort: a patch failure (e.g. bad path) returns False and leaves the original `.xsq` intact (no corruption)
- [x] 4.5 Live (gated): finalize mad russian → open the patched `.xsq` in xLights → Beats/Bars/Sections/Onsets(drums…) tracks appear with marks at the right places; the sequence still plays
