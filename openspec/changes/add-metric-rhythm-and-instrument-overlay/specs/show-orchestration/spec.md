## MODIFIED Requirements

### Requirement: An accent on about every beat, bounded
An accent SHALL be placed on approximately every beat of a section (not heavily downsampled), with an
upper bound so a long section cannot place an unbounded number of effects. The per-beat accents SHALL
form a METER BACKBONE: each beat of the bar lights a DISTINCT rhythm group drawn in a fixed order from
a metric ring of groups (e.g. in 4/4 the four beats light four different prop-family groups in turn),
so the bar's meter is visible as a walk across the props. The ring SHALL honor the section's real
beats-per-bar (the beat index modulo the ring length selects the group), and SHALL be seeded by the
brief's pulse groups when set, else derived from the layout's rhythm groups. Each accent is a discrete
pulse on a whole group (per-model render), not a within-group buffer chase.

#### Scenario: Normal section
- **WHEN** a section has ~32 beats
- **THEN** roughly that many accents are placed (not capped to a small fraction)

#### Scenario: Each beat lights a distinct group in order
- **WHEN** consecutive beats of a bar are accented and the metric ring has at least as many groups as beats per bar
- **THEN** beat 1 lights the first ring group, beat 2 the second, and so on, so the pulse walks across distinct prop-family groups rather than all groups firing together

#### Scenario: The ring honors the meter and wraps
- **WHEN** the section's beats-per-bar differs from the ring length (a non-4/4 meter, or fewer rhythm groups than beats)
- **THEN** the beat-to-group mapping uses the beat index modulo the ring length (it wraps), and never errors for a short ring

#### Scenario: Very long section
- **WHEN** a section has far more beats than the upper bound
- **THEN** the accents are bounded to the upper limit

### Requirement: Bar starts are emphasized
Bar starts SHALL be emphasized relative to other beats, and the backbeat (the bar's weak-strong beats,
e.g. beats 2 and 4 in 4/4) SHALL carry a distinct accent on a contrasting group when the section has
percussion present, so the groove's backbeat reads in addition to the downbeat.

#### Scenario: Downbeat vs off-beat
- **WHEN** a beat is a bar start
- **THEN** it produces a larger hit (a wider/anchor accent) than an in-between beat

#### Scenario: Backbeat accent on 2 and 4
- **WHEN** a section has drums present and a beat is a backbeat position (e.g. beat 2 or 4 in 4/4)
- **THEN** a distinct accent is placed on the backbeat group at that beat

#### Scenario: No phantom backbeat without drums
- **WHEN** a section has no meaningful drum presence
- **THEN** no backbeat accent is added

### Requirement: Accent props fire on downbeats
When snowflake/spinner accent (sparkle) groups exist, they SHALL fire on the section's STRONGEST drum
hits — the drum stem's onsets ranked by onset magnitude (the stem's energy at the onset), keeping a
bounded top subset per section — rather than mechanically on every bar. When the section has no drum
stem, the sparkle layer SHALL NOT fire.

#### Scenario: Sparkle rides the strongest drum hits
- **WHEN** a section has a drum stem and sparkle props are available
- **THEN** sparkle accents are placed on the top-magnitude drum onsets (a bounded subset), not on every bar downbeat

#### Scenario: No drums, no sparkle
- **WHEN** a section has no drum stem onsets
- **THEN** no sparkle accents are placed

## ADDED Requirements

### Requirement: Instrument-mapped groove overlay
On top of the meter backbone, generation SHALL place an instrument-routed overlay: the prominent
MELODIC stem (the highest-share of guitar/piano/vocals — never drums or bass) SHALL drive the hero
focal group on its own onsets, and the bass stem SHALL drive a low pulse on the ground band on its
onsets. Each sublayer SHALL be bounded per section and SHALL no-op when its stem or its target group
is absent. The melodic lead SHALL ride its real onsets (so an arpeggiated or sustained instrument such
as piano flows on the focal prop), never the per-beat metric walk.

#### Scenario: Melodic lead drives the hero
- **WHEN** a section's prominent melodic stem (e.g. piano or guitar) has onsets and a focal group exists
- **THEN** the focal group is accented on that stem's onsets (bounded), independent of the drum-driven backbone

#### Scenario: Bass drives the ground band
- **WHEN** a section has a bass stem with onsets and a ground-band group exists
- **THEN** a low pulse is placed on the ground band on the bass onsets

#### Scenario: Missing stem or group no-ops
- **WHEN** the routed stem or its target group is absent for a section
- **THEN** that overlay sublayer places nothing and generation does not fail

### Requirement: Accent gestures are phrasing-aware
The deterministic accent gestures SHALL be modulated by the section's resolved phrasing: a LEGATO
section's accents SHALL be lengthened and soft-faded and sparsened (biased toward the stronger beats),
and a STACCATO section's accents SHALL remain crisp short pops. Phrasing SHALL resolve from the
section's directed value when set, else from its intensity (as established for the cell weaver).

#### Scenario: Legato section softens its accents
- **WHEN** a section resolves to legato
- **THEN** its beat/onset accents carry fade-in/out and longer durations and are sparser than the crisp default

#### Scenario: Staccato section stays crisp
- **WHEN** a section resolves to staccato
- **THEN** its accents are short crisp pops with no synthesized fades

### Requirement: Rhythm group selection is layout-derived
Generation SHALL select the groups each rhythm sublayer targets — the metric ring, the sparkle props,
the hero, the bass band, and the backbeat group — from the layout's classified groups by
role/capability/band rather than a single fixed list, and SHALL degrade gracefully so a missing
category disables only its own sublayer. The brief's pulse groups SHALL still seed and override the
metric ring.

#### Scenario: Selection adapts to the available groups
- **WHEN** a layout provides rhythm-cell, accent, focal, and ground-band groups
- **THEN** each sublayer targets the appropriate classified groups, and a layout missing a category simply omits that sublayer

#### Scenario: The brief still steers the ring
- **WHEN** a section's brief sets pulse groups
- **THEN** those seed the metric ring instead of the layout default
