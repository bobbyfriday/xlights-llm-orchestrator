## Context
`MusicBrief.repetition_map: dict[label, list[int]]` maps a label to the section indices that recur. Sections have normalized intensity. #2/#3 key brightness + coverage off intensity.
## Goals / Non-Goals
**Goals:** escalate later recurrences via an effective-intensity boost; reuse existing levers. **Non-Goals:** motif/effect reuse (LLM); beat-density escalation; identity palettes.
## Decisions
### `escalation_level(i, repetition_map) -> float`
Find the label list containing `i`; if `len>1`, level = `sorted(list).index(i)/(len-1)` (0..1); else 0.
### Effective intensity
`eff = min(1.0, intensity + ESCALATION_BOOST(0.25) * level)`; use `eff` (not raw intensity) for `wash_brightness` and `trim_coverage` at both generate sites. So the final recurrence acts up to +0.25 intensity → brighter + more props.
## Risks / Trade-offs
- **Already-max intensity** — choruses near intensity 1.0 can't escalate much via this; acceptable (they're already big). The differentiation matters most for mid-intensity recurrences.
- **Boost size** — 0.25 tune live.
## Open Questions
- Whether to also escalate beat density / add an accent layer on the final chorus — later.
