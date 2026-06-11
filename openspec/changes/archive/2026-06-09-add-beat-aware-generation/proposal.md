## Why

The show now has the right structure, colors, and groups — but it doesn't **move with the music**. Generation places one section-spanning wash per group, so a section "feels" right but nothing hits the beat. Yet the analysis already has everything to fix that: the **beat grid** (617 beats), **onsets** (1166), and **per-stem onsets** from the 6-stem split (drums 716, guitar 853, bass 450, piano 339, …) — the actual rhythm of each instrument. And the user's **`04_BEAT_1–4` groups are purpose-built rhythm groups** (and targetable). We're throwing all of it away at generation.

This change adds a **beat layer**: short accent effects placed *within* each section, timed to the beats and the section's **prominent instrument's** onsets, chasing across the rhythm groups — so the lights punctuate the kicks, hits, and pulse of the song. Timing is deterministic (from the analysis); the creative choices (which groups, which instrument, what accent) come from the brief. (No bar lines are detected in this data, so we work off the beat grid + onsets.)

## What Changes

- **Surface per-section rhythm** (a deterministic helper): each section's beat times, its **prominent stem** (top non-"other" from `stem_shares`) + that stem's onset times in the window, and the tempo — available to the Director and the placement pass.
- **Per-section rhythmic intent in the brief** (additive `SectionPlan` fields): `pulse_groups` (which groups punctuate — default `04_BEAT_*`), `follow_stem` (whose rhythm to ride), `accent_effect` (a placeable punctuation effect), `pulse_on` (`beat`|`onset`). The Director chooses these from the surfaced rhythm; deterministic fallback when omitted.
- **A deterministic beat-accent placement pass**: per section, place **short accent effects** on the `pulse_groups` at the chosen times (the `follow_stem`'s onsets or the beats), **chasing across the groups** (rotate per beat), in the section's palette — **added alongside** the existing section washes (a second layer). **Density is bounded** so the effect count stays sane.
- The accents are tagged `section_index` like everything else, and the **Sync QA finally has real beat-aligned effects to measure**.

**Non-goals:** one effect per onset of every stem (count explosion); xLights timing-track/effect-speed-to-BPM sync; bar/downbeat detection (not in the data); melody/pitch-following; per-stem color reactivity; changing the section-wash generation (this *adds* a layer).

## Capabilities

### Modified Capabilities
- `show-orchestration`: generation places beat/onset-synchronized accent effects within sections (timed to the beats or the section's prominent instrument, chasing across directable rhythm groups), bounded in density — so the show pulses with the music instead of sitting still.
- `music-interpretation`: surfaces, per section, the beat times and the prominent instrument with its onsets, for rhythmic generation.

## Impact

- **`xlights-orchestrator`**: a per-section rhythm helper; `SectionPlan` rhythm fields (additive); a deterministic beat-accent placement pass after section generation (like the palette/intensity passes); the Director prompt surfaces the rhythm + requests intent. The section-wash generator is unchanged (the beat layer is additive).
- **Builds on** the 6-stem instrumentation (`audio-analysis`), the rich song description + creative brief (`music-interpretation`/`show-orchestration`), the palette realization (accents use the section palette), and the targetable-group filter (rhythm groups are real targets). Gives the existing Sync QA something real to evaluate.
