## Context
The generator emits wash instructions across a section's target groups; we light them all regardless of energy. The guide wants restraint in quiet sections. `section.intensity` is normalized 0–1.
## Goals / Non-Goals
**Goals:** deterministic energy→coverage cap; preserve Director ordering; never fully dark. **Non-Goals:** silence-blackout / pre-drop blackout (#5); brightness (#2).
## Decisions
### `coverage_cap(intensity, n_groups) -> int`
`max(MIN_LIT=2, round(n_groups * (0.3 + 0.7*intensity)))` — quiet ≈ 30% of groups, loud = all, floor 2.
### `trim_coverage(instructions, intensity) -> list`
Distinct targets in first-seen (Director-priority) order; keep the first `cap`; drop instructions on the rest. Applied to the generator's wash instructions BEFORE the palette/brightness passes, at both generate sites. Beat/hero accents are added after and not trimmed (they're the rhythm, not the bed).
## Risks / Trade-offs
- **Fighting the LLM** — a cap only trims when the section lit more groups than energy warrants; the floor keeps it non-empty. The guide-injected Director should already restrain; this guarantees it.
- **Which groups to drop** — keep first-seen (Director put important ones first); good enough.
## Open Questions
- The 0.3/0.7 curve + floor — tune in the live re-gen.
