## Why

The show is only as intentional as its understanding of the song — and right now that understanding is empty, so the Director invents things. Concretely, for the instrumental Trans-Siberian Orchestra track *Mad Russian's Christmas*: the MusicBrief's per-section `intensity` is **0.05–0.19 (flat)** because it's raw RMS never normalized (the song peaks at 0.283); `dominant_instruments` is `["other"]` for **all 14 sections** because the brief keeps only the single top stem even though per-section **shares** are already computed; and there's no human-readable description. Handed flat dynamics, undifferentiated instruments, and no lyrics, the Director fabricated *"boastful trap energy / climbing status and wealth."* Garbage in → a confident, wrong creative direction → effects for a song that doesn't exist.

This is Stage 1 of setting the stage: a **deep, human-readable song description** that genuinely captures the song — structure, real dynamics, what's powerful when, harmony, narrative, and the lines worth featuring — with a **hard review checkpoint** so you confirm/correct the foundation before anything downstream. The raw material almost all exists in `SongAnalysis` (beats, bars, key, chords, onsets, harmonic-change points, stems + per-section shares, mood, timed lyrics, track id) — we **surface, normalize, and describe** it, not compute new DSP.

## What Changes

- **Fix dynamics:** per-section intensity is **normalized to the song's own range** (quietest≈0, loudest≈1); identify the climax(es), build-ups, drops, and dynamic range.
- **Instrument prevalence over time:** carry each section's **stem shares** (e.g. *other 55% / drums 30% / bass 12% / vocals 3%*) + a phrase on what's carrying it — not just the single dominant.
- **Featured lyric moments:** pair the powerful lines (hook, title drop, emotional peak) with their **start–end timestamps** + why each lands; empty/skipped for instrumentals.
- **A rich, layered, human-readable song description** (`description.md` + structured data): identity/global, structural map (per-section musical description), dynamic arc, instrumentation over time, rhythm & accents, harmony & tension, narrative/journey, featured lyric moments — excruciatingly descriptive, not a few sentences.
- **A hard review checkpoint:** the pipeline pauses for you to review/edit/approve the description before proceeding; `--auto` writes it and continues unattended.

**Non-goals:** Stage 2 creative direction (palettes / effect-types-per-group — the next change); new DSP extractors (use existing `SongAnalysis`); effect-generation/quality changes; auto-applying anything.

## Capabilities

### Modified Capabilities
- `music-interpretation`: the interpretation becomes a comprehensive, human-readable **song description** — per-section intensity normalized to the song's dynamic range, instrument prevalence over time (stem shares, not just the dominant), featured lyric lines with timestamps, and a layered prose description across structure/dynamics/instrumentation/harmony/narrative — gated by a hard human review checkpoint before downstream stages.

## Impact

- **`xlights-orchestrator`**: `music_brief.py` (richer schema — per-section shares/normalized intensity/musical description, global dynamic arc + featured lyric moments), the analyst panel + synthesizer prompts (much deeper), a `description.md` renderer, and a hard interpret-stage checkpoint in `pipeline/run.py`.
- **`xlights-core`**: none — `SongAnalysis.section_instrumentation` (shares) and timed lyrics already exist; we surface them.
- **Builds on** `music-interpretation` (the brief), `audio-analysis` (the raw features), and the human-readable/checkpoint patterns from `revision-log`/`show-refinement`. Foundation for Stage 2 (creative direction).
