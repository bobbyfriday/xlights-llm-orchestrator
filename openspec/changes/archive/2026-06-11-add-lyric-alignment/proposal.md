## Why
Candy Cane Lane proved the gap: Genius fetches the lyrics, but they're UNTIMED text — so featured lyric moments never fire (0), the narrative stayed empty (an integration gap on top), and the synthesizer still calls a song with a sung chorus "instrumental." The original plan's design applies: align the Genius text against the demucs VOCAL STEM (WhisperX) at the ANALYSIS stage, so timing, sectioning hints, and meaning flow to everything downstream — the lyric timing track, featured moments, the panel's narrative, and the Director's lyric-driven key moments.

## What Changes
- **`audio/lyrics_align.py`** (xlights-core): WhisperX transcribes the vocal stem with word timestamps; the Genius lines are fuzzy-matched against the transcript word stream → **timed lines** (+ words), plus **section markers** (`[Verse]`/`[Chorus]`) anchored to their line times when Genius has them, and **repeated-line clusters** (chorus inference) when it doesn't.
- **Analyzer integration**: when lyrics text is fetchable, alignment runs as part of `analyze` (vocal stem already separated) → `SongAnalysis.lyrics = {lines, words, sections}`; augment-and-resave refreshes cached analyses missing timed lyrics.
- **Interpretation**: the panel receives the timed lyrics; the integration gap (narrative/featured-lines never reaching the brief) is found and fixed; featured lyric moments anchor to real times.
- Downstream freebies (already built, now fed): the Lyrics timing track, `featured_lyric_moments`, lyric-driven key moments.

**Non-goals:** singing-face/Text effects (still needs presets); phoneme-level timing; diarization.

## Capabilities
### Modified Capabilities
- `audio-analysis`: timed lyrics (lines/words + section hints) are produced at analysis time by aligning fetched lyrics against the vocal stem.
- `music-interpretation`: the interpretation consumes timed lyrics — narrative, featured lyric moments with timestamps, and lyric-informed section labels.
