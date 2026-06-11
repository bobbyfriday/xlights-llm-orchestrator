## Context

The saved `.xsq` is XML (root children: `head, ColorPalettes, EffectDB, DisplayElements, ElementEffects`). A timing track appears in TWO places:
- `<DisplayElements>`: `<Element type="timing" name="X" visible="1" collapsed="0" active="1"/>` (the row).
- `<ElementEffects>`: `<Element type="timing" name="X"><EffectLayer><Effect label="" startTime="ms" endTime="ms"/>…</EffectLayer></Element>` (the marks).

Confirmed from the corpus: timing `<Effect>` marks carry **only** `label/startTime/endTime` — **no id**, and the corpus file has no `<nextid>` for them. So we mirror that exactly (no id/nextid bookkeeping for timing marks). We already patch `.xsq` offline in `patch_xsq_media` (ElementTree, macOS sandbox path) — reuse that pattern.

## Goals / Non-Goals

**Goals:** build Section/Beat/Bar/per-prominent-stem-Onset (+ Chords/Lyrics when present) tracks from `SongAnalysis`/the plan; inject offline; best-effort + toggleable; corpus-exact XML so xLights loads it. Hermetic tests + a live open.

**Non-Goals:** live `create_timing_track`; lyric/word EFFECTS; fixing downbeat detection; combined all-onsets track; programmatic consumption.

## Decisions

### Marks model + builders
A `TimingMark{label, start_ms, end_ms}` and a `TimingTrack{name, marks}`. Builders from `SongAnalysis` + the labeled plan sections:
- **Section** — from `st.music_brief.sections` (`LabeledSection{label,start_ms,end_ms}` — `SectionPlan` has NO label), one mark per section; fall back to index labels (`"Section 1"…`) if the brief is absent.
- **Beat** — consecutive beats become `[beat_i, beat_{i+1})` marks; `label = beat-in-bar` (`(i % beats_per_bar) + 1`).
- **Bar** — group beats into bars of `BEATS_PER_BAR` (default 4); each bar mark spans `[beat_{k*N}, beat_{(k+1)*N})`. Derived because `bar_position` is None.
- **Onset (per prominent stem)** — prominent stems = the stems whose total onset count (or share) crosses a threshold, **excluding "other"** and any combined/full-mix, capped to a small set (drums + the lead/bass); configurable list. One track each, `name="Onsets (<stem>)"`, marks `[onset_i, onset_{i+1})`, `label` = an intensity bucket (l/m/h) from the stem's local energy if available else "".
- **Chords** — only if `SongAnalysis` carries chord spans; map to marks. **Lyrics** — only if timed words exist; one mark per word.

Each consecutive-times track makes marks by pairing sorted times `t_i → t_{i+1}`, matching the corpus (marks tile, no gaps). **Clamp the last mark** to a short fixed length (`LAST_MARK_MS≈500`, or the song/section end if nearer) so a final beat/onset/chord doesn't become a giant block.

### Offline patcher
`patch_xsq_timing_tracks(xsq_path, tracks) -> bool` (sibling of `patch_xsq_media`, runs AFTER it — two sequential parse/write cycles on the same file, fine): `ET.parse` → find/create `<DisplayElements>` and `<ElementEffects>` → for each track append the display `<Element …/>` and the effects `<Element><EffectLayer><Effect …/>…</Element>` → write. Skip a track with no marks. **Atomic write:** `tree.write` to a temp path (UTF-8 + xml_declaration, mirroring `patch_xsq_media`) then `os.replace` over the original, so a mid-write failure can't corrupt the `.xsq`. **Best-effort:** wrap in try/except → log + return False, leaving the original intact.

### Wiring (finalize)
After `save_sequence` + `patch_xsq_media`, build the tracks from `st.song_analysis` + `st.show_plan.sections` and call the patcher — **best-effort, toggleable** (a `timing_tracks=True` flag / `--no-timing-tracks`). Never raises into finalize. The prominent-stem set is configurable (default drums + the top lead/bass).

## Risks / Trade-offs

- **xLights rejects the patched `.xsq`** — mitigated by mirroring the corpus XML exactly (attributes, both sections, no ids) and an offline parse round-trip in tests + a gated live open. If xLights is unhappy, the best-effort wrapper means the sequence sans tracks is still valid (we'd just have written it; use atomic replace so a half-write can't corrupt).
- **Mark tiling vs point marks** — the corpus tiles marks (end = next start). We follow that; the last mark ends at the section/song end.
- **Bars wrong if not 4/4** — default 4 is right for most; configurable. The phase starts at the first beat (no anacrusis handling — acceptable for a reference grid).
- **Onset intensity labels** — if per-onset energy isn't readily available, leave `label=""` (the corpus uses l/m/h but blank is valid). Don't block on it.
- **Clutter** — selective onset tracks (not all six, no combined) + toggleable keeps the timeline readable.

## Open Questions

- Beats-per-bar detection (vs default 4) — defer; expose as config.
- Intensity bucketing source for onset labels (per-onset RMS vs stem energy curve) — start blank/simple; refine later.
- Whether to also write a Chords track now (depends on whether `SongAnalysis` currently carries chord spans) — include if present, else skip; confirm at build time.
