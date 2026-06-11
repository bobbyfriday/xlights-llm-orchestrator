## Why

The skeleton's Director plans straight from a compact summary of raw audio measurements. The project's vision is **multiple agents analyzing the song in parallel** — interpreting structure, rhythm, and harmony into a musical understanding before any lighting is designed. This change adds that panel: parallel analyst agents turn the `SongAnalysis` into a `MusicBrief` (labeled sections, themes, energy arc, mood, transitions), which the Director then plans from. Richer, more musical input → better shows, and it's the first genuinely multi-agent stage.

## What Changes

- New **`MusicBrief`** contract: labeled sections (intro/verse/chorus/drop — interpretation, with timing), a repetition map (recurring sections → reprise opportunities), an energy-arc summary, key/mood, candidate themes, transition points, and **lyric-derived narrative** (overall narrative/sentiment + featured "money lines").
- **Lyric acquisition (Genius):** fetch the song's lyric **text** via `lyricsgenius` (using the audio file's artist/title tags, filename fallback). Optional + graceful — no token / no match → the panel simply proceeds without lyrics.
- **Four analyst agents** (worker tier), each given a focused slice of the song data:
  - **Structure & Theme** — segments + repetition + chords/energy → labeled sections, repetition map, candidate themes.
  - **Rhythm & Dynamics** — tempo/beats/downbeats + energy + onsets → groove, energy envelope/climax, accent list.
  - **Harmony & Mood** — key + chords + tonal-change → emotional arc, color-temperature/palette hints.
  - **Lyric & Narrative** — the lyric text (+ section labels) → narrative arc, per-mood/sentiment, featured lines, lyric-driven effect hints. **Runs only when lyrics were found** (skipped for instrumentals / no token).
- A **Music Synthesizer** agent (planner tier) that fuses the analysts into one de-conflicted `MusicBrief`.
- A new **"interpret" stage** (analyze → **interpret** → design → generate → apply → render): the analysts run **concurrently** (`asyncio.gather` + a `Semaphore` cap for free-tier rate-limit safety), then the synthesizer; cached like the other stages.
- The **Director now consumes the `MusicBrief`** (labeled sections + themes + energy arc) instead of the raw analysis summary; ShowPlan and everything downstream are unchanged.
- New registry roles **`analyst`** (worker) and **`synthesizer`** (planner), routed per-provider like director/generator.
- The panel is **configurable/collapsible** — it can fall back to a single "musicologist" analyst for cheap/fast runs.

**Non-goals (later):** **word-level lyric *timing*** (forced alignment / demucs vocal-sep — heavy/GPU, ④b) — we use untimed lyric *text* here; the rest of the ④b audio enrichment (stems, Essentia mood, AcoustID id); critics + Judge + iterate/refine loop (⑦); human checkpoints; value-curve/audio-derived generation.

## Capabilities

### New Capabilities
- `music-interpretation`: Interpret a raw `SongAnalysis` (plus optionally the song's lyric text) into a `MusicBrief` via a parallel panel of analyst agents and a synthesizer, and feed that brief to the show planner — with the panel runnable in parallel, configurable in size, lyric-aware, and cache-resumable.

### Modified Capabilities
<!-- None at the spec level. The Director's *input* changes (now a MusicBrief), but
     `show-orchestration`'s requirements (produce a ShowPlan, place additively, etc.) are unchanged. -->

## Impact

- **`xlights-orchestrator`** gains `agents/analysts/` (+ synthesizer + lyric analyst), a `music_brief.py` contract, a `lyrics.py` fetcher, an `interpret` pipeline stage, and `analyst`/`synthesizer` roles in `models/config.yaml`.
- **New deps:** `lyricsgenius` (lyric text) + `mutagen` (read artist/title tags). **New token:** `GENIUS_ACCESS_TOKEN` in `.env` (optional — absent → lyric analyst is skipped). The `.env` already has the (empty) slot.
- **More LLM calls** (up to 4 analysts + 1 synthesizer + existing director/generators) — bounded by a concurrency semaphore; fine on Gemini's free tier (default provider).
- **Consumes** `audio-analysis` (SongAnalysis) and extends `show-orchestration`'s pipeline; the Director's input rendering changes (its contract/output do not).
- **Defers** only word-level lyric *timing* (forced alignment) to ④b; untimed lyric *text* + narrative interpretation land here.
