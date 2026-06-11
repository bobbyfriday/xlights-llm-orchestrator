## Why
The guide: *"reuse the chorus motif so viewers recognize it, but escalate — chorus 1: 70% of props, chorus 2: 90%, final: 100% + accents; the last chorus should be the biggest."* We have the brief's `repetition_map` (which sections recur) but treat every recurrence identically. This escalates later recurrences so the show builds.

## What Changes
- An **escalation level** per section from `repetition_map`: the k-th of n occurrences of a recurring label gets level `k/(n-1)` (0 for first, 1 for last).
- Apply it as an **effective-intensity boost** so later recurrences are brighter (#2) and light more props (#3) — the final chorus is the biggest. Reuses the existing energy levers; no new effect plumbing.

**Non-goals:** the motif (same effect/color) reuse — that's the guide-injected Director's job; beat-density escalation (could fold in later); cross-song identity.

## Capabilities
### Modified Capabilities
- `show-orchestration`: recurring sections escalate across the show (later recurrences brighter and fuller), so repeated choruses build to a peak instead of repeating flat.

## Impact
- **`xlights-orchestrator`**: an `escalation_level` helper + an effective-intensity boost in `run.py` (both generate sites) using `st.music_brief.repetition_map`.
- **Builds on** the brief's `repetition_map`, #2 (brightness), #3 (coverage).
