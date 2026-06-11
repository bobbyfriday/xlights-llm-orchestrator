## ADDED Requirements

### Requirement: Evaluate a draft with deterministic checks
The system SHALL evaluate a draft sequence using deterministic checks — timing synchronization to the beat grid/sections, placement survival, and variety/coverage — producing structured findings and a numeric score, without calling xLights or an LLM. The checks SHALL distinguish **objective** metrics (timing, placement — where "more correct" is unambiguous) from **advisory** metrics (variety/coverage), and the score SHALL NOT by itself constitute a creative-quality verdict.

#### Scenario: Score a draft
- **WHEN** a draft's instructions are evaluated
- **THEN** the system returns findings and a numeric score derived purely from the instructions, analysis, and brief

#### Scenario: Off-beat transitions are flagged
- **WHEN** an effect's start/end falls outside the tolerance window around the nearest beat/section boundary
- **THEN** that transition is reported as a sync finding

#### Scenario: Objective vs advisory separation
- **WHEN** the evaluation is produced
- **THEN** timing/placement findings are marked objective and variety/coverage findings advisory, so the loop can gate only on objective regressions

### Requirement: The objective score gates only regressions, not creative quality
The system SHALL use the deterministic score solely to detect **objective regressions** between iterations (e.g. more off-beat transitions, a newly empty section, more failed placements). It SHALL NOT use the deterministic score to override the Judge's or the human's assessment of creative quality.

#### Scenario: A revision that breaks timing/placement is reverted
- **WHEN** a revision objectively worsens timing or placement beyond a margin
- **THEN** the loop reverts to the previous best instruction set

#### Scenario: Creative quality is not decided by the deterministic score
- **WHEN** a revision holds objective metrics but changes the creative character
- **THEN** whether to keep it is decided by the Judge and the human, not by the deterministic score alone

### Requirement: Judge the draft into scoped revisions
The system SHALL turn the evaluation into a verdict: a score, a prioritized list of scoped revision items (each naming the section/groups, the issue, and a suggested fix), and a decision to accept, iterate, or stop.

#### Scenario: Iterate verdict produces scoped revisions
- **WHEN** the judge decides the draft should improve
- **THEN** it returns one or more revision items each scoped to specific sections/groups

### Requirement: Refine by regenerating flagged scopes and rebuilding
The system SHALL apply revisions by regenerating only the flagged sections and rebuilding the sequence from the full instruction set — it SHALL NOT rely on removing or mutating individual placed effects.

#### Scenario: Scoped regeneration
- **WHEN** a revision targets a section
- **THEN** only that section's instructions are regenerated; unflagged sections are unchanged

#### Scenario: Rebuild, not remove
- **WHEN** the sequence is updated after a revision
- **THEN** it is rebuilt from the complete instruction list (no per-effect removal)

### Requirement: The loop is bounded and provably terminates
The system SHALL bound refinement by a hard maximum number of iterations it cannot exceed, and SHALL additionally terminate on any independent stop condition — objective no-progress (a stall over consecutive iterations), the Judge's accept/stop, or a human stop — never depending on the Judge to halt. The best-scoring result SHALL be retained.

#### Scenario: Hard iteration cap
- **WHEN** the maximum iterations is reached
- **THEN** refinement stops regardless of any other signal, and the best-scoring instruction set is used

#### Scenario: Stall stop
- **WHEN** consecutive iterations produce no objective improvement
- **THEN** refinement stops and the previous best result is kept

#### Scenario: Independent of the Judge
- **WHEN** the Judge keeps requesting iteration
- **THEN** the hard cap and stall detector still terminate the loop

### Requirement: Human checkpoints
The system SHALL support an attended mode in which it pauses at each refine decision to present the score, findings, and proposed revisions, and lets a human approve, edit or drop revisions, redirect, stop, or accept as final — the human decision overriding the Judge — with a final approval before saving. An unattended mode SHALL run to the bounded stop conditions without prompting.

#### Scenario: Human stops the loop
- **WHEN** the human chooses stop at a checkpoint
- **THEN** refinement ends and the current best sequence is finalized

#### Scenario: Human overrides the Judge
- **WHEN** the Judge says iterate but the human accepts as final
- **THEN** no further iteration occurs

#### Scenario: Unattended mode
- **WHEN** unattended mode is selected
- **THEN** refinement proceeds without prompts, bounded by the cap and stall conditions

### Requirement: Anti-oscillation
The system SHALL avoid re-flagging a change it deliberately made in a prior iteration, so refinement does not oscillate between two states.

#### Scenario: A deliberate change is not undone
- **WHEN** a section was revised for a stated reason in a prior iteration
- **THEN** the next judgment does not re-flag that same change for reversal

### Requirement: Refinement is optional and always leaves a valid sequence
The system SHALL treat refinement as opt-in; when it is off, or stops at any point, a valid rendered sequence remains.

#### Scenario: Refinement disabled
- **WHEN** refinement is not requested
- **THEN** the pipeline produces the first-draft sequence exactly as before

#### Scenario: Early stop leaves a valid sequence
- **WHEN** refinement stops (limit, no improvement, or accept)
- **THEN** a complete, rendered sequence remains in xLights
