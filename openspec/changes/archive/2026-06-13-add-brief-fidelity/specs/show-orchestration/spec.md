## ADDED Requirements

### Requirement: Deterministic rhythm layers respect the section's brief intent
The deterministic rhythm layers (the synthesized fallback weave and the beat-accent chase) SHALL
fire only where the section's creative brief opts into rhythm — it sets pulse groups, includes
rhythm-pool groups in its targets, or has intensity at/above a floor. In sections that do none of
these (deliberately quiet/still), the fallback weave SHALL NOT be synthesized and the beat-accent
chase SHALL NOT fire, so the section renders as the brief directs. The deterministic rhythm pool
SHALL NOT inject groups the brief excluded.

#### Scenario: A still section stays still
- **WHEN** a section's brief is low intensity with no pulse groups and no rhythm groups in its targets (e.g. a frosty-glow intro)
- **THEN** no fallback chase and no beat-accent pops are added, and the section shows the brief's own effects on its chosen groups (the rhythm props stay dark)

#### Scenario: An energetic section is unchanged
- **WHEN** a section is high intensity, or sets pulse groups, or targets rhythm-pool groups
- **THEN** the rhythm layers fire as before

#### Scenario: The LLM's own weave is honored
- **WHEN** the Generator emitted weave recipes for a section
- **THEN** those expand regardless of the gate; only the code-synthesized fallback is suppressed in non-rhythmic sections
