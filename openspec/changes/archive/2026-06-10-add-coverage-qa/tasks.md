> **Build result (verified live):** `qa/coverage.py` — per-section lit-pixel sampling (3 frames, max, peak-normalized) over the rendered `.fseq` via an injected sampler (`make_lit_sampler` in pipeline/visual.py, mtime-cached renderer); only intensity ≥0.5 sections scored; sampler failure → neutral (never gates blind). `qa.evaluate(..., sampler=)` folds coverage into the objective (mean of sync/placement/coverage); legacy signature unchanged without it (hermetic fakes unaffected — run.py skips the sampler when a qa fake is injected). Refine loop saves the sequence before each evaluation so coverage sees the current render. **194 tests pass.** LIVE: scored the real show 68/100 and objectively flagged sections 4, 5, 11 (intensity 0.8–1.0, rendering 0–5% of peak) — the exact dark sections the Judge described in prose for days. The refine loop can now gate + scope-regenerate them.

## 1. Coverage metric
- [x] 1.1 `qa/coverage.py`: `evaluate(plan, sampler)` — 3 samples/section (max), peak-normalized, score only intensity ≥ 0.5, `min(1, frac/(0.6×intensity))`, error findings (metric="coverage", section_index) for <50% of expectation; (100, []) when sampler=None/no scorable sections
## 2. Wiring
- [x] 2.1 `qa.evaluate(..., sampler=None)`: objective = mean(sync, placement[, coverage]); subscores["coverage"]
- [x] 2.2 `run.py`: lazy sampler from the visual-critique paths; `_refine_loop` saves before evaluating when sampler set; thread sampler into the 3 qa_eval call sites
## 3. Tests & verification
- [x] 3.1 Fake sampler: loud section dark → low score + error finding w/ section_index; loud lit → high; quiet dark → NOT penalized; sampler=None → (100, []) and objective unchanged
- [x] 3.2 `qa.evaluate` with sampler folds coverage into objective; without → identical to before; existing tests pass
- [x] 3.3 Live: compute coverage on the current (filled) fseq + plan → sane subscore; confirm it would have flagged the dark-chorus render (dark frames → low)
