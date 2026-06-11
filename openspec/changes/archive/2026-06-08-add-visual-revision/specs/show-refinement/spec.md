## ADDED Requirements

### Requirement: The Judge decides revisions from the visual critique
The refine loop SHALL convert the (music-aware) visual critique into scoped revisions via the Judge's judgment: the Judge weighs the visual findings against the musical intent and produces revisions targeting the affected sections. The loop SHALL NOT apply a deterministic rule that turns a visual property (such as darkness) directly into a revision.

#### Scenario: Judge turns a confirmed visual problem into a revision
- **WHEN** the music-aware critique reports a genuine visual problem in a section and refinement iterates
- **THEN** the Judge produces a revision targeting that section and it is regenerated

#### Scenario: No deterministic dark-equals-revise rule
- **WHEN** a section renders dark but the music-aware critique judges it appropriate
- **THEN** no revision is forced for that section

### Requirement: A regenerated section receives the visual issue
The system SHALL provide the originating visual issue to the Generator when regenerating a flagged section, so the regeneration addresses what looked wrong rather than re-rolling blindly.

#### Scenario: Visual context reaches the Generator
- **WHEN** a section is regenerated because of a visual finding
- **THEN** the Generator's input for that section includes the visual issue (e.g. "dark mid-chorus — make it brighter/fuller/more dynamic")

### Requirement: Narrow backstop for critic-confirmed defects
When the music-aware critic itself confirms a section is a defect (a finding of error severity, judged in musical context) and the Judge does not produce a revision for it, the loop SHALL ensure that section is attempted or surfaced, bounded by the iteration cap and anti-oscillation ledger. The backstop SHALL trigger only on the critic's contextual error judgment, not on a raw visual property.

#### Scenario: Critic-confirmed error the Judge ignored
- **WHEN** the critic flags a section as an error in musical context and the Judge returns no revision for it
- **THEN** the loop attempts a revision for that section (or surfaces it), within the iteration cap

#### Scenario: Bounded
- **WHEN** a backstop revision does not resolve the defect
- **THEN** the loop still terminates within the cap / anti-oscillation ledger

### Requirement: Visual findings remain advisory to the objective gate
The system SHALL keep visual findings advisory to the objective revert/stall gate — acting on them (revisions, backstop) SHALL NOT add them to the objective score.

#### Scenario: Objective score excludes visual
- **WHEN** visual findings are acted upon
- **THEN** the objective score used for the revert/stall decision is unchanged by them

### Requirement: The loop re-evaluates visually after regeneration
The system SHALL re-run the visual critique on the rebuilt sequence after a revision, so the next decision reflects whether the visual problem was fixed.

#### Scenario: Re-see after fixing
- **WHEN** a section is regenerated and the sequence rebuilt
- **THEN** the next iteration's visual critique reflects the updated render of that section
