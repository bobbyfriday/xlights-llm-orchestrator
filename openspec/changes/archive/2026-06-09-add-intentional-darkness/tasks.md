## 1. Coverage cap
- [x] 1.1 `coverage_cap(intensity, n) -> int` = `max(2, round(n*(0.3+0.7*intensity)))`
- [x] 1.2 `trim_coverage(instructions, intensity)`: keep instructions on the first `cap` distinct targets (Director order)
## 2. Wire
- [x] 2.1 Apply `trim_coverage(out.instructions, section.intensity)` before the palette/brightness passes at both generate sites
## 3. Tests
- [x] 3.1 `coverage_cap`: quiet < loud; floor 2; loud == n
- [x] 3.2 `trim_coverage`: low intensity drops groups (keeps first cap), high keeps all, never below floor; existing tests pass
- [x] 3.3 Live (batched): re-gen → quiet sections visibly light fewer props than loud ones
