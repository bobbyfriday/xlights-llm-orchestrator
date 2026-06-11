> **Build result:** qa/rules.py — catalog §11 rules #2 (texture-on-linear), #3 (energy bands ±1), #4 (one feature at a time) as an objective `rules` metric folded into qa.evaluate (mean of sync/placement/rules[/coverage]); rule #7 hard caps (Strobe ≤1s, Shimmer ≤2 bars) clamped deterministically at both generate sites. The Generator stays the author — violations gate the loop and are fixed by regeneration. 199 tests pass.

## 1. Rules metric
- [x] 1.1 `qa/rules.py`: effect→energy-band table (catalog §2); linear-group detection (SEM_ARCHES/OUTLINE/CANES/ICICLES/PATH + _LTR); TEXTURE={Plasma,Fire,Liquid,Life}; FEATURES={Kaleidoscope,Shader,Shockwave,Fireworks}
- [x] 1.2 `evaluate(instructions, plan) -> (score, findings)`: affinity violations, energy-band gaps ≥2, overlapping features; section-indexed error findings; score = 100 − penalty/violation (floor 0)
- [x] 1.3 Fold into `qa.evaluate` objective (mean with sync/placement[/coverage]); subscores["rules"]
## 2. Hard caps
- [x] 2.1 Clamp pass at both generate sites: Strobe end ≤ start+1000ms; Shimmer end ≤ start + 2 bars (from tempo_overall, fallback 4000ms)
## 3. Tests & verification
- [x] 3.1 Plasma→SEM_ARCHES flagged; Strobe in 0.2-intensity section flagged; two Shockwaves overlapping flagged; clean show → 100, []
- [x] 3.2 Clamps: 10s Strobe → 1s; Shimmer → ≤2 bars; non-accent effects untouched
- [x] 3.3 qa.evaluate folds rules into objective; legacy callers unchanged; full suite passes
