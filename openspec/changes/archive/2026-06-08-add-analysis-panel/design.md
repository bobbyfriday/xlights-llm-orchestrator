## Context

The first genuinely multi-agent stage. Inserts an **interpret** step between analyze and design: a parallel panel of analyst agents reads the raw `SongAnalysis` and a synthesizer fuses them into a `MusicBrief` the Director plans from.

Grounded: pydantic-ai 1.106 (`Agent`/`TestModel`/`AnthropicModelSettings`; BaseNode-Graph deprecated → plain async stages). Live runs use **Gemini** (`XLO_PROVIDER=gemini`, gemini-2.5-flash; Anthropic account has no credits). The orchestrator already has the registry, the sequential async pipeline with stage caching, Director/Generator agents, and the emitter — this change adds one stage + agents and rewires the Director's input. See [[llm-auth]].

## Goals / Non-Goals

**Goals:** parallel analyst panel → `MusicBrief`; **lyric-aware** (fetch lyric text via Genius → a Lyric & Narrative analyst); Director plans from the brief; bounded concurrency (free-tier safe); cache-resumable; panel configurable. Hermetic tests with TestModel + a mocked lyrics fetch.

**Non-Goals:** word-level lyric *timing* (forced alignment / demucs vocal-sep — ④b); rest of ④b enrichment (stems, Essentia mood, AcoustID id); critics/refine loop (⑦); checkpoints; value-curve/audio generation.

## Decisions

### `MusicBrief` contract (`music_brief.py`)
`LabeledSection{ start_ms, end_ms, label, intensity, dominant_instruments: list[str] }` (label = verse/chorus/drop… — *interpretation*; `dominant_instruments` filled **deterministically in code** from `add-stem-analysis` `section_instrumentation` by time-overlap, not by the LLM, else empty), plus `repetition_map: dict[label, list[section_index]]`, `energy_arc: list[float]` (compact), `key_mood: str`, `candidate_themes: list[str]`, `transition_points_ms: list[int]`, and **lyric-derived narrative** (optional): `narrative_summary: str | None`, `sentiment: str | None`, `featured_lines: list[str]` (the "money lines"). This is the Director's new input. (Raw `SongAnalysis` stays measurements-only; labeling happens *here*, in the agents, exactly as the audio-analysis spec intended.)

### Lyric acquisition (`lyrics.py`) — text only, graceful
`fetch_lyrics(song_path) -> LyricData | None`: read artist/title from the audio file's tags via **mutagen** (filename fallback), then **lyricsgenius** `Genius(token, timeout=…, retries=1)` `.search_song(title, artist)` → plain lyric text. Gated on `GENIUS_ACCESS_TOKEN`; **graceful** — no token / no tags / no match / network error / **timeout** → returns `None` (logged), and the panel runs without the lyric analyst. (Genius's client can hang; set an explicit timeout so a slow lookup degrades rather than stalling the run.) Cached alongside the other interpret artifacts (keyed by song hash) so we don't re-hit Genius. **Not** folded into `SongAnalysis` — that capability is deliberately offline/deterministic; lyrics are an online, optional enrichment owned by the interpret stage. Word-level *timing* (aligning text to the vocal) is **out** (④b) — we pass untimed text + the section labels so the analyst can reason about narrative arc against structure.

### Four analysts + synthesizer (PydanticAI agents, registry-routed)
Each analyst is a `pydantic_ai.Agent(output_type=<its pydantic output>, model=registry[analyst])`, worker tier; the synthesizer is planner tier (`registry[synthesizer]`). Outputs:
- **Structure & Theme** → `{labeled_sections, repetition_map, candidate_themes}` (gets segments, self-similarity-derived repetition hints, chords/energy).
- **Rhythm & Dynamics** → `{groove, energy_envelope, climax_ms, accents_ms}` (gets tempo/beats/downbeats, energy arc, onsets — **plus per-section instrument prevalence + per-stem onsets when `SongAnalysis.stems` is present** from `add-stem-analysis`; degrades to full-mix when absent).
- **Harmony & Mood** → `{emotional_arc, key_mood, palette_hint}` (gets key, chords, tonal-change).
- **Lyric & Narrative** → `{narrative_summary, sentiment, featured_lines, lyric_themes}` (gets the lyric text + the structural section labels). **Conditional** — added to the panel only when `fetch_lyrics` returned text; skipped for instrumentals / no token.
- **Synthesizer** → `MusicBrief` (gets all available analyst outputs + a tiny analysis header).
Each agent gets a **focused, compact slice** of the song data (token control) rendered by a per-analyst `render_input`. New roles `analyst`/`synthesizer` added to `models/config.yaml` per provider (Gemini: gemini-2.5-flash for both; Anthropic: sonnet analyst / opus synthesizer).

### Parallel execution with a Semaphore (the multi-agent core)
A new `agents/panel.py` runs the analysts with `asyncio.gather` under an `asyncio.Semaphore(max_concurrency)` (default small, e.g. 3 — Gemini free-tier friendly; configurable). `gather(return_exceptions=True)` so one analyst failing doesn't sink the panel — a failed analyst is dropped and the synthesizer works with the rest (logged). Then the synthesizer runs once. This is the within-stage parallelism the project plan calls for; the pipeline itself stays sequential across stages.

### New pipeline stage: interpret
`pipeline/run.py` gains an **interpret** stage between analyze and design: fetch lyrics (`lyrics = fetch_lyrics(song_path)`), assemble the analyst list (the 3 DSP analysts + the Lyric analyst iff `lyrics`), then `music_brief = await run_panel(song_analysis, lyrics, analysts, synthesizer, sem)`. Cached to `data/orchestrator/<song_key>/music_brief.json` (and `lyrics.txt`). The **design** stage switches to `director.render_input(music_brief, groups, placeable_types)` (its only caller is `run.py:70`, updated here) — Director consumes the brief, not the raw summary. `State` gains `music_brief` (and `lyrics`) fields.

**🔴 Injectability (or every existing hermetic test breaks).** `run_pipeline` must accept injected panel pieces — `run_pipeline(..., analysts=None, synthesizer=None, fetch_lyrics=fetch_lyrics_default)` — defaulting to live construction (registry agents) and overridable in tests; otherwise the interpret stage default-constructs real `Agent(...)` objects that need an API key at construction (proven in `add-orchestration-skeleton`). **The existing `tests/test_orchestrator.py` flow tests (lines 107/132/139) must be updated** to inject TestModel analysts+synthesizer (or a stub interpret), since they currently pass only `director`/`generator`.

**🔴 Wire stems in (else the signal never arrives).** `run.py:59` calls `analyze(song_path)` with no stems → `SongAnalysis.section_instrumentation` is always `None`. Add `stems: bool = True` to `run_pipeline` and call `analyze(song_path, stems=stems)` (the injected `analyze` callable in tests ignores it). Default on so the per-section instrument signal actually reaches the brief; a caller can disable for speed.

**Deterministic stem→brief merge (don't trust the LLM to copy numbers).** After the panel returns, *code* attaches each `section_instrumentation[i].dominant` to the time-overlapping `LabeledSection.dominant_instruments` — the synthesizer handles labels/themes/narrative, code carries the objective per-section instrument data. Immune to LLM transcription drift.

**Stage-cache shape drift.** Orchestrator stage caches (`show_plan.json`, now `music_brief.json`) have no version key — a stale file from an older `MusicBrief` shape would fail `model_validate_json`. Mitigate cheaply: wrap the cache read in try/except → on validation error, treat as a miss and recompute (same effect the audio layer gets from its `ANALYZER_VERSION`).

### Director input swap
`agents/director.py` gains `render_input(music_brief, groups, placeable_types)` (labeled sections + themes + energy arc + palette hints). The Director's `output_type` (ShowPlan) and the generator/emitter are untouched — this is an input change only, so `show-orchestration`'s requirements don't change.

### Configurable / collapsible panel
Panel membership is data-driven (a list of analyst specs). Collapsing to one "musicologist" = a single analyst whose output_type is the full MusicBrief (synthesizer becomes identity). Controlled by config (e.g. `panel: full | single`). Default full (3).

### Testing (hermetic)
TestModel per analyst (custom_output_args) + synthesizer; **mock `fetch_lyrics`** (no network). Assert: the panel runs analysts concurrently (a barrier/counter proves overlap), produces a MusicBrief, the Director receives it (inject a recording director), the interpret stage is cache-resumable, **with lyrics** the Lyric analyst is included and narrative lands while **without lyrics** the panel still yields a valid brief, and the **deterministic stem merge** populates `dominant_instruments` when `section_instrumentation` is present. **Also update the existing `test_orchestrator.py` flow tests** to inject the panel (they break otherwise) and add a `fetch_lyrics`-raises → degrades-to-no-lyrics test. Live (Gemini + `GENIUS_ACCESS_TOKEN`, gated) → MusicBrief whose labeled-section boundaries track the audio segments and whose narrative reflects the real lyrics.

## Risks / Trade-offs

- **Free-tier rate limits** with parallel calls → the Semaphore cap + PydanticAI's retry handle bursts; default concurrency low.
- **More tokens/cost/latency** (4 extra calls) → focused slices keep prompts small; caching makes re-runs free; panel collapsible for cheap runs.
- **Analyst disagreement** (e.g. different section boundaries) → the synthesizer de-conflicts; `gather(return_exceptions=True)` tolerates a dropped analyst.
- **Brief vs raw drift** → Director now depends on MusicBrief quality; keep labeled sections anchored to the analysis segment times so a weak analyst can't invent structure wholesale (synthesizer prompt instructs anchoring to provided segment times).
- **Wrong-song lyrics** → Genius can match the wrong track (covers, remixes, kids' medleys like "Baby Shark with Jaws Intro"). Mitigate: query from tags first, then filename; the lyric analyst is told the title/artist so it can flag an obvious mismatch; lyrics are advisory (narrative flavor), never load-bearing for placement. Word-level timing — which would expose misalignment harshly — is out of scope here.
- **External-service/token risk (Genius)** → optional + cached + graceful; never a hard dependency.

## Open Questions

- Exact slicing per analyst (how much of chords/energy each needs) — tune during build against a real song.
- Whether the synthesizer should hard-anchor section times to the audio segments or allow re-segmentation — default: anchor to provided segments, relabel only. Revisit if too rigid.
