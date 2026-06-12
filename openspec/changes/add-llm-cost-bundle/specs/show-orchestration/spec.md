## ADDED Requirements

### Requirement: The per-section generator is prompted with bounded guide extracts
The generator's system prompt SHALL compose deterministic, heading-sliced extracts of the guides (effects quick-reference + placement rules, the layering guide's render-style section, sequencing philosophy + rhythm sections) and SHALL stay under 15KB; the full guide corpus SHALL remain on the Director's single planning call. A section that names a cookbook scene SHALL receive ONLY that scene's recipe, inlined in its per-call input. A missing or restructured guide SHALL degrade the extract to a fallback slice or empty string, never an error.

#### Scenario: Generator prompt carries essentials, not the corpus
- **WHEN** the generator system prompt is composed with the repo's guides present
- **THEN** it contains the catalog quick-reference and placement-rules sections and the render-style guidance, and its total size is under 15KB (vs ~100KB for the full guides)

#### Scenario: A scene section gets exactly its own recipe
- **WHEN** a section plan names scene SC-01
- **THEN** the generator's input for that section includes SC-01's cookbook block and no other scene's, and a section with no scene_id gets no recipe

#### Scenario: Missing guide degrades cleanly
- **WHEN** a guide file is absent or its headings moved
- **THEN** the extract returns its fallback slice or "" and prompt composition proceeds without raising

### Requirement: The refine loop stops on a plateau
Each refine iteration SHALL compute a signature of (objective score, advisory score, the set of flagged section/issue pairs); WHEN the signature equals the previous iteration's, the loop SHALL record the iteration as a plateau and terminate before applying revisions. Regression-revert and stall handling SHALL be unchanged.

#### Scenario: Identical scores and revisions stop the loop
- **WHEN** two consecutive iterations produce the same objective and advisory scores and the judge re-flags the same sections with the same issues
- **THEN** the loop stops at the second iteration without regenerating, recording the decision as "plateau"

#### Scenario: Moving scores keep iterating
- **WHEN** the objective or advisory score (or the flagged revision set) changes between iterations
- **THEN** the loop continues under the existing cap, stall, and revert rules
