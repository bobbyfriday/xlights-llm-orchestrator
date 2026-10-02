## ADDED Requirements

### Requirement: A deterministic phrase-gesture layer
Sections realized with the `full` or `pulse` treatment SHALL receive one bounded phrase-class gesture (rotating among Morph, Curtain, and Fill) spanning approximately 4 bars on the hero or a broad group — rhymed across recurring section identities the same way the cell-fabric carrier is — while withholding treatments (`feature`, `gesture`, `rest`) receive none. The chosen effect SHALL respect the catalog energy bands, and the gesture SHALL be skipped in short or quiet sections rather than force-placed. (Corpus grounding: Morph is 6.2% of the community corpus and a top-3 effect in 4 of 17 shows; Curtain 2.7%; ours previously 0.7% / 0.0%.)

#### Scenario: A pulse-treatment chorus gains a gesture
- **WHEN** an energetic section resolves to the `pulse` treatment and spans at least 6 bars
- **THEN** the realized instructions include exactly one phrase-class effect (Morph, Curtain, or Fill) of ~4 bars, tagged with provenance `phrase`

#### Scenario: Recurring sections rhyme
- **WHEN** two sections share a repetition label
- **THEN** both receive the same phrase-gesture effect type

#### Scenario: Withholding treatments stay withheld
- **WHEN** a section resolves to `rest`, `gesture`, or `feature`
- **THEN** no phrase gesture is placed

### Requirement: Deterministic staple shares follow the corpus
The cell-fabric carrier rotation SHALL weight SingleStrand as the dominant chase (double weight) and SHALL NOT include Garlands (community share 0.5%, ours was 1.9% from rotation alone); the fallback weave SHALL default its texture recipe to Ripple when the section's own vocabulary offers no cellable texture; and the VU Meter feature SHALL be placeable in `pulse`-treatment sections in addition to `full` (unchanged: at most one per section, intensity-gated).

#### Scenario: Carrier rotation contents
- **WHEN** carriers are assigned across four consecutive distinct section identities
- **THEN** SingleStrand appears twice and Garlands never

#### Scenario: Fallback texture is Ripple
- **WHEN** the LLM omits the weave and the section's effect types contain no cellable texture but non-accent target groups exist
- **THEN** the fallback weave includes a Ripple texture recipe on those groups

#### Scenario: VU in a pulse section
- **WHEN** an energetic section resolves to `pulse` and a wide group is available
- **THEN** a VU Meter instruction may be placed (subject to the existing intensity gate), where previously only `full` sections could receive one
