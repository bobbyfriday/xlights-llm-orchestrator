## 1. Flash pass
- [x] 1.1 `key_moment_flashes(show_plan, available_groups)`: for climax/accent/drop/hit key_moments (cap ~8), a ~150ms white `On` across up to ~24 groups at `at_ms`, full brightness via extra_settings; skip lyric-only
## 2. Wire
- [x] 2.1 Append `key_moment_flashes(...)` to the generated instructions in run.py (after sections)
## 3. Tests
- [x] 3.1 climax/accent moments → white flashes on many groups at at_ms, brief, white palette, full-bright; lyric-only → none; bounded (≤cap groups, ≤cap moments)
- [x] 3.2 no key_moments → []; existing tests pass
- [x] 3.3 Live (batched): re-gen → a visible full-display white hit at the climax
