> **Build result (verified live on Gemini):** rich `SongDescription` schema (per-section musical_description/stem_shares/normalized intensity/accents + global identity/dynamic_arc/harmony/narrative_or_journey/featured_lyric_moments). DETERMINISTIC code passes (the reliable fixes): `normalize_intensities` OVERWRITES intensity → real 0.00–1.00 highs/lows (was flat 0.05–0.19); `merge_dominant_instruments` now surfaces per-section stem SHARES (drums/bass rising into choruses, not just 'other'); `featured_lyric_moments` pairs lines w/ timestamps (empty for instrumentals). Deeper synthesizer prompt + an explicit INSTRUMENTAL/no-lyrics + track-id grounding signal KILLED the hallucination (was 'Russian rap / fintech / designer brands' for instrumental TSO → now an accurate music-grounded 'cinematic wall-of-sound rock' description, no fake title/artist/narrative). `description.md` pure-render + a HARD interpret checkpoint (attended gate; --auto bypass). Interpret cache busted (music_brief→song_description). **116 hermetic tests pass** (8 new + fixed ⑪ emitter-fake fallout). Residual: a genre guess can bleed into range_note (cosmetic; track-id resolves genre).

## 1. Schema: SongDescription (richer brief)

- [x] 1.1 `music_brief.py`: extend `LabeledSection` — normalized `intensity`, `stem_shares: dict[str,float]`, `instrumentation_phrase: str`, `musical_description: str`, `accents_ms: list[int]`
- [x] 1.2 Extend `MusicBrief` — global `identity`, `dynamic_arc {climax_ms, builds[], drops[], range_note}`, `harmony_summary`, `transition_cues_ms`, `narrative_or_journey`, `featured_lyric_moments: list[{line,start_ms,end_ms,why}]` (all optional/back-compat-defaulted)

## 2. Surface + normalize from SongAnalysis

- [x] 2.1 `normalize_intensities(sections, energy_arc)`: per-section mean RMS → 0..1 via robust percentile (5th-95th) min/max; pure. Applied as a **code pass post-synthesis that OVERWRITES `sec.intensity`** (not prompt-trusted)
- [x] 2.2 Extend `merge_dominant_instruments` (existing time-overlap match) to also set `sec.stem_shares = dict(best.shares)` + synthesize `instrumentation_phrase`; omit + note when `stems` is None
- [x] 2.3 `featured_lyric_moments`: defensively parse the untyped `SongAnalysis.lyrics` dict; fuzzy-match `featured_lines` to nearest timed line → `{line,start_ms,end_ms,why}`; empty when `lyrics is None`; never raise on malformed dict
- [x] 2.4 **Bust the interpret cache:** rename the stage key `music_brief` → `song_description` so old flat briefs don't shadow the new pipeline

## 3. Rich agents + rendered description

- [x] 3.1 Deepen the analyst-panel + synthesizer prompts to demand per-section musical description, the dynamic arc, instrumentation-over-time, harmony/tension, narrative/JOURNEY (instrumental → emotional journey, no fabricated lyrics); output the structured `SongDescription`
- [x] 3.2 `render_description(brief) -> str`: pure render of the layered human-readable `description.md` (identity, structural map, dynamic arc, instrumentation, rhythm/accents, harmony, narrative, featured lyric moments); write to `data/.../<key>/description.md`

## 4. Hard review checkpoint

- [x] 4.1 `pipeline/run.py`: after interpret, an injectable **interpret checkpoint** that presents `description.md` and gates (attended → review/approve/abort; `--auto` → write + continue). On approve/edit, the (possibly corrected) description is source-of-truth downstream

## 5. Tests & verification

- [x] 5.1 `normalize_intensities`: flat raw-RMS sections → spread 0..1 (loudest≈top, quietest≈bottom, outlier doesn't flatten); **the code pass OVERWRITES a model-supplied flat intensity** → still spread
- [x] 5.2 Stem shares surfaced per section from `section_instrumentation` (not just dominant); `stems=None` → omitted + noted
- [x] 5.3 `featured_lyric_moments` pair lines with timestamps; **empty when no lyrics**; a malformed/empty `lyrics` dict does NOT raise
- [x] 5.3a **Cache-bust:** an existing `music_brief.json` does NOT shadow the new pipeline (the `song_description` stage regenerates)
- [x] 5.4 `render_description` renders all layers from a structured brief (TestModel-stubbed prose); deterministic
- [x] 5.5 Checkpoint gates: attended stub stops for review; `--auto` writes + continues; generation/refine unaffected when a description is present
- [x] 5.6 Live (gated): re-run interpret on mad russian → normalized dynamics show real highs/lows, per-section stem shares (other-dominant but drums rising in louder parts), a rich multi-section `description.md`, checkpoint pauses
