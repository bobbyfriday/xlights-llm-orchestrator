## ADDED Requirements

### Requirement: Recurring sections escalate
When a section recurs (per the repetition map), later occurrences SHALL be escalated relative to earlier ones (brighter and/or more props).

#### Scenario: Final chorus is biggest
- **WHEN** a label occurs multiple times
- **THEN** the last occurrence is brighter and lights at least as many props as the first

#### Scenario: Non-recurring unaffected
- **WHEN** a section does not recur
- **THEN** it receives no escalation boost
