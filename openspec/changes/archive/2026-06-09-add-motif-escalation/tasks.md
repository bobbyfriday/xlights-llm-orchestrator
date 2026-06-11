## 1. Escalation level
- [x] 1.1 `escalation_level(i, repetition_map) -> float`: k/(n-1) for the k-th of n occurrences; 0 if non-recurring
## 2. Wire
- [x] 2.1 In run.py (both sites): `eff = min(1, intensity + 0.25*escalation_level(i, brief.repetition_map))`; use `eff` for `wash_brightness` + `trim_coverage`
## 3. Tests
- [x] 3.1 `escalation_level`: first occurrence 0, last 1.0, middle between; non-recurring 0; single-occurrence 0
- [x] 3.2 effective intensity boosts brightness+coverage for a later recurrence vs the first (same raw intensity); existing tests pass
- [x] 3.3 Live (batched): re-gen → a later chorus is visibly bigger/brighter than the first
