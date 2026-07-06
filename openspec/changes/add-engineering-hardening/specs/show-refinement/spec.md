## MODIFIED Requirements

### Requirement: The loop is bounded and provably terminates
The system SHALL bound refinement by a hard maximum number of iterations it cannot exceed, and SHALL additionally terminate on any independent stop condition — objective no-progress (a stall over consecutive iterations), the Judge's accept/stop, or a human stop — never depending on the Judge to halt. The best-scoring result SHALL be retained. Each termination guard SHALL be implemented as a named, individually-testable unit (the hard-iteration cap, the stall/plateau detector, the objective-regression revert, and the best-result tracker), testable in isolation from the loop body; this decomposition SHALL preserve behavior exactly, leaving the loop's observable outcomes and the golden snapshot unchanged.

#### Scenario: Hard iteration cap
- **WHEN** the maximum iterations is reached
- **THEN** refinement stops regardless of any other signal, and the best-scoring instruction set is used

#### Scenario: Stall stop
- **WHEN** consecutive iterations produce no objective improvement
- **THEN** refinement stops and the previous best result is kept

#### Scenario: Independent of the Judge
- **WHEN** the Judge keeps requesting iteration
- **THEN** the hard cap and stall detector still terminate the loop

#### Scenario: Each guard is testable in isolation
- **WHEN** a single termination guard (cap, stall/plateau, regression revert, or best tracker) is unit-tested
- **THEN** it can be exercised directly without running the whole loop, and the loop's end-to-end behavior is unchanged from before the decomposition
