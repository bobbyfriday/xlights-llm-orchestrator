## ADDED Requirements

### Requirement: Opposite sweeps counter-phase per bar
WHEN a section's weave contains two chase-family recipes with opposite static horizontal directions on the same group set, the realization SHALL swap both directions at each bar boundary in opposite phase (the layers cross, reverse at the ends, and cross back), rather than holding statically opposed directions. An explicit alternate direction SHALL be available per recipe, phase-staggered deterministically among same-group alternating recipes. Single static-direction recipes SHALL be unaffected.

#### Scenario: Crossing chases become a woven figure
- **WHEN** a weave carries a Left-Right and a Right-Left chase recipe on the same groups
- **THEN** in bar N the layers run L→R and R→L, and in bar N+1 they run R→L and L→R, swapping at every bar boundary

#### Scenario: Explicit alternate with stagger
- **WHEN** two recipes on the same groups both specify the alternate direction
- **THEN** they flip per bar in opposite phase to each other

#### Scenario: Singles untouched
- **WHEN** a section has a single ltr recipe (no opposite partner)
- **THEN** its cells keep the static Left-Right setting exactly as today
