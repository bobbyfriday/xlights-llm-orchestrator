## Why
The closed-loop run proved the gap: the loop regenerates sections within a FIXED brief, so a defect that lives in the brief itself (Plasma assigned to a 0.95-intensity section) survives every regeneration — the Generator faithfully realizes the flawed design. Rules violations sat unchanged across 3 iterations while generation-level problems (coverage) were fixed. Design-level defects need a path back to the agent that owns the design.

## What Changes
- **Design escalation in the refine loop**: when a section's violations are design-implicated (a rules finding names an effect the brief's own `effect_types` chose) or persist after a regeneration, the loop sends the **section design back to the Director** (a section-redesigner agent: the section + the violation text + the catalog) and replaces that section's plan, then regenerates against the new design.
- **Once per section per run** (no redesign thrashing); injectable for hermetic tests like the other agents.
- The **updated brief is written back** to the design cache at finalize so subsequent runs keep the corrected design.

**Non-goals:** redesigning the whole show (section-scoped only); changing the Judge; escalating advisory-only findings.

## Capabilities
### Modified Capabilities
- `show-orchestration`: the refine loop escalates persistent or design-implicated section defects to a design-level revision (the Director re-plans the section), closing the feedback path that section regeneration alone cannot.
