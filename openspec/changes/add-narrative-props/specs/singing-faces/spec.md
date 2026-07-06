## ADDED Requirements

### Requirement: Phoneme timing is extracted deterministically from aligned lyrics
The pipeline SHALL derive Papagayo-style phoneme marks deterministically from the already-aligned per-word lyric spans, mapping ARPAbet phonemes to the ten xLights mouth shapes.
`word_phonemes(word)` looks the word up in CMUdict (via `pronouncing`/`g2p-en`) and maps its ARPAbet phones through a committed `_ARPA_TO_PAPAGAYO` table to the ten mouth shapes `AI, E, etc, FV, L, MBP, O, rest, U, WQ`, falling back to `['etc']` for out-of-dictionary tokens. `phoneme_marks(lines)` distributes each word's phonemes across its aligned `[start, end]` span with vowel-class phonemes weighted about twice consonant-class ones, and inserts `rest` marks in inter-word gaps longer than `REST_GAP_MS`. The result is deterministic for in-dictionary words.

#### Scenario: Known words map to exact label sequences
- **WHEN** `word_phonemes` is called on an in-dictionary word
- **THEN** it returns the deterministic Papagayo-label sequence for that word

#### Scenario: Out-of-dictionary token falls back
- **WHEN** `word_phonemes` is called on an unpronounceable or out-of-dictionary token
- **THEN** it returns `['etc']`

#### Scenario: Marks fill the word span with rests in the gaps
- **WHEN** `phoneme_marks` runs over aligned lyric lines
- **THEN** each word's phoneme marks sum to cover its aligned span (vowel-weighted) and `rest` marks fill inter-word gaps longer than `REST_GAP_MS`

### Requirement: Phoneme-driven Faces effects are placed on singing-face props over sung regions
The pipeline SHALL place one asset-bound Faces effect per singing-face model per sung region, bound by name to the "Lyric Phonemes" timing track and to the model's real face definition, placed on top.
Sung regions are the aligned line spans merged across gaps of at most two seconds; faces close and go dark in instrumental breaks. `place_faces` emits `direct_settings = build_faces_settings(timing_track="Lyric Phonemes", face_definition=..., ...)` with `on_top=True`. During sung regions the pass gently dims concurrent `SEM_ALL`-bed instructions toward the catalog's ≤30% "singer owns focus" rule, without dimming the face prop itself. The pass fully owns Faces-type instructions (filter-and-rebuild), tagging each with its owning `section_index` so refine and `xlo regen` splices reproduce it without duplication.

#### Scenario: Faces span the sung regions
- **WHEN** a vocal song is generated on a layout with a singing-face prop that has a face definition
- **THEN** one Faces effect per prop spans exactly the sung regions (aligned line spans merged with ≤2 s gaps), bound to "Lyric Phonemes" and the model's real definition, placed on top

#### Scenario: Splice reproduces faces without duplication
- **WHEN** a section that owns a Faces instruction is regenerated via a refine splice or `xlo regen`
- **THEN** the Faces instruction is recreated exactly once

### Requirement: Singing Faces is gated on a vocal song, a defined face prop, and a scheduled track
The pass SHALL run only when a vocal song, a singing-face model carrying a verified face definition, and a scheduled phoneme timing track all hold, and SHALL no-op with a logged reason otherwise.
Gate 1: `sa.lyrics["lines"]` is non-empty with word spans. Gate 2: a model nameable as `SINGING_FACE` (name contains face/sing/carol/mouth) carries a face definition detected by `face_definitions(rgb_path)` parsing `faceInfo` in `rgbeffects.xml`; a missing definition means no Faces, ever — the reference is verified, never invented. Gate 3: the run will write the phoneme track at finalize. Instrumental songs skip at gate 1; the current face-less fixture layout skips at gate 2; every skip logs a single degradation line.

#### Scenario: Instrumental song
- **WHEN** the song has no aligned lyric lines
- **THEN** `place_faces` no-ops at gate 1 with a single degradation-log line and emits no Faces instructions

#### Scenario: No face model or definition
- **WHEN** the layout has no singing-face model, or a candidate model lacks a `faceInfo` face definition
- **THEN** `place_faces` no-ops with a degradation-log line and emits no Faces instructions

#### Scenario: Shipped fixture layout is unchanged
- **WHEN** the pipeline runs on the shipped fixture layout (no face-named prop)
- **THEN** zero Faces instructions are produced and the golden output is unchanged

### Requirement: The face prop is never choreographed and never sits under a wash
The pass SHALL keep singing-face props out of general choreography and place Faces on top, and QA SHALL exclude the face prop from coverage/variety expectations.
Singing-face props are already excluded from every SEM_ ensemble (`_NON_ENSEMBLE`); the Faces instruction adds `on_top=True` so a face never sits under a wash even if an explicit Generator instruction targets it. A placement-rules advisory is raised if any non-Faces instruction targets a SINGING_FACE model. Because timing tracks are patched offline after save, in-run renders (visual critic, coverage sampler, RealRender) do not see mouth movement; the finalized-file eyeball is the acceptance gate.

#### Scenario: Face excluded from coverage QA
- **WHEN** coverage/variety QA evaluates a section that contains a singing-face prop
- **THEN** the face prop is excluded from those expectations and does not affect the objective score

#### Scenario: Wash aimed at a face is flagged
- **WHEN** a non-Faces instruction targets a SINGING_FACE model
- **THEN** a placement-rules advisory is raised
