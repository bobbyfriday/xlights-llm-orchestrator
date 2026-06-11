> **Build result (verified live):** core audio/lyrics_align.py — mlx-whisper (WhisperX is Py<3.14-only; same engine family) word-timestamps on the VOCAL stem + monotonic fuzzy line matching → 38/44 Candy Cane Lane lines timed (hook @7.5/22.6/96.2s), markers parsed when present, repeated-line chorus hints. analyzer.attach_lyrics (augment-and-resave) + run.py attaches at the ANALYSIS stage. ROOT-CAUSE FIX: the synthesizer instrumental flag reads sa.lyrics — never populated before → it discarded lyric output. LIVE RUN FIRSTS: narrative non-empty (whimsical holiday dreamscape), 4 featured lyric moments WITH timestamps, lyric-informed section boundaries (verse starts at the 7s vocal entry), Lyrics timing track (38 marks) + Onsets(vocals) in the .xsq. 224 tests.

## 1. Alignment
- [x] 1.1 `audio/lyrics_align.py`: whisperx small-model transcription of the vocal stem (word timestamps) → fuzzy-match Genius lines to the word stream → {lines:[{text,start,end}], words, sections:[{label,start}]}; markers parsed when present; repeated-line clusters → chorus hints; ALL graceful (None on any failure)
## 2. Analyzer
- [x] 2.1 analyze(): fetch lyrics text (moved/also at analysis), align on the persisted vocal stem, store sa.lyrics; `_lyrics_need_refresh` augment-and-resave for cached analyses
## 3. Interpretation
- [x] 3.1 Find+fix the integration gap (narrative empty despite lyrics): panel/synthesizer wiring
- [x] 3.2 Panel input includes timed lines + section hints; featured_lyric_moments fire with real times
## 4. Tests & verification
- [x] 4.1 Hermetic: line-matching on a synthetic transcript; marker + repeated-line hints; graceful without whisperx
- [x] 4.2 Live: align candy cane lane's vocal stem → sane line times; re-run interpret → narrative + featured moments present; Lyrics timing track in the .xsq
