## ADDED Requirements

### Requirement: Blend-value distribution is measured
The fabric statistics SHALL report the distribution of blend-mode VALUES among blended rows — at minimum the shares of `Max`, `Brightness`, the mask/reveal family, and other — identically for an instructions cache and a finalized `.xsq`, and the frozen community aggregates SHALL include the corpus-measured value shares (Brightness 0.36, mask family ≈ 0.27) so a generated show's blend vocabulary is comparable without the licensed corpus present.

#### Scenario: Value shares from an instructions cache
- **WHEN** stats are computed over instructions where some rows carry `T_CHOICE_LayerMethod` values
- **THEN** the report includes the share of each blend-value bucket among blended rows

#### Scenario: Identical measurement for .xsq
- **WHEN** the same effects are measured from a finalized `.xsq`
- **THEN** the blend-value buckets are computed from the same setting key with the same bucketing

#### Scenario: Canary guards re-inversion
- **WHEN** the hermetic golden fixture is measured after this change's defaults land
- **THEN** a loose test bound fails if blended rows return to ~all-Max
