> **Build result (verified live on Gemini):** lyrics (mutagen tags→Genius), `music_brief.py`, 4-analyst parallel panel (asyncio.gather+Semaphore, drops failures) + synthesizer, deterministic stem→brief merge, interpret stage (injectable, stems=True), Director consumes the MusicBrief. **67 hermetic tests pass** (incl. existing flow tests updated to inject the panel). Live run on 'Baby Shark': lyric analyst read real Genius lyrics → narrative/sentiment/featured-lines; stems → per-section dominant instruments (intro=drums+bass, outro=vocals); 12 effects placed. Graceful when no lyrics/token.

## 1. Contract + roles + deps

- [x] 1.1 `music_brief.py`: `LabeledSection` (start_ms, end_ms, label, intensity) + `MusicBrief` (sections[], repetition_map, energy_arc[], key_mood, candidate_themes[], transition_points_ms[], narrative_summary?, sentiment?, featured_lines[])
- [x] 1.2 Add `analyst` (worker) and `synthesizer` (planner) roles to `models/config.yaml` for both providers (Gemini: gemini-2.5-flash; Anthropic: sonnet/opus)
- [x] 1.3 Add deps `lyricsgenius` + `mutagen` to `xlights-orchestrator` pyproject; document `GENIUS_ACCESS_TOKEN` in `.env.example`

## 2. Lyric acquisition

- [x] 2.1 `lyrics.py` `LyricData` + `fetch_lyrics(song_path) -> LyricData | None`: read artist/title via mutagen (filename fallback) → `lyricsgenius` `Genius(token, timeout=…, retries=1)` search → text; gated on `GENIUS_ACCESS_TOKEN`; graceful (no token/tags/match/network/**timeout** → `None`, logged)

## 3. Analyst + synthesizer agents

- [x] 3.1 Per-analyst output models + prompts in `agents/analysts/prompts/` for Structure&Theme, Rhythm&Dynamics, Harmony&Mood, **Lyric&Narrative**
- [x] 3.2 `agents/analysts/<name>.py`: build agent (role `analyst`) + `render_input(...)` giving each a compact, focused slice (structure: segments/repetition/chords/energy; rhythm: tempo/beats/downbeats/energy/onsets; harmony: key/chords/tonal-change; lyric: lyric text + section labels)
- [x] 3.3 `agents/synthesizer.py`: build agent (role `synthesizer`), output_type `MusicBrief`; `render_input(analyst_outputs, analysis_header)`; prompt anchors section times to the provided audio segments (relabel, don't re-segment) and folds in lyric narrative when present

## 4. Parallel panel

- [x] 4.1 `agents/panel.py` `run_panel(song_analysis, lyrics, *, analysts, synthesizer, max_concurrency=3)`: assemble analyst list (Lyric analyst iff `lyrics`); run via `asyncio.gather` under `asyncio.Semaphore`; `return_exceptions=True` → drop a failed analyst (log), synthesize from the rest → `MusicBrief`
- [x] 4.2 Configurable/collapsible: support `panel: full | single` (single = one combined "musicologist" analyst emitting MusicBrief directly; synthesizer skipped)

## 5. Pipeline integration

- [x] 5.1 `State` gains `music_brief` + `lyrics`; insert an **interpret** stage (fetch lyrics → panel) between analyze and design in `pipeline/run.py`, cached to `…/music_brief.json` (+ `lyrics.txt`); cache read wrapped in try/except (validation error → treat as miss, recompute)
- [x] 5.2 **Injectability:** `run_pipeline(..., analysts=None, synthesizer=None, fetch_lyrics=<default>)` — default live-construct from the registry, overridable in tests (mirrors `director`/`generator`)
- [x] 5.3 **Wire stems:** add `stems: bool = True` to `run_pipeline`; call `analyze(song_path, stems=stems)` (run.py:59) so `section_instrumentation` is produced
- [x] 5.4 **Deterministic stem→brief merge:** after the panel, attach `section_instrumentation[i].dominant` to the time-overlapping `LabeledSection.dominant_instruments` in code (not via the synthesizer)
- [x] 5.5 Director: change `render_input(music_brief, groups, placeable_types)` (incl. narrative/featured lines + dominant instruments when present); update the only caller `run.py:70`; ShowPlan output unchanged

## 6. Tests & verification

- [x] 6.1 Hermetic: TestModel per analyst + synthesizer, **`fetch_lyrics` mocked** → `run_panel` returns a MusicBrief combining all analysts; assert concurrency (overlap counter) and that a raised analyst is dropped without failing the panel
- [x] 6.2 Hermetic: with lyrics present → Lyric analyst included and narrative lands in the brief; with `fetch_lyrics` → `None` → panel still yields a valid brief (no narrative); **`fetch_lyrics` raising → degrades to no-lyrics** (not a crash)
- [x] 6.3 Hermetic: full pipeline with TestModel agents (panel injected) → interpret stage produces a MusicBrief and the Director receives it (recording director); sections carry labels
- [x] 6.4 **Stem-merge flow:** a `SongAnalysis` with `section_instrumentation` populated → `MusicBrief.LabeledSection.dominant_instruments` non-empty after the pipeline (deterministic merge proven)
- [x] 6.5 **Update existing `tests/test_orchestrator.py` flow tests (107/132/139)** to inject the panel — they must still pass with the interpret stage added
- [x] 6.6 Hermetic: interpret stage is cache-resumable (second run reuses cached MusicBrief without calling analysts or Genius); stale/invalid `music_brief.json` → treated as miss
- [x] 6.7 Hermetic: collapsed panel (`single`) produces a valid MusicBrief from one analyst
- [x] 6.8 Live (gated, Gemini + `GENIUS_ACCESS_TOKEN` + xLights): `xlo run` interprets a real song → MusicBrief labeled sections track the audio segments, dominant instruments reflect the stems, narrative reflects the lyrics; full show still generates and places
