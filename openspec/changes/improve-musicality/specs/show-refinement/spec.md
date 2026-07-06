## ADDED Requirements

### Requirement: QA measures musicality advisorially

Show QA SHALL include advisory (non-gating) musicality metrics so the Judge and the revision log can
see compositional regressions: a repetition-rhyme score (visual similarity between sections the
repetition map marks as the same material), a dynamic-range score (contrast between the quietest and
loudest sections of the show), and a focus budget (concurrent moving-effect systems per section
relative to its energy). These findings SHALL be advisory only — they inform judging and never gate
the objective score — and each metric SHALL emit a bounded number of findings with a metric name
distinguishable from existing metrics in the revision log.

#### Scenario: A non-rhyming repeat is surfaced

- **WHEN** two sections share a repetition label but are realized with different carriers or largely
  different (target, effect) sets
- **THEN** QA emits an advisory repetition-rhyme finding naming the label, and the objective score is
  unchanged by it

#### Scenario: Wall-to-wall brightness is surfaced

- **WHEN** every section of a show lights nearly the same coverage at similar brightness
- **THEN** QA emits an advisory dynamic-range finding, and a show with deliberate quiet sections does
  not receive it

### Requirement: Coverage expectations follow section energy

Rendered-coverage QA SHALL key its expectations to each section's energy and treatment: a
low-energy or rest/gesture section being sparse or near-dark is not an objective error (at most an
advisory note), while unexpected darkness in a high-energy full-treatment section remains an
objective error exactly as today.

#### Scenario: Deliberate darkness passes

- **WHEN** a rest-treatment section renders nearly dark
- **THEN** coverage QA emits no objective error for that section

#### Scenario: A broken bright section still fails

- **WHEN** a high-energy full-treatment section renders dark
- **THEN** coverage QA emits the same objective error it does today
