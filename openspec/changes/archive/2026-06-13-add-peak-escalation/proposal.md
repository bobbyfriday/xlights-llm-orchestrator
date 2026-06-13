## Why

The one critic complaint that has survived every change: the climax looks like a busier verse, not a bigger moment. Grounded in carol's latest run — the peak section (sec6, **intensity 1.00**) targets only **1 group**: the Director spent a narrow "split" scene on the payoff, so "half the yard remains completely dark" exactly when it should be fullest. And a 0.81 *build* section reads "as dark and slow as the intro." Two gaps: peaks don't guarantee display-wide coverage, and nothing escalates into or at the peak. The dim single-band `ensemble_bed` (ground only, 60% brightness) is not enough to make a peak read as lit.

## What Changes

- **Peak detection (code):** `peak_sections(show_plan)` = the section(s) within a small band of the show's max intensity — the payoff moment(s), identified deterministically.
- **Peak fill (code):** at a peak section, light the FULL display (SEM_ALL / broad ensemble) at full wash brightness — not the dim 60% band bed — so the yard reads alive even when the Director under-targets. The dim band bed stays for merely-high (≥0.7) non-peak sections, preserving the arc.
- **Coverage floor at peaks (code):** the realized peak covers the rhythm pool + full display, not just the Director's named target_groups.
- **Escalation signal (code):** ensure the climax key-moment treatment lands at the peak (the existing white flash fires there; the peak's wash brightness ceiling is raised above neighbors).
- **Director brief (LLM):** name the show's single peak; reserve the broadest coverage and biggest gesture for it; the section before it should build (rising coverage/brightness into the peak) — don't spend a narrow or dark scene on the payoff.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `show-orchestration`: the show's peak section(s) SHALL be realized as the visual payoff — display-wide coverage at full brightness regardless of how narrowly the brief targeted them — and the creative brief SHALL reserve the broadest, biggest look for the peak and build into it; merely-high sections SHALL stay below the peak so the arc escalates.

## Impact

- `pipeline/beats.py` (peak_sections, peak_fill; ensemble_bed stays for non-peak highs), `pipeline/run.py` (apply peak fill + coverage floor in generate + regen), `agents/director.py` prompt.
- Back-compat: sections below the peak band are unchanged; a flat-intensity show (no clear peak) gets no peak fill.
