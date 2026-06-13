## Context

`coverage_cap`/`trim_coverage` can only keep a subset of the targets the Director's instructions already cover — they can't widen a peak the Director targeted narrowly (sec6: intensity 1.0, 1 group). `ensemble_bed` adds one ground-band at 60% brightness for intensity ≥0.7 — enough to avoid a black yard, not enough to read as a payoff. So a narrow peak stays dark by construction, and the critic flags it every run.

## Goals / Non-Goals

**Goals:** the show's peak reads as the biggest moment — display-wide, full-bright — no matter how the brief targeted it; the arc escalates (highs build, the peak tops them); the Director reserves the biggest look for the peak. **Non-Goals:** changing the energy/intensity model (the Director's intensities are trusted); per-prop peak choreography; making EVERY high section full-display (that would flatten the arc).

## Decisions

**D1 — Peak detection is deterministic and relative.** `peak_sections(show_plan, band=0.12)` returns indices whose `intensity` is within `band` of the max section intensity AND ≥ `PEAK_FLOOR` (0.66 — a quiet song has no "peak"). Relative, so it works regardless of absolute energy. Usually 1 section; ties (a double chorus) all qualify.

**D2 — Peak fill REPLACES the dim bed at the peak.** A new `peak_fill(section, intensity, available_groups, existing_targets)` lights the broadest available ensemble (`SEM_ALL`, else `SEM_BAND_GROUND`) across the section at FULL wash brightness (not `BED_BRIGHTNESS_FACTOR`), with the section's expanded palette. `run.py` calls `peak_fill` for peak sections and `ensemble_bed` for the rest — so 0.7–0.8 highs get the dim frame, the peak gets the lit yard. The contrast IS the escalation.

**D3 — Coverage floor at peaks.** For peak sections, the weave carrier + beat accents target the full rhythm pool + the broad ensemble even if `section.target_groups` is narrow (pass an augmented group set into the realization for those sections). Keeps the peak from collapsing onto one group.

**D4 — The climax signal lands.** `key_moment_flashes` already emits a white `On` at climax key-moments; ensure a peak section that carries no climax/accent key-moment still gets one synthesized at its downbeat, and raise the peak's `wash_brightness` ceiling slightly above neighbors so the wash itself steps up. (Small: peaks already hit wash_brightness ~180 at intensity 1.0; the lever is guaranteeing the full-display fill + flash, not a new brightness scale.)

**D5 — Director brief carries the intent; code guarantees the floor.** Prompt: "Identify the single highest-energy moment — the payoff. Give it the broadest coverage and the biggest gesture; build the section before it (rising coverage/brightness); never spend a narrow or dark look on the peak." Even if the LLM ignores it, D2–D4 enforce the floor deterministically.

## Risks / Trade-offs

- [Every high section becomes full-display → arc flattens] → peak_fill is the top band ONLY (≥0.66 and within 0.12 of max); non-peak highs keep the dim bed. Tested: a 0.7 section gets the bed, the 1.0 peak gets the fill.
- [A genuinely sparse/intimate peak (a quiet finale) gets force-lit] → PEAK_FLOOR gates it; a show whose max intensity is < 0.66 gets no fill. A loud-song peak that the artist wants sparse is rare and the brief can't currently express it — accepted; revisit if it ever bites.
- [Full-display On at the peak fights the weave's motion] → the fill is a bed UNDER the fabric (placed first, lower layer); the weave/accents ride on top via the existing layer machinery.

## Migration Plan

Additive; non-peak sections unchanged. Branch `change/add-peak-escalation`, PR (user merges).

## Open Questions

- Whether the pre-peak section should be auto-escalated (forced rising coverage) or left to the Director's build — starting with the brief note + the peak floor; revisit if builds still read flat after the peak itself lands.
