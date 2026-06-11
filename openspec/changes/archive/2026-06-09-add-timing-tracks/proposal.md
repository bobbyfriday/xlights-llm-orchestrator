## Why

The finished sequence now has beat-synced effects in intentional colors — but when you open it to **critique and hand-edit**, there's no beat/bar/section grid to see or snap to. Timing tracks are exactly that grid, and they're valuable **even if nothing programmatic consumes them** — they're reference artifacts for the human in the loop.

We already have all the data (`beats`, labeled sections, per-stem onsets, chords if Chordino ran), and the user's corpus `.xsq` files **already contain the exact tracks and XML format to mirror** — Beats (labeled beat-in-bar), Bars, Sections, Chords, per-stem Onsets. So this is a focused, well-grounded addition: build those tracks from the analysis and patch them into the saved `.xsq` **offline** (like the audio patch), avoiding the live-automation modal-crash risk.

## What Changes

- A **timing-track patcher** (offline `ElementTree`, mirroring `patch_xsq_media`): inject `<Element type="timing" name="X">` into the `.xsq`'s `<DisplayElements>` (the row) and `<ElementEffects>` (the marks: `<Effect label startTime endTime/>` in an `<EffectLayer>`). No id/`nextid` bookkeeping — corpus timing marks carry none.
- Tracks built from `SongAnalysis`/the plan:
  - **Section** — labeled sections (intro/verse/chorus) at their times.
  - **Beat** — the beat grid, labeled beat-in-bar (1..N).
  - **Bar** — **derived** from the beat grid (every N beats, default 4/4), since downbeats aren't detected.
  - **Onset (per prominent stem)** — one track per prominent stem (drums + the lead/bass), **not** a combined track and **not** all six; intensity-labeled.
  - **Chords** — only if chord data exists.
  - **Lyrics** — only for vocal songs with timed words.
- Wired into **finalize** (after save / audio patch), **best-effort** (failures log and leave a valid sequence) and **toggleable**; the prominent-stem set is configurable.

**Non-goals:** live `create_timing_track` automation (offline is robust); singing-face/word-display *effects* that consume the lyric track; fixing QM downbeat detection (we derive bars); a combined all-onsets track; programmatic consumption (reference artifacts for now).

## Capabilities

### New Capabilities
- `timing-tracks`: the finished sequence includes reference timing tracks (sections, beats, bars; per-prominent-stem onsets; chords/lyrics when available), written offline and best-effort, so a human can see and snap to the song's structure when editing.

## Impact

- **`xlights-orchestrator`**: a timing-track builder + offline `.xsq` patcher (sibling to `patch_xsq_media`); a best-effort, toggleable call in the finalize step. No live-API surface.
- **Builds on** the offline `.xsq` patch pattern, the 6-stem onsets (`audio-analysis`), the labeled sections (`music-interpretation`), and the beat grid. Mirrors the corpus `.xsq` timing-track format exactly so xLights loads them cleanly.
