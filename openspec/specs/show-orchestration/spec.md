# show-orchestration Specification

## Purpose
TBD - created by archiving change add-orchestration-skeleton. Update Purpose after archive.
## Requirements
### Requirement: Produce a show plan from a song analysis
The system SHALL transform a `SongAnalysis` into a `ShowPlan` that assigns, per song section, a creative intent (target prop groups, effect family, intensity) — driven by an LLM Director agent.

#### Scenario: Plan covers the song
- **WHEN** a `SongAnalysis` is given to the Director
- **THEN** the system produces a `ShowPlan` with one or more sections, each naming target groups and an intent

#### Scenario: Plan targets valid groups
- **WHEN** the Director chooses targets
- **THEN** the targets are prop groups that exist in the current layout

### Requirement: Generate placeable effect instructions
The system SHALL turn each section of the `ShowPlan` into validated effect instructions — each selecting a preset look, knob values, palette, target, layer, and time range — assembled through the preset library so the settings are valid by construction.

#### Scenario: Instructions are assembled from presets
- **WHEN** the Generator produces instructions for a section
- **THEN** each instruction references a preset look/palette and assembles to a valid settings string (out-of-range knob values are rejected)

### Requirement: Place effects without removing any
The system SHALL place generated effects additively — on prop groups, on distinct layers and/or non-overlapping time ranges — and SHALL NOT depend on removing or replacing existing effects (the automation API cannot remove effects).

#### Scenario: Additive placement
- **WHEN** multiple effects are placed
- **THEN** they are arranged so none requires deleting another (distinct layers and/or non-overlapping times)

#### Scenario: Skip effects xLights will not place
- **WHEN** an effect type or instruction is not accepted by xLights (reported as not placed)
- **THEN** the system skips it and continues, rather than aborting the run

### Requirement: Agent roles are routable to different model providers
The system SHALL resolve each agent role to a model via configuration, so a role can be served by different providers (e.g. Claude or Gemini) without code changes.

#### Scenario: Default routing
- **WHEN** no override is configured
- **THEN** each role uses its default model

#### Scenario: Re-route a role
- **WHEN** a role's model is changed in configuration
- **THEN** that role runs on the newly configured provider/model with no code change

### Requirement: Orchestrate as a resumable pipeline
The system SHALL run the stages — analyze, design, generate, apply, render, finalize — as an ordered pipeline whose state can be persisted and resumed.

#### Scenario: End-to-end run
- **WHEN** the pipeline is run for a song
- **THEN** it proceeds analyze → design → generate → apply → render → finalize and ends with a rendered sequence

#### Scenario: Resume after interruption
- **WHEN** a run is interrupted and restarted
- **THEN** it can resume from persisted state rather than restarting from scratch

### Requirement: Never discard the user's open work
The system SHALL create its working sequence without discarding any sequence the user already has open, refusing or pausing rather than forcing.

#### Scenario: User sequence open
- **WHEN** a sequence is already open when a run starts
- **THEN** the system does not force it closed; it refuses with a clear message (or uses an explicitly sanctioned path)

### Requirement: Run without live services for testing
The system SHALL allow its pipeline to run with stubbed agent outputs (no real model calls), so the flow can be exercised without an LLM API key.

#### Scenario: Stubbed agents
- **WHEN** the pipeline runs with test/stub models
- **THEN** the full analyze→render flow executes and produces effect instructions without contacting a real LLM provider

### Requirement: The generated sequence includes the song audio
The system SHALL attach the song's audio to the generated sequence so it plays with sound.

#### Scenario: Audio attached
- **WHEN** a sequence is generated for a song
- **THEN** the open sequence has the song's audio attached and its duration matches the song

### Requirement: The sequence is named after the song
The system SHALL name the generated sequence after the song by default, deriving a safe name from the song filename, and SHALL allow a manual name override.

#### Scenario: Default name from the song
- **WHEN** a sequence is generated for `mad russian christmas.mp3` with no name override
- **THEN** the sequence is saved under a name derived from the song (e.g. `mad_russian_christmas`)

#### Scenario: Manual override
- **WHEN** a name is explicitly provided
- **THEN** that name is used instead of the song-derived one

### Requirement: Generation replaces an already-open sequence
The system SHALL replace (clean-slate) any already-open sequence when generating, rather than aborting.

#### Scenario: A sequence is already open
- **WHEN** generation runs while another sequence is open
- **THEN** generation discards the open sequence and proceeds, without requiring the user to close it first

### Requirement: Audio is attached via a readable path
The system SHALL attach audio using a path the application can read (within its accessible storage), rather than an arbitrary source path that may be inaccessible or mis-encoded.

#### Scenario: Source path is outside accessible storage or has problematic characters
- **WHEN** the song's source path is outside the application's accessible storage or contains characters that break attachment
- **THEN** the system uses a copy placed in accessible storage with a safe name so attachment succeeds

### Requirement: Fall back to an audio-less sequence on attachment failure
The system SHALL fall back to generating an audio-less sequence (and warn) if the audio cannot be attached, rather than failing the run.

#### Scenario: Audio cannot be attached
- **WHEN** the song cannot be copied or attached
- **THEN** generation continues with an audio-less sequence and surfaces a warning

### Requirement: The creative direction defines a color palette mapped to the song
The creative direction SHALL define a color palette and how it maps to the song's sections and moods, with the mapping justified by the song's dynamics and harmony.

#### Scenario: Palette mapping
- **WHEN** the creative direction is produced
- **THEN** it includes a core palette and a per-section palette whose choices reflect the section's energy/mood

### Requirement: The creative brief conveys the show in plain, non-musical terms
The creative brief SHALL include a plain-language description of what the light show conveys to a viewer — its overall visual/emotional experience and a per-section sense of what is seen — expressed in everyday terms rather than musical theory, so a non-musician can understand and approve the creative intent.

#### Scenario: Lay-readable vision
- **WHEN** the creative brief is produced
- **THEN** it includes an audience-experience description (overall and per section) understandable without musical knowledge

### Requirement: Each prop group has a coherent role
The creative direction SHALL assign each prop group a role/motif (its purpose, signature style, and color treatment) that is kept consistent across the show.

#### Scenario: Group roles
- **WHEN** the creative direction is produced
- **THEN** each group used in the show has a stated role/motif that recurs coherently across sections

### Requirement: Per-section direction is grounded in the song description
Each section's direction SHALL be grounded in the song description — citing that section's dynamics, instrumentation, and accents — and SHALL NOT invent narrative or genre unsupported by the analysis.

#### Scenario: Grounded section
- **WHEN** a section's direction is produced
- **THEN** its rationale references the section's real intensity/instrumentation/accents

#### Scenario: No fabrication
- **WHEN** the song is instrumental or otherwise lacks supporting evidence
- **THEN** the direction does not invent lyrics, a story, or a genre not supported by the song description

### Requirement: Key musical moments receive deliberate choreography
The creative direction SHALL give the song's key moments — accents, the climax, and any featured lyric moments — deliberate visual choreography tied to their timestamps.

#### Scenario: Key moments
- **WHEN** the song has accents/a climax/featured lyric moments
- **THEN** the direction specifies a deliberate treatment for them at their times

### Requirement: Human review of the creative brief before generation
The system SHALL produce a human-readable creative brief and pause for human review/approval (with the ability to correct) before generating effects, unless running unattended.

#### Scenario: Attended run
- **WHEN** the creative direction is produced in an attended run
- **THEN** the pipeline pauses and presents the creative brief for review/approval before generation

#### Scenario: Unattended run
- **WHEN** running unattended
- **THEN** the brief is written and generation proceeds without pausing

### Requirement: Effect generation follows the creative brief
Effect generation SHALL follow the creative brief — a section's generated effects reflect its assigned palette, group roles/motifs, and effect direction.

#### Scenario: Generation reflects the brief
- **WHEN** a section is generated
- **THEN** the generator is given that section's palette, group motifs, and effect direction to follow

### Requirement: The planner targets only groups that accept effects
The planner SHALL target only prop groups that the application accepts effects on, so that planned/generated sections are not left empty by un-targetable groups.

#### Scenario: Non-targetable groups are excluded
- **WHEN** the available groups are determined for planning
- **THEN** groups that the application rejects effects on are excluded from what the Director and Generator may target

### Requirement: Targetability is determined empirically and reused per layout
The set of targetable groups SHALL be determined empirically (by testing whether an effect can be placed) and reused across runs for a given prop layout, re-determined only when the layout's groups change.

#### Scenario: Reused across runs
- **WHEN** a second run uses the same layout
- **THEN** the targetable set is reused without re-testing every group

#### Scenario: Layout changed
- **WHEN** the layout's group set changes
- **THEN** the targetable set is re-determined

### Requirement: Fall back to the full group list when targetability is unknown
If targetability cannot be determined (e.g. the probe or the application is unavailable), the system SHALL fall back to using the full group list rather than failing or producing an empty set.

#### Scenario: Probe unavailable
- **WHEN** targetability cannot be determined
- **THEN** the full group list is used (no regression from prior behavior)

### Requirement: Generated effects use the creative brief's section palette
When a section's creative brief specifies a palette (its chosen colors), the generated effects for that section SHALL be colored with that palette.

#### Scenario: Section has a brief palette
- **WHEN** a section's plan specifies colors
- **THEN** that section's placed effects use a palette built from those colors

### Requirement: Fall back to a mined palette when no brief palette applies
When no brief palette is specified for a section, or its colors cannot be realized, generation SHALL fall back to a mined palette rather than failing.

#### Scenario: No usable brief palette
- **WHEN** a section has no specified colors (or none can be realized)
- **THEN** placement uses a mined palette and the effect still places

### Requirement: Generation places beat-synchronized accent effects
Generation SHALL place beat- or onset-synchronized accent effects within sections, timed to the music's beats or the section's prominent instrument, in addition to the section's sustained effects.

#### Scenario: Accents on the beat
- **WHEN** a section is generated
- **THEN** short accent effects are placed within it at times aligned to the section's beats or its prominent instrument's onsets

### Requirement: Rhythmic choices are directable with a default
The rhythm groups, the followed instrument, and the accent effect SHALL be directable from the creative brief, and SHALL fall back to a sensible default when not specified.

#### Scenario: Directed by the brief
- **WHEN** the brief specifies the rhythm groups / followed instrument / accent effect for a section
- **THEN** the placed accents use those

#### Scenario: Default when unspecified
- **WHEN** the brief does not specify rhythmic intent for a section
- **THEN** generation uses a default (the section's prominent instrument and the layout's rhythm groups)

### Requirement: Accent density is bounded
The number of accent effects placed in a section SHALL be bounded so the total effect count and placement time stay reasonable (dense beats/onsets are downsampled).

#### Scenario: Dense section
- **WHEN** a section has many beats/onsets
- **THEN** the accents are capped/downsampled rather than placing one per beat without limit

### Requirement: Beat accents contrast the wash
Beat accents SHALL be colored to contrast the section's wash, rather than reusing the wash's colors.

#### Scenario: Multi-color section
- **WHEN** a section has two or more colors
- **THEN** the wash uses the calmer/darker colors and the beat accents use a brighter, distinct color

#### Scenario: Single-color section
- **WHEN** a section has one color
- **THEN** the beat accents use a brightened/contrasting variant so they still read against the wash

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

### Requirement: Accent density scales with section intensity
The number of beat accents placed in a section SHALL scale with the section's intensity — quieter sections sparser, louder sections denser — while always keeping the bar-start emphasis.

#### Scenario: Quiet vs loud section
- **WHEN** two sections have the same beats but different intensity
- **THEN** the lower-intensity section places fewer accents than the higher-intensity one, and both retain downbeat accents

### Requirement: Feature-prop hits follow the prominent instrument
Beat accents SHALL be augmented by hits on a feature prop placed at the section's prominent instrument's onset times.

#### Scenario: Prominent stem present
- **WHEN** a section has a prominent stem with onsets
- **THEN** additional accents are placed on a feature prop at those onset times (bounded)

#### Scenario: No prominent stem
- **WHEN** no stem onsets are available
- **THEN** no feature-prop hits are added (the beat chase still plays)

### Requirement: Accent color follows chord changes
When chords are available, the accent color SHALL step through the section's palette as the chord changes.

#### Scenario: Chords present
- **WHEN** accents fall in different chord spans
- **THEN** their color differs across the chord changes

#### Scenario: No chords
- **WHEN** no chord data is available
- **THEN** accents use the single contrasting accent color

### Requirement: Sequencing agents apply a best-practices guide
When a sequencing best-practices guide is configured, the design, generation, and critique agents SHALL apply it.

#### Scenario: Guide present
- **WHEN** a guide is configured and the Director, Generator, Visual Critic, or Judge runs
- **THEN** that agent's instructions include the guide

### Requirement: Single user-editable guide source
The guide SHALL be a single user-editable source applied to those agents, so editing it updates all of them.

#### Scenario: Edit propagates
- **WHEN** the guide file is edited
- **THEN** the agents use the updated content (no per-agent copies to maintain)

### Requirement: Missing guide is a no-op
A missing or unconfigured guide SHALL be a no-op — the agents behave exactly as without it.

#### Scenario: No guide
- **WHEN** no guide file is found
- **THEN** the agents run with their normal instructions and nothing fails

### Requirement: Music-interpretation agents do not receive the guide
The music-interpretation agents (analysis panel, synthesizer) SHALL NOT receive the sequencing guide.

#### Scenario: Analyst excluded
- **WHEN** an analysis/synthesizer agent runs
- **THEN** its instructions do not include the sequencing guide

### Requirement: Effects can carry synthesized value curves
The system SHALL be able to synthesize a value curve for an effect parameter and attach it to a placed effect, so the parameter varies (ramps/swells/fades) over the effect's duration.

#### Scenario: Brightness ramp
- **WHEN** an effect is placed with a synthesized brightness ramp
- **THEN** the placed effect's settings include a valid value curve for brightness

### Requirement: Synthesized curves are valid and appended safely
A synthesized value curve SHALL be a valid xLights value-curve string (parseable by the existing parser) and SHALL be attachable to an effect even when the effect's preset has no such knob.

#### Scenario: Added to a look without that knob
- **WHEN** a value curve is attached to an effect whose preset does not define that parameter
- **THEN** placement still succeeds and the curve is present in the effect's settings

### Requirement: Wash brightness scales with section energy
The section's sustained (wash) effects SHALL be given a brightness that scales with the section's intensity — lower intensity dimmer, higher intensity brighter.

#### Scenario: Quiet vs loud section
- **WHEN** two sections differ in intensity
- **THEN** the lower-intensity section's wash is dimmer than the higher-intensity section's

#### Scenario: Applied regardless of preset
- **WHEN** a wash effect's preset has no brightness knob
- **THEN** the brightness is still applied (via appended settings)

### Requirement: Lit-group coverage scales with section energy
The number of prop groups a section's wash lights SHALL scale with the section's intensity — fewer in low-intensity sections, more in high-intensity sections — leaving the rest intentionally dark.

#### Scenario: Quiet section is sparse
- **WHEN** a low-intensity section is generated
- **THEN** only a few of its groups are lit and the others are left dark

#### Scenario: Loud section is full
- **WHEN** a high-intensity section is generated
- **THEN** most/all of its groups are lit

#### Scenario: Never empty
- **WHEN** coverage is reduced
- **THEN** at least a minimum number of groups remain lit (a section is never fully blacked out by this rule)

### Requirement: Recurring sections escalate
When a section recurs (per the repetition map), later occurrences SHALL be escalated relative to earlier ones (brighter and/or more props).

#### Scenario: Final chorus is biggest
- **WHEN** a label occurs multiple times
- **THEN** the last occurrence is brighter and lights at least as many props as the first

#### Scenario: Non-recurring unaffected
- **WHEN** a section does not recur
- **THEN** it receives no escalation boost

### Requirement: Climax moments get a white flash
The show's climax/accent key-moments SHALL be punctuated with a brief full-display white flash.

#### Scenario: Flash at a climax
- **WHEN** a key-moment of an impactful kind (climax/accent) exists
- **THEN** a short white effect is placed across many groups at that time

#### Scenario: No impactful moments
- **WHEN** there are no such key-moments
- **THEN** no flashes are added

### Requirement: Effect speed scales with section energy
Section effects SHALL have their speed scaled by the section's intensity — slower when quiet, faster when loud.

#### Scenario: Quiet vs loud
- **WHEN** two sections differ in intensity
- **THEN** the lower-intensity section's effects are given a lower speed than the higher-intensity section's

#### Scenario: Applied regardless of preset
- **WHEN** an effect's preset omits a speed setting
- **THEN** a speed is still applied (appended) using the effect's speed key

### Requirement: Semantic role/ensemble groups exist in the layout
The layout SHALL contain semantic groups (`SEM_*`) derived from each model's role, spatial band/side, sweep order, and ensemble membership, generated from `rgbeffects.xml`.

#### Scenario: Role and ensemble groups
- **WHEN** the layout is processed
- **THEN** role groups (e.g. `SEM_ARCHES`), band/side groups, ordered `_LTR` groups, and ensemble groups (`SEM_ALL`, `SEM_FOCAL`, `SEM_ACCENTS`, `SEM_HOUSE`, `SEM_YARD`) are present

### Requirement: A layout manifest is emitted
A `layout_semantics.json` manifest SHALL be written describing each prop's role, capability, position, and the groups, for the planner to consume.

#### Scenario: Manifest written
- **WHEN** the generator runs
- **THEN** `layout_semantics.json` is written with per-prop role/res/pos and the group membership

### Requirement: The planner targets semantic groups
The planner SHALL target `SEM_*` groups (roles/ensembles) rather than the removed numbered taxonomy.

#### Scenario: Whole-display ensemble
- **WHEN** a high-energy section wants the full display
- **THEN** it can target the `SEM_ALL`/ensemble group

### Requirement: Layout edits are safe and idempotent
Editing the layout SHALL back up the file first, be idempotent (re-running replaces only `SEM_` groups), and leave non-numbered user groups untouched.

#### Scenario: Re-run
- **WHEN** the generator runs twice
- **THEN** the `SEM_` groups are replaced (not duplicated) and the plain user groups are unchanged

### Requirement: The Generator chooses each effect's render style
The Generator SHALL choose a render/buffer style per effect (informed by the layering guide), and that choice SHALL be applied to the placed effect.

#### Scenario: LLM-chosen style applied
- **WHEN** the Generator specifies a render style for an effect
- **THEN** the placed effect uses that buffer style

### Requirement: Render style is iterable in the refine loop
The render style SHALL be re-choosable when a section is regenerated, so the Generator can change it in response to critique (e.g. a section reading dark/sparse).

#### Scenario: Dark section regenerated
- **WHEN** the critic flags a section as dark/sparse and it is regenerated
- **THEN** the Generator may assign a different render style

### Requirement: No effect renders on the sparse default
When no render style is specified (or for code-generated effects), a deterministic fallback SHALL be applied so an effect is never left on the unset (sparse group-canvas) default.

#### Scenario: Unspecified style
- **WHEN** an effect has no chosen render style
- **THEN** a sensible default buffer style is applied

### Requirement: Catalog hard caps are enforced
Strobe and Shimmer durations SHALL be clamped to the catalog's hard caps (Strobe ≤ ~1s, Shimmer ≤ ~2 bars) regardless of what generation produced.

#### Scenario: Over-long strobe
- **WHEN** generation produces a 10-second Strobe
- **THEN** the placed effect is clamped to the cap

### Requirement: Placement-rule violations gate the loop
Texture-on-linear-prop, energy-band-mismatch, and overlapping-feature violations SHALL be detected as objective findings so the refine loop regenerates the offending sections.

#### Scenario: Texture on a linear prop
- **WHEN** a texture effect targets an arch/outline group
- **THEN** an objective finding names the section and the violation

#### Scenario: Energy mismatch
- **WHEN** an effect's energy band is far from its section's energy
- **THEN** an objective finding is raised

#### Scenario: Two features at once
- **WHEN** two high-attention effects overlap in time
- **THEN** an objective finding is raised

### Requirement: Design-implicated defects escalate to a design revision
When a section's objective violations implicate the brief's own choices (or persist after regeneration), the loop SHALL revise that section's design before regenerating, rather than re-realizing the flawed design.

#### Scenario: Brief-chosen effect violates the rules
- **WHEN** a rules violation names an effect type that the section's brief specifies
- **THEN** the section design is revised (violation text in hand) and generation realizes the new design

#### Scenario: Bounded
- **WHEN** a section has already been redesigned this run
- **THEN** it is not redesigned again (regeneration only)

### Requirement: The corrected design persists
A design revised during refinement SHALL be written back to the design cache at finalize.

#### Scenario: Re-run keeps the fix
- **WHEN** a later run loads the cached design
- **THEN** it contains the revised sections

### Requirement: Multi-color effects receive enough colors
Effects that render multiple palette colors SHALL receive at least 3 colors, expanded deterministically from the section palette when the brief is thin.

#### Scenario: Plasma with a 2-color brief
- **WHEN** a multi-color effect is placed in a section whose brief has 2 colors
- **THEN** its palette is expanded to 3+ colors derived from the section's

### Requirement: Concurrent effects vary within the section palette
Effects in the same section SHALL NOT all carry an identical palette; assignments vary (rotation) within the section's color family.

#### Scenario: Two washes in one section
- **WHEN** two effects are placed in the same section
- **THEN** their palettes differ in color order/subset while staying in the section's palette

### Requirement: The Director's color names resolve
The Director SHALL be guided to the known color vocabulary, and common show colors SHALL be present in it, so chosen names are not silently dropped.

#### Scenario: Copper
- **WHEN** the brief names a common show color like Copper
- **THEN** it resolves to a hex rather than being dropped

### Requirement: Objective QA includes rendered lit-coverage
When a rendered preview is available, the objective QA score SHALL include a coverage metric measuring how lit the display is in high-energy sections.

#### Scenario: Dark loud section gates
- **WHEN** a high-intensity section renders near-black
- **THEN** the coverage score drops, an error finding names the section, and the objective score falls

#### Scenario: Quiet sections not penalized
- **WHEN** a low-intensity section is sparse/dark
- **THEN** coverage does not penalize it (restraint is intentional)

#### Scenario: No preview available
- **WHEN** no rendered preview exists (hermetic tests, missing renderer)
- **THEN** the QA behaves exactly as before (coverage neutral, objective unchanged)

### Requirement: The beat chase spans at least two rhythm groups
The beat accent chase SHALL run across at least two groups, extending a thin brief choice with the layout's rhythm-cell groups (arches, canes, mini trees).

#### Scenario: Brief picks one group
- **WHEN** the brief's pulse_groups has a single group and rhythm-cell groups exist
- **THEN** the chase is extended so the beat alternates across ≥2 groups

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

### Requirement: High-energy sections carry an ensemble bed
Sections at high intensity SHALL include a low-brightness ensemble bed wash beneath the features, unless the section already targets that ensemble.

#### Scenario: Peak section
- **WHEN** a section's effective intensity is ≥0.7 and a ground/whole-display group exists
- **THEN** a bed wash spans the section on it

### Requirement: Long energetic washes build
Wash effects longer than ~15s in high-energy sections SHALL ramp brightness rather than holding a flat level.

#### Scenario: 36-second chorus wash
- **WHEN** a long wash is placed in a high-intensity section
- **THEN** its brightness ramps upward across the effect

### Requirement: Instrument entrances are detected and featured
A sustained surge of an instrument stem SHALL be detected as an entrance, and a hero prop SHALL ride that instrument's onsets with a suitable effect for a bounded feature window.

#### Scenario: Guitar entrance
- **WHEN** a stem's energy rises sharply and sustains above its entrance threshold
- **THEN** a feature is placed on the focal prop at the entrance, timed to that stem's onsets

#### Scenario: No surge
- **WHEN** a stem is already prominent (no surge) or only blips
- **THEN** no entrance is detected for it

### Requirement: Entrances surface to the planner
Detected entrances SHALL be added to the show's key moments so design and critique see them.

#### Scenario: Key moment
- **WHEN** an entrance is detected
- **THEN** a key moment of kind "entrance" exists at its time

### Requirement: Refined instructions persist
The instruction cache SHALL reflect the refined (final) instructions, not the pre-refine generation.

#### Scenario: Cached re-run
- **WHEN** a run completes refinement and a later run loads the cache
- **THEN** the loaded instructions are the refined ones

### Requirement: Visual judgments use the real render when available
When the open sequence has media attached, the refine loop SHALL export the real render and use it for the visual critique and the coverage metric.

#### Scenario: Media-attached sequence
- **WHEN** the loop evaluates and the open sequence has media
- **THEN** the coverage frames and critic clips come from the real export

### Requirement: Export is guarded and fail-safe
The export SHALL only be attempted on media-attached sequences, and any export failure SHALL fall back to the offline approximation (and then to neutral) without failing the run.

#### Scenario: No media / export failure
- **WHEN** the sequence has no media or the export fails
- **THEN** the offline renderer is used (or coverage stays neutral) and the run continues

### Requirement: Real-render timing is offset-corrected
Frames and clips taken from the export SHALL account for the export's lead-in offset so song-time maps to the right video-time.

#### Scenario: Lead-in
- **WHEN** the export is longer than the song
- **THEN** sampling at song-time t reads the frame at t + lead-in

### Requirement: Effects respect duration classes
Each placed effect SHALL respect its duration class: hit effects bounded to ~a bar, phrase effects to ~8 bars, sustained effects unbounded.

#### Scenario: Hit effect placed long
- **WHEN** generation produces a hit-class effect (e.g. Shockwave) spanning many bars
- **THEN** it is converted into short per-bar cells rather than one long smear

#### Scenario: Phrase effect placed long
- **WHEN** a phrase-class effect spans more than ~8 bars
- **THEN** it is clamped to its phrase length

#### Scenario: Sustained untouched
- **WHEN** a sustained-class effect spans a section
- **THEN** it is left as designed

### Requirement: Sections compose from cookbook scenes
The Director SHALL choose a cookbook scene (or explicitly freeform) per section with an archetype-to-group casting, and the Generator SHALL realize the chosen scene's stack.

#### Scenario: Scene chosen
- **WHEN** a section's design names a scene
- **THEN** the brief records the scene and casting, and generation realizes its stack on the cast groups

#### Scenario: Freeform allowed
- **WHEN** no scene fits a section
- **THEN** the section may be freeform (empty scene id) and generation proceeds as before

### Requirement: Subtractive ensemble groups exist for scenes
The layout semantics SHALL include subtractive groups (all-less-hero, all-less-hero-rhythm) so beds never paint over features.

#### Scenario: Bed under a clean hero
- **WHEN** the layout is (re)generated
- **THEN** SEM_ALL_LESS_FOCAL and SEM_ALL_LESS_FOCAL_RHYTHM exist with the right members

### Requirement: Render precedence is canonical
Sequence element rows SHALL follow a canonical precedence: ensemble beds first (painted over), then frame/rhythm/role rows, with focal and accent rows last (winning overlaps).

#### Scenario: Bed vs feature overlap
- **WHEN** a bed group and the focal group light the same props
- **THEN** the focal row renders after (over) the bed

### Requirement: The canonical view drives sequence creation when available
A canonical master view SHALL be authored into the layout, and sequence creation SHALL use it when xLights has it loaded, falling back gracefully otherwise.

#### Scenario: View not yet loaded
- **WHEN** the view exists in the file but xLights hasn't restarted
- **THEN** sequence creation proceeds with the default view (no failure) and the finalize reorder still applies

### Requirement: Sections are woven from beat-quantized cell recipes
Section generation SHALL realize sections as short, beat-quantized effect cells expanded deterministically from per-section cell recipes. The recipes — effect types, target groups, alternation pattern, cell length in beats, blend mode, motion value curve, and in/out transition — SHALL be directable by the generation LLM, with a deterministic fallback weave when recipes are absent or invalid. Cell timing SHALL snap to the section's real beat grid.

#### Scenario: LLM recipes expand into beat-snapped cells
- **WHEN** a section's generation output includes cell recipes (e.g. a SingleStrand chase carrier over the rhythm groups at 1 beat per cell)
- **THEN** the pipeline emits one effect instruction per cell slot, with boundaries on the section's beat times, targets rotating across the recipe's groups per its alternation pattern, and the section palette realized per cell

#### Scenario: Fallback weave when the LLM omits recipes
- **WHEN** a section's generation output carries no weave (or its recipes reference no valid groups)
- **THEN** a deterministic default weave (a motion-effect beat carrier over the rhythm groups) is expanded instead, and generation never fails or skips for lack of recipes

#### Scenario: Cell settings carry blend, curve, and transition keys
- **WHEN** a recipe specifies a blend mode, a motion curve, or a transition
- **THEN** the expanded cells carry the corresponding corpus-verified settings keys (layer blend on the upper layer; motion value curve on the effect's own parameter; in/out transition type), and unknown curve/effect combinations degrade to no extra keys rather than a placement failure

### Requirement: Cell density is bounded and scales with intensity
The number of woven cells per section SHALL be bounded by a budget that scales with section intensity and length, with even downsampling when recipes exceed it, so quiet sections weave sparsely and peaks approach community density without unbounded placement counts.

#### Scenario: Quiet vs peak density
- **WHEN** two equal-length sections weave the same recipes at intensity 0.2 and 1.0
- **THEN** the quiet section expands materially fewer cells than the peak section, and both stay within their budgets

### Requirement: The deterministic beat layer defers to a covering carrier
WHEN a section's weave contains a carrier recipe whose groups cover the rhythm pool, the deterministic beat-accent layer SHALL NOT also place its every-beat chase on those groups (downbeat sparkle and hero-onset accents remain), so the beat is carried once, not doubled.

#### Scenario: No doubled beat chase
- **WHEN** a section weaves a carrier recipe over the rhythm groups
- **THEN** the beat-accent pass emits no every-beat chase instructions for that section, while its downbeat sparkle and hero onset layers still place

### Requirement: Motion-effect share is surfaced to QA as an advisory
The placement-rules QA SHALL surface, per energetic section, an advisory finding when the share of continuous-motion effects among that section's placements falls below a threshold, visible to the Judge but never gating the objective score.

#### Scenario: Static section flagged
- **WHEN** an intensity ≥ 0.5 section's placements are predominantly static/punctuation effects
- **THEN** the QA report contains an advisory motion-share finding scoped to that section, and the objective score is unchanged by it

### Requirement: Beat cells support directional realization via effect settings
Beat-synchronized cells SHALL support direction — left/right sweeps, bounces, center-out/center-in gestures, and up/down runs — realized exclusively through the effects' own direction parameters (chase types, direction choices, reverse flags) using corpus-observed values, without altering the cells' target groups or render styles. Direction SHALL be directable by the generation LLM per cell recipe; WHEN a recipe names no direction, explicit recipes SHALL expand exactly as today while the deterministic fallback weave SHALL default to a bouncing sweep. An effect with no mapped direction parameter SHALL ignore the direction without failing.

#### Scenario: Chase direction comes from the effect's chase type
- **WHEN** a carrier recipe over the arches specifies left-to-right (or center-out)
- **THEN** its cells carry the effect's own direction setting (e.g. chase type Left-Right, or From Middle) in their settings, targets and render styles unchanged

#### Scenario: Static-direction effects bounce per bar
- **WHEN** a recipe with a static-direction effect (e.g. Fill or Wave) specifies bounce
- **THEN** cells within one bar share a single direction and the direction value reverses at each bar boundary, while effects with native bounce types (e.g. SingleStrand Dual Bounce) bounce within the effect itself

#### Scenario: Graceful degradation
- **WHEN** a recipe's effect has no mapped direction parameter, or the direction value is unknown
- **THEN** cells expand exactly as they do today

### Requirement: The beat-accent chase alternates direction per bar
The deterministic every-beat accent layer SHALL alternate its group-rotation order on each bar — forward through the spatial group order on even bars, backward on odd bars — with no LLM involvement.

#### Scenario: Accent chase bounces
- **WHEN** beat accents chase three rhythm groups across two consecutive bars
- **THEN** the first bar visits the groups in spatial order and the second bar visits them in reverse order

### Requirement: Directional cells render as visible cross-group motion
WHEN a cell recipe specifies a horizontal or radial direction on a chase-family effect, the cell SHALL render on a buffer spanning the full target group (so the motion travels across all of the group's props) and SHALL persist long enough to track (a minimum cell length of two beats), unless the recipe explicitly chooses a render style. Non-directional cells SHALL keep the per-model default.

#### Scenario: A left-to-right chase travels the whole arch line
- **WHEN** a carrier recipe over the arches specifies ltr on a chase effect with no explicit render style
- **THEN** its cells render on the group buffer with at least two-beat duration, so one chase head visibly travels across all the arches

#### Scenario: Explicit style and non-directional cells unchanged
- **WHEN** a recipe explicitly sets a render style, or has no direction
- **THEN** the cell uses exactly that style (or the per-model default), as today

### Requirement: Automated palettes guarantee LED-legible hue contrast
The palette realization SHALL enforce a hue-contrast floor: WHEN a section's resolvable colors cluster within a minimum hue spread, a contrasting anchor SHALL be injected deterministically; rhythm-carrying cells (carrier and accent roles, and the beat-accent layer) SHALL alternate between the two most hue-distant anchors beat-to-beat, while texture and bed placements keep the section's expanded color family.

#### Scenario: A warm-clustered palette gains a contrast anchor
- **WHEN** a section's palette resolves to near-identical warm hues (e.g. golds and warm whites)
- **THEN** a hue-distant anchor is injected and consecutive carrier cells alternate between two clearly different colors, while the section's washes keep the warm family

#### Scenario: An already-contrasting palette is untouched
- **WHEN** a section's palette already spans distant hues (e.g. deep blue and gold)
- **THEN** no color is injected and the two existing most-distant colors become the alternating anchors

### Requirement: Effect speed uses each effect's real speed parameter
The intensity-to-speed realization SHALL set each effect's actual speed/cycles/movement parameter (corpus-verified key and value range per effect type) and SHALL emit nothing for effects that have no speed parameter, so no placement carries a speed key the effect does not define.

#### Scenario: Cycles-class effect gets real speed control
- **WHEN** a Color Wash placement is realized at high section intensity
- **THEN** its settings carry `E_TEXTCTRL_ColorWash_Cycles` with a value in the corpus-observed range, and no `E_SLIDER_Color Wash_Speed` key

#### Scenario: Speedless effects emit nothing
- **WHEN** a Twinkle or SingleStrand placement is realized
- **THEN** no speed key is added to its settings

### Requirement: Placements carry no stale settings keys
Settings keys known to be absent from the current xLights version SHALL be stripped from mined looks at placement, so the editor logs no ApplySetting errors for our effects.

#### Scenario: Stale chase key stripped
- **WHEN** a mined SingleStrand look whose frozen settings include `E_CHECKBOX_Chase_3dFade1` is placed
- **THEN** the assembled settings string does not contain that key

### Requirement: Semantic groups render at native buffer resolution
The layout patcher SHALL set a grid size on the SEM_ groups that covers their actual extent, so group-canvas effects render at full resolution without max-grid warnings; user-authored groups SHALL NOT be modified.

#### Scenario: Large semantic group renders without downscaling
- **WHEN** the layout is patched and xLights reloads it
- **THEN** SEM_ groups whose extent exceeds 400 carry a larger GridSize and rendering logs no max-grid-size warnings for them

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

### Requirement: The show's peak is realized as the visual payoff
The orchestrator SHALL deterministically identify the show's peak section(s) — those within a small band of the maximum section intensity, above a floor — and realize them with display-wide coverage at full brightness, regardless of how narrowly the creative brief targeted them. Merely-high (non-peak) sections SHALL remain below the peak (a dim ensemble bed, not a full lit display) so the energy arc escalates rather than flattening.

#### Scenario: A narrowly-targeted peak still fills the yard
- **WHEN** the peak section's brief names only one or two groups at maximum intensity
- **THEN** a full-display ensemble is lit at full wash brightness across that section, and the peak's coverage spans the rhythm pool plus the broad display, so the yard reads as the biggest moment

#### Scenario: Highs stay under the peak
- **WHEN** a section is high-energy (≥ the bed threshold) but not within the peak band
- **THEN** it gets the dim ensemble bed as before, not the full peak fill — the peak remains visibly bigger

#### Scenario: No peak in a quiet show
- **WHEN** the show's maximum section intensity is below the peak floor
- **THEN** no peak fill is applied and sections realize as before

### Requirement: The brief reserves the biggest look for the peak
The Director's creative brief SHALL be directed to give the show's single highest-energy moment the broadest coverage and biggest gesture, and to build the preceding section into it, rather than spending a narrow or dark look on the payoff.

#### Scenario: Director prompt names the peak intent
- **WHEN** the Director composes the show plan
- **THEN** its instructions direct it to identify the peak, reserve the broadest/biggest look for it, and build into it

### Requirement: Curated trigger effects from a hand-editable cookbook
The orchestrator SHALL place curated "trigger" effects — deterministic rules mapping musical or lyrical events to scaled effects — defined in a hand-editable markdown cookbook parsed best-effort (a missing or malformed entry is skipped, never fatal). Each trigger SHALL declare its detector, effect, render scope, rarity, section eligibility, and color/direction treatment. Triggers SHALL be applied as a deterministic layer over the existing fabric and SHALL respect the hard caps and layer budget.

#### Scenario: A cookbook trigger places its effect
- **WHEN** the cookbook defines a trigger whose detector finds events in the analysis
- **THEN** the pipeline places that trigger's effect at the detected times, scaled and colored per the cookbook, tagged with the section index

#### Scenario: Editing the cookbook changes the show without code
- **WHEN** a user edits the cookbook (tunes a threshold, changes an effect or color, enables/disables a trigger that reuses an existing detector)
- **THEN** the next run reflects the edit with no code change

#### Scenario: A malformed or unknown trigger is skipped
- **WHEN** a cookbook entry names an unknown detector or has invalid fields
- **THEN** that trigger is skipped with a log and the run proceeds

### Requirement: Triggers are used sparingly across the show
Trigger effects SHALL be bounded by two sparsity scales: section selection (a deterministic rotation so not every section features the same accent) and per-trigger within-section density. Periodic drum triggers SHALL key to the drum stem's onsets (not the beat grid); singular triggers (a big-moment shockwave) SHALL fire on the strongest event in their region only.

#### Scenario: Not every section gets the same accent
- **WHEN** several sections are eligible for the same periodic trigger
- **THEN** only a rotated subset feature it, so consecutive sections differ

#### Scenario: The big moment is singular
- **WHEN** the big-moment shockwave trigger runs over a region
- **THEN** it fires once on the strongest drum hit / energy jump there, rendered across the whole house

### Requirement: Trigger scale and variety come from render scope and per-event modulation
Small vs large SHALL be expressed as render scope — per-model (each prop, prop-scaled) vs whole-house (one radiating gesture) — not by shrinking a radius. Successive events of a periodic trigger SHALL vary deterministically: rotating target groups and alternating contrast-anchor color and out/in direction.

#### Scenario: Periodic drum shockwaves vary per hit
- **WHEN** the periodic drum-onset shockwave trigger fires across a section
- **THEN** successive onsets rotate across the rhythm groups and alternate color and out/in radius, each rendered per-model

### Requirement: Word-precise lyric timing for color words
The analysis SHALL persist per-word lyric timestamps (already computed during alignment) so lyric-driven triggers can place effects on the word, not only the line.

#### Scenario: A color word lights the yard
- **WHEN** a lyric line contains a color word and per-word timing is available
- **THEN** the color-word trigger colors the prominent props at that word's time

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

### Requirement: Color Wash is a placeable effect type
"Color Wash" SHALL be treated as a placeable effect type — included in the placeable set offered to the director and enumerated by the editable-brief schema — having been re-verified to place (`addEffect` `worked=true`) and render via the automation API. The reject-list mechanism SHALL remain for any effect type genuinely confirmed unplaceable.

#### Scenario: Color Wash is offered and accepted
- **WHEN** the placeable effect types are computed
- **THEN** "Color Wash" is included, so the director may choose it and the brief schema lists it as a valid effect type

#### Scenario: The reject mechanism still exists
- **WHEN** a future effect type is confirmed unplaceable and added to the reject list
- **THEN** it is filtered out of the placeable set exactly as before

### Requirement: The creative brief is emitted as a schema-backed editable file
When the creative brief is written, the orchestrator SHALL also write a JSON Schema for it (`creative_brief.schema.json`) and reference that schema from `creative_brief.json` via a relative `$schema` key, so a schema-aware editor offers valid choices and validation. The schema SHALL enumerate the run's actual vocabulary — the live layout groups for group fields, placeable effect types for effect fields, cookbook scene IDs for `scene_id`, the song's stems for `follow_stem`, and the named colors for palette fields — and SHALL keep `intensity` bounded to 0–1.

#### Scenario: Schema lists the run's real choices
- **WHEN** the brief is written for a run whose layout has groups G and whose cookbook defines scenes S
- **THEN** the generated schema's group fields enumerate G and its `scene_id` field enumerates S, so an editor offers exactly those choices

#### Scenario: An edited brief is read back unchanged
- **WHEN** the user edits `creative_brief.json` (which carries a `$schema` key) and re-runs
- **THEN** the brief loads as the edited `ShowPlan`, with the `$schema` key ignored, and the run uses the edited values

#### Scenario: A brief without a schema still loads
- **WHEN** a `creative_brief.json` has no `$schema` key
- **THEN** it validates and runs exactly as before

### Requirement: The creative brief is editable via a local browser form
The orchestrator SHALL provide a local browser form that edits the creative brief using widgets generated from the brief schema — dropdowns for enum fields, multi-selects for array-of-enum fields, color swatches for the palette, a slider for intensity — and writes edits back to `creative_brief.json`. The save SHALL preserve the `$schema` reference and every field the form does not render, and SHALL reject a structurally invalid edit without writing.

#### Scenario: Edit a section's scene and palette via widgets
- **WHEN** the user opens the brief editor and changes a section's scene (dropdown) and palette (color rows)
- **THEN** Save writes those changes to `creative_brief.json` while leaving unrendered fields (e.g. group_motifs) and the `$schema` key intact

#### Scenario: Invalid edit is rejected
- **WHEN** a save would produce a brief that is not a valid ShowPlan
- **THEN** the server rejects it with an error shown in the form and does not overwrite the file

#### Scenario: Launch from the CLI
- **WHEN** the user runs `xlo edit-brief --song <mp3>` (or `--brief <path>`)
- **THEN** the editor serves that song's cached brief and opens it in the browser

### Requirement: Featured accent/sparkle prop groups are steered to pop
When a section's look centers on a dedicated accent/sparkle prop group (such as SEM_SNOWFLAKES or SEM_SPINNERS), the creative-direction prompts SHALL steer those props to be the bright, high-contrast focal element in a light color over a different-hued background bed (e.g. white snowflakes on a blue house), kept bright even in a calm section. The generator prompt SHALL also steer away from named particle effects (Snowflakes/Snowstorm/Meteors) on small dedicated props — which render nothing visible there — toward lighting the props directly, reserving particle effects for a large canvas with a high count. This is steering, not a deterministic guarantee.

#### Scenario: Snow section steered to white-on-blue
- **WHEN** the Director and Generator compose a section that features the snowflake props
- **THEN** their prompts direct the snow props to a bright light color over a contrasting bed, and direct against a particle effect that won't render on the small props

#### Scenario: Particle effects still allowed on a real canvas
- **WHEN** a section uses a particle effect on a large whole-house or Matrix canvas
- **THEN** the guidance does not discourage it (the caveat is scoped to small dedicated props)

### Requirement: An instruction's explicit color is respected
When an effect instruction carries an explicitly-chosen `palette_colors`, the orchestrator SHALL use those colors as-is rather than overwriting them with the index-rotated section palette. An instruction with no explicit `palette_colors` SHALL receive the section-palette family as before.

#### Scenario: A pinned feature color survives
- **WHEN** the generator sets `palette_colors` (e.g. white) on a feature-prop instruction
- **THEN** that color is used as-is and is not replaced by the section-palette rotation

#### Scenario: Unpinned instructions take the section family
- **WHEN** an instruction has no explicit `palette_colors`
- **THEN** it receives the expanded section palette exactly as before

### Requirement: Featured sparkle/snow props have a deterministic contrast floor
When a dedicated sparkle/snow prop group (SEM_SNOWFLAKES or SEM_SPINNERS) is among a section's target groups, the orchestrator SHALL recolor that group's base-lighting effects to the section's lightest resolved palette color and raise their brightness to a bright level, so the feature pops against the bed regardless of the LLM's color choice. This floor SHALL apply only to those accent prop groups and only when they are featured; all other groups and effect choices remain the LLM's.

#### Scenario: Snow props forced to the lightest color, bright
- **WHEN** a section targets SEM_SNOWFLAKES with a palette containing a light color
- **THEN** the snowflake props' base lighting is set to that lightest color at a bright level, while the bed and other groups keep their colors

#### Scenario: No accent group featured
- **WHEN** a section does not target a sparkle/snow prop group
- **THEN** the floor makes no change

### Requirement: Triggers can key off any instrument stem
A trigger SHALL be able to fire on any instrument stem's onsets (drums, piano, bass, guitar,
vocals), selected by a `stem` field, with section eligibility by that stem's prominence. Triggers
without a `stem` SHALL default to drums (back-compat). A stem that is never prominent SHALL simply
produce no events (not an error).

#### Scenario: Piano notes drive the props
- **WHEN** a trigger specifies the piano stem on a piano-heavy song
- **THEN** it fires on the piano's onsets, rotating across the target groups so the melody walks the props, in the sections where piano is prominent

#### Scenario: Drum triggers unchanged
- **WHEN** an existing trigger names no stem
- **THEN** it fires on the drum stem exactly as before

### Requirement: Holiday songs prefer the traditional Christmas palette
The Director's palette guidance SHALL prefer a red / green / white primary palette with accent
colors for Christmas/holiday songs, unless the song's mood clearly calls for a different scheme.

#### Scenario: Christmas song palette
- **WHEN** the Director designs a show for a clearly Christmas/holiday song
- **THEN** its section palettes lean on red, green, and white as primaries with a small number of accent colors

### Requirement: Long sections are subdivided regardless of lyrics
No song section SHALL exceed the long-section cap. A segment longer than the cap SHALL be subdivided at the music's own seams (harmonic-change points, then energy-delta peaks, then beat-snapped time), with pieces labeled from the parent (id + ordinal). This SHALL apply whether or not the song has timed lyrics, so a long instrumental span in a lyric song (e.g. a long intro before the first sung line) is broken up rather than left as one oversized section.

#### Scenario: A lyric song's long instrumental intro is split
- **WHEN** a song has lyrics but a long instrumental stretch with no lyric markers (longer than the cap)
- **THEN** that stretch is subdivided into sections no longer than the cap, cut at musical seams, labeled from the parent

#### Scenario: Sections within the cap are untouched
- **WHEN** all sections already fit within the cap
- **THEN** the segmentation is unchanged (no-op, idempotent)

#### Scenario: Instrumental songs are unaffected by the change
- **WHEN** a song has no lyrics
- **THEN** long sections are capped exactly as before

### Requirement: Long-section cuts land on the strongest seam, not the latest
When subdividing a long section, the cut within each window SHALL be chosen by structural-seam
STRENGTH — how much the energy changes at the seam (harmonic-change times scored by the coincident
energy shift; energy-delta points scored directly) — selecting the strongest seam and breaking ties
toward the earliest time, so cuts land on the real break rather than drifting to the length cap.

Section boundaries SHALL be DOWNBEAT-AWARE wherever they are placed — both the instrumental-cap cuts
AND the lyric-marker-derived boundaries (marker starts, the outro split, and long-span in-fill
boundaries). A boundary SHALL snap to the nearest downbeat (bar line) when one lies within a small
tolerance of it, using the beat grid's bar positions, so a section starts on a bar line rather than a
weak off-beat. For instrumental-cap cuts, a seam whose bar line falls outside the current window
(e.g. a loud seam near the cap whose downbeat is past the cap) SHALL be excluded, so an earlier
downbeat phrase boundary is preferred over a louder off-beat seam near the cap. When the beat grid
carries no bar positions, boundary placement SHALL fall back to beat-snapped behavior unchanged.
Snapping SHALL never produce a piece shorter than the minimum-piece floor nor a section longer than
the cap.

#### Scenario: A real energy break beats a run of weak harmonic changes
- **WHEN** a window contains many equally-weighted harmonic-change candidates plus one point where the energy clearly drops out / surges back
- **THEN** the cut is placed at the energy break, not at the latest harmonic change near the cap

#### Scenario: A cut lands on the bar line, not a weak off-beat near the cap
- **WHEN** a window's strongest energy seam sits on a weak beat near the cap while an earlier downbeat carries a real phrase boundary (a coincident harmonic change)
- **THEN** the off-beat seam's bar line falls past the cap and is excluded, and the cut lands on the earlier downbeat

#### Scenario: A lyric-marker boundary lands on the bar line
- **WHEN** a song has timed lyric markers and a section boundary (a marker start, the outro, or an in-fill cut) falls within the snap tolerance of a downbeat
- **THEN** that boundary is placed on the downbeat rather than the nearest off-beat

#### Scenario: Chosen cut snaps to the nearest downbeat within tolerance
- **WHEN** the selected cut time sits within the snap tolerance of a downbeat that respects the minimum-piece floor and the cap
- **THEN** the cut is placed on that downbeat

#### Scenario: No bar positions falls back to beat snapping
- **WHEN** the beat grid carries no bar-position information
- **THEN** cuts and lyric boundaries are chosen and beat-snapped exactly as before, with no downbeat adjustment

#### Scenario: No seam data falls back to spacing
- **WHEN** a window has no harmonic or energy candidate at all
- **THEN** the cut falls back to an even beat-snapped spacing near the cap, snapped to a downbeat when one is within tolerance

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

### Requirement: Section phrasing is directable as legato or staccato

The show plan SHALL let the Director direct each section's phrasing — the soft-versus-crisp
character of its woven cells — through an optional `phrasing` field on the section plan whose
value is `legato`, `staccato`, or empty. `legato` SHALL mean evolving, softly-faded cells suited
to calm or introspective sections; `staccato` SHALL mean crisp on/off cells suited to energetic
sections. The field SHALL be optional and back-compatible: a section (or a cached plan) that omits
it SHALL remain valid.

#### Scenario: Director directs legato phrasing

- **WHEN** the Director sets a section's `phrasing` to `legato`
- **THEN** the section plan carries that value and the weaver realizes that section's cells with
  soft fades rather than crisp on/off edges

#### Scenario: Phrasing is optional and back-compatible

- **WHEN** a section plan (or a previously cached plan) omits `phrasing`
- **THEN** the plan is still valid and generation proceeds, resolving phrasing from the section's
  intensity rather than failing

### Requirement: The weaver realizes legato phrasing as a curated soft-edge transition

The cell weaver SHALL resolve each section's effective phrasing — the directed `phrasing` value
when present, otherwise derived from the section's intensity (low intensity SHALL resolve to
legato, energetic intensity SHALL resolve to staccato) — and SHALL realize legato cells with a
soft-edge transition primitive selected in code from the cell's effect family: a linear fade-in /
fade-out (scaled to the cell's duration and bounded by a cap) for line and chase effects, or a
dissolve in/out transition for textural fill and wash effects. The selection and all numeric
values SHALL be owned by code, not the Director. Staccato cells SHALL carry no synthesized
soft-edge keys, so energetic sections render exactly as they do today. A cell recipe that already
names an explicit transition SHALL keep that transition (the phrasing-derived primitive applies
only when the recipe names none). Legato realization SHALL NOT increase a section's cell count
beyond its existing intensity-scaled budget.

#### Scenario: Low-intensity line effect softens with a fade

- **WHEN** a low-intensity section with no directed phrasing weaves a line or chase effect
- **THEN** its cells carry synthesized fade-in/fade-out settings (in xLights' fade units) sized
  from each cell's length and clamped to the cap, so the section reads as evolving rather than
  flashing

#### Scenario: Legato textural effect softens with a dissolve

- **WHEN** a legato section weaves a textural fill or wash effect
- **THEN** its cells carry a dissolve in/out transition (with code-set adjust) rather than a flat
  opacity fade

#### Scenario: Energetic section stays crisp

- **WHEN** a section resolves to staccato (directed, or energetic by intensity) is woven
- **THEN** its cells carry no synthesized soft-edge keys and the placements match the pre-change
  crisp behavior

#### Scenario: Directed phrasing overrides the intensity default

- **WHEN** a section's intensity would imply staccato but the Director directs `legato` (or vice
  versa)
- **THEN** the weaver uses the directed phrasing, not the intensity-derived default

#### Scenario: An explicit recipe transition is preserved

- **WHEN** a legato cell recipe already names its own transition
- **THEN** the weaver keeps the recipe's transition and does not overwrite it with the
  phrasing-derived primitive

