# The community corpus

What the effect files are mined from, as of 2026-11-02. Community-authored, hand-sequenced
`.xsq` only: no `<author>xlight-autosequencer</author>`, no xLights 2026.x (those are ours, and
carry no author tag), and byte-identical re-downloads dropped. Different people's sequences of
the same song are **distinct sequences of one song**; facts report breadth in both.

## Sequences (22; 14 songs)

| Song | Sequencer / variant | File | xLights | Effects | Spirals | Where |
|---|---|---|---|---|---|---|
| Light Of Christmas (TobyMac & Owl City) | main | `Light of Christmas.xsq` | 2022.12 | 6,382 | 440 | show folder |
| Light Of Christmas | XATW sharer A | `Light Of Christmas XATW.xsq` | 2022.21.2 | 2,289 | 241 | show folder |
| Light Of Christmas | XATW sharer B | `XATW Light Of Christmas.xsq` | 2022.21.2 | 371 | 32 | show folder |
| Light Of Christmas | Bill Jenkins | `Bill Jenkins/Light of Christmas.xsq` | 2022.21.2 | 2,617 | 58 | show folder, `Bill Jenkins/` subfolder |
| Kid On Christmas (Pentatonix) | Eliot Wisser | `XATW Kid On Christmas Eliot Wisser.xsq` | 2023.20 | 2,723 | 350 | both (identical) |
| Kid On Christmas | Jeremy Poling | `XATW Kid On Christmas Jeremy Poling.xsq` | 2023.20 | 420 | 14 | both (identical) |
| Kid On Christmas | Greg Colburn | `XATW Kid on Christmas Greg Colburn.xsq` | 2023.20 | 489 | 27 | both (identical) |
| Shut Up and Dance (Walk the Moon) | Tammy Ghee | `XATW Shut Up and Dance Tammy Ghee.xsq` | 2023.20 | 4,406 | 329 | both (identical) |
| Shut Up and Dance | Bill Jenkins | `XATW Shut Up and Dance Bill Jenkins.xsq` | 2023.20 | 1,777 | 1 | both (identical) |
| Shut Up and Dance | Jeremy Poling | `XATW Shut Up and Dance Jeremy Poling.xsq` | 2023.20 | 555 | 9 | both (identical) |
| Danger Zone (Kenny Loggins) | XATW | `Danger Zone XATW.xsq` | 2022.21.2 | 2,706 | 177 | show folder |
| Danger Zone | XATW 2 | `XATW Danger Zone 2.xsq` | 2022.21 | 450 | 18 | show folder |
| Sounding Joy (Ellie Holcomb) | XATW R2.1 | `Sounding Joy.xsq` | 2024.15 | 2,736 | 155 | `xlights around the world/XATW Sounding Joy R2.1 (1).xsqz` |
| Uptown Funk (Mark Ronson) | Updated 11.25 | `Uptown Funk (Radio Edit).xsq` | 2025.08 | 7,047 | 96 | `xlights around the world/Uptown Funk … .xsqz` |
| Magic (Lindsey Stirling) | Updated 11.25 | `Magic.xsq` | 2025.08 | 3,922 | 75 | `xlights around the world/Magic Updated 11.25-2.xsqz` |
| Believer (Imagine Dragons) | XATW R2.1 | `Believer.xsq` | 2024.15 | 6,214 | 19 | `xlights around the world/XATW Believer R2.1 (1).xsqz` |
| Candy Cane Lane (Sia) | John Storms | `Candy Cane Lane - Sia.xsq` | 2022.24 | 678 | 19 | show folder |
| Save Your Tears (The Weeknd) | AG | `The Weeknd AG - Save Your Tears HD.xsq` | 2021.32 | 2,777 | 9 | show folder |
| Away In A Manger (Carrie Underwood) | | `Carrie Underwood - Away In A Manger HD with Lyrics.xsq` | 2023.18 | 1,124 | 6 | show folder |
| Christmas Just Ain't Christmas (Idina Menzel) | | `Idina Menzel - Christmas Just Ain't Christmas.xsq` | 2020.45 | 1,547 | 4 | show folder |
| Baby Shark (Pinkfong) | John Storms | `Baby Shark with Jaws Intro - Pinkfong.xsq` | 2023.20 | 260 | 3 | show folder |
| 1984 (Van Halen) | John Storms | `1984 - Van Halen.xsq` | 2022.15 | 60 | 0 | show folder |

The four `.xsqz` packages are read in place by the miner (first `.xsq` member, `__MACOSX`
ignored); nothing needs extracting. The machine-readable list is
`packages/xlights-core/src/xlights_core/knowledge/corpus_manifest.json` (paths relative to
`/Users/rob/xlights`); this page is its human register. Add a sequence to both.

## Duplicate check (2026-11-02)

- `xlights around the world/` holds 10 packages. **Six are byte-identical** to files already in
  the show folder (the three Kid On Christmas and the three Shut Up and Dance sharers): same MD5,
  same effect fingerprint. Counted once.
- The three Kid On Christmas and three Shut Up and Dance files are different people's work:
  different effect counts (420 / 489 / 2,723 and 555 / 1,777 / 4,406), different content
  fingerprints. Kept as distinct sequences of one song.
- The four Light Of Christmas files differ in content (the Bill Jenkins one, found 2026-11-02 in
  the `Bill Jenkins/` subfolder, is 2,617 effects mostly On/Ripple/Marquee). Kept, but together
  they are a third of all Spirals placements, which is why facts carry song breadth.
- Every other `.xsq` in the show folder's subfolders (`baseline-sequences/`, `Kyle Bostick…`,
  `Mark Butcher…`, `Jeremy Poling/`, `xLights ATW…`, the unzipped XATW folders) is byte-identical
  to a top-level file.
- Among our own files, `Cher-DJ_Play_a_Christmas_Song.xsq` and its `__baseline` are identical;
  both are tool-generated and excluded anyway.

## Weighting

Pooled shares are dominated by the dense sequencers (Light of Christmas, Eliot Wisser, Tammy
Ghee). Every fact in an effect file therefore carries **breadth**: the number of sequences and
songs it occurs in. A habit in one sequence is one sequencer's habit. Rob's priority list of
exemplary sequences per effect is still to come; until then Light of Christmas is the first
exemplar and breadth is the sanity check.

## Still to do

- The preset catalog is now mined from this manifest with stable look ids:
  `uv run python -m xlights_core.knowledge.xsq_extractor --manifest` keeps every id the
  committed catalog already has and appends new signatures (2026-11-02: 1,183 → 1,314 looks,
  22 sequences). `Text` and `Moving Head` entered the catalog from the 2024–2025 files and are
  excluded from the placeable types.
- Rob's per-effect priority list (`exemplary_for` in the manifest) is still to come; only Light
  of Christmas → Spirals is marked.
