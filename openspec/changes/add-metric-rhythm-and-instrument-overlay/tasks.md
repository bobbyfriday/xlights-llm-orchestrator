## 1. Group selection + instrument routing (helpers)

- [x] 1.1 In `semantic_groups.py` (or a new `rhythm_roles.py`), add a `select_rhythm_groups(section, available_groups)` that returns the metric ring, sparkle groups, hero, bass band, and backbeat group — derived from the classified SEM_ groups, brief `pulse_groups` seeding the ring, graceful when a category is absent.
- [x] 1.2 Add `route_stems(section, sa)` returning the per-section instrument→layer routing (drums → backbone/sparkle, bass → ground, melodic-lead = top share of guitar/piano/vocals → hero). Centralized + tunable.
- [x] 1.3 Add dials to `tuning.py`: default metric ring members, sparkle top-N/top-pct, hero onset cap, bass density, backbeat drum-presence threshold.

## 2. Meter backbone (prop-family-per-beat)

- [x] 2.1 Replace the off-beat "rotating single group" + "downbeat hits all" logic with the metric ring: beat index `i` → `ring[i % len(ring)]`, discrete pulse, per-model render; downbeat (`i % bpb == 0`) gets the wider/anchor hit. Honor `beats_per_bar` from the rhythm dict.
- [x] 2.2 Preserve the per-section cap, the still-section guard (`section_is_rhythmic`), and `carrier_covers` deferral (backbone defers to a covering weave carrier).

## 3. Groove overlay

- [x] 3.1 Backbeat: on backbeat positions (4/4 → beats 2 & 4) place a distinct accent on the backbeat group, gated on drum presence.
- [x] 3.2 Sparkle: rank the drum stem's onsets by magnitude (reuse the trigger layer's `energy_at`) and place sparkle on the top-N; no drums → none.
- [x] 3.3 Hero: route the prominent melodic stem (guitar/piano/vocals) to `SEM_FOCAL` on its real onsets, magnitude-capped (replaces the current prominent-stem hero, which could be drums).
- [x] 3.4 Bass: low pulse on `SEM_BAND_GROUND` on bass onsets (sparser/longer); no bass or no ground group → none.

## 4. Phrasing modulation

- [x] 4.1 Resolve section phrasing (reuse `resolve_phrasing`) and apply to every accent gesture: legato → longer duration + `soft_edge_settings` fades + sparser (bias to stronger beats); staccato → crisp as today.

## 5. Hermetic tests

- [x] 5.1 Metric ring: consecutive beats light distinct ring groups in order; wraps for short ring / non-4/4 `bpb`; downbeat anchor is wider.
- [x] 5.2 Backbeat fires on 2 & 4 only with drums present; none without drums.
- [x] 5.3 Sparkle selects top-magnitude drum onsets (a section with a clear loud-vs-soft onset set); none without a drum stem.
- [x] 5.4 Routing: a piano/guitar-led section routes melodic lead to hero (not drums); bass → ground; missing stem/group no-ops.
- [x] 5.5 Phrasing: legato accents carry fades + longer/sparser; staccato crisp (matches pre-change shape where applicable).
- [x] 5.6 Guards preserved: still-section places nothing; `carrier_covers` defers the backbone; per-section cap holds.
- [x] 5.7 Regenerate the golden snapshot; confirm the diff is the new rhythm structure only. Full hermetic suite green.

## 6. Live verification

- [x] 6.1 Run on `dj play a christmas song.mp3` (drum-heavy): confirm the meter walks across prop families, the backbeat reads, sparkle rides the strong hits, and the groove reads as the song's rhythm. Capture objective/advisory.
- [x] 6.2 Run on `christmas canon.mp3` (piano): confirm piano routes to the hero/feature on its onsets (not the metric walk) and reads as flowing (legato), not flashing. Tune the routing/dials per the renders.

## 7. Land

- [x] 7.1 Open a PR per the project workflow; do not commit to `main` directly.
