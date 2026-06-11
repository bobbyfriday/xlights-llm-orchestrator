> **Build result (verified live):** pipeline/features.py — instrument_entrances (per-stem energy-arc surge detection: ≥1.3× prior, ≥40% of stem peak, prior <45%, 20s debounce; tuned to catch sustained step-ups after the 2:07 guitar [39%→65%] was missed by from-silence-only thresholds) + instrument_feature_layer (SEM_FOCAL rides the entering stem onsets ~10s; guitar→Lightning, piano→Meteors, drums→Shockwave; quiet→Twinkle; accent colors; section_index=None survives regens). Entrances also appended to key_moments. Instructions cache now rewritten post-refine. 215 tests. LIVE: 14 entrances detected incl. guitar@124.8s; 24 Lightning hits ride its onsets on SEM_FOCAL; 96 Lightning + 44 Meteors show-wide; 1458 placed/6 skipped.

## 1. Detection
- [x] 1.1 `instrument_entrances(sa) -> [(t_ms, stem)]`: per non-"other" stem, surge = mean(next 5s) ≥ 1.5× mean(prior 10s) AND ≥ 40% of stem peak AND prior below 35% of peak; debounce ≥20s per stem
## 2. Feature layer
- [x] 2.1 `instrument_feature_layer(sa, sections, available_groups)`: per entrance → SEM_FOCAL rides the stem's onsets for ~10s (≤24 hits), stem→effect map (guitar Lightning / piano Meteors / drums Shockwave / bass On; section intensity <0.5 → Twinkle), accent color of the containing section, section_index=None (survives regen); skip without SEM_FOCAL
- [x] 2.2 Entrances appended to show_plan.key_moments (kind="entrance"); wired once after the section loop
## 3. Housekeeping
- [x] 3.1 After refine, rewrite the instructions cache from st.instructions (alongside the brief write-back)
## 4. Tests & verification
- [x] 4.1 Detector: flat→surge arc detects one entrance at the jump; already-loud stem → none; blip → none; debounce
- [x] 4.2 Layer: guitar entrance → Lightning on SEM_FOCAL at the stem's onsets within the window, capped, accent-colored; quiet section → Twinkle; no focal → []
- [x] 4.3 Live: detector finds the ~125s guitar entrance on the real analysis; re-gen → a feature rides the guitar at 2:05-2:17
