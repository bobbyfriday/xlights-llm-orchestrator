## Why

The show doesn't always match its own creative brief. Grounded example — Christmas Canon section 0: the brief calls for *"a perfectly still, frosty night… faint blue glow… slow falling snowflakes"*, intensity 0.2, `target_groups: [SEM_ALL, SEM_SNOWFLAKES]`, `pulse_groups: []`, scene SC-09 *"rhythm groups remain dark."* What actually rendered: **112 SingleStrand chases on the rhythm pool** (arches/canes/mini-trees — groups the brief excluded) plus **88 beat-accent On pops** — yellow/blue motion instead of still falling snow.

Cause: the deterministic "musicality" layers run **unconditionally on every section**, after the Generator places the brief's effects. The **fallback weave** synthesizes a chase on the rhythm pool even when the brief asked for none, and the **beat-accent layer** fires regardless of intensity or intent. They were built to prevent *dead* sections but can't tell a deliberately-still intro from a dead one — so they bury the creative direction.

## What Changes

- **Gate the deterministic rhythm layers on the section's brief intent.** A section is "rhythmic" only when the brief opts in — it sets `pulse_groups`, includes rhythm-pool groups in `target_groups`, or its intensity clears a floor. For non-rhythmic (deliberately quiet/still) sections:
  - the **fallback weave** is not synthesized (the LLM's own weave, if any, still expands);
  - the **beat-accent chase** does not fire.
- **The deterministic rhythm pool stops injecting groups the brief excluded.** `rhythm_pool` builds from `pulse_groups` / rhythm groups the brief actually chose, and only falls back to the default pool when the section is rhythmic.
- This makes a still intro render as the brief promises (glow + the chosen Snowflakes), rhythm props dark.

**Not in scope (per direction):** *guaranteeing* the brief's chosen effect lands. We should use the chosen effects in most cases, but a chosen effect not appearing is an acceptable exception, not a failure to fix.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `show-orchestration`: the deterministic rhythm layers (fallback weave, beat-accent chase) SHALL respect each section's brief intent — firing only where the brief opts into rhythm (pulse groups, rhythm target groups, or sufficient intensity) and not lighting groups the brief excluded — so deliberately quiet/still sections are realized as directed.

## Impact

- `pipeline/beats.py` (`section_is_rhythmic` helper; beat-accent gating) and `pipeline/weave.py` (`rhythm_pool` respects brief groups; `fallback_weave` empty when non-rhythmic).
- `pipeline/run.py` (generate + regen: gate the fallback weave + beat accents).
- Back-compat: energetic / pulse-group / rhythm-target sections are unchanged (they're rhythmic); only deliberately-quiet sections change — which is the fix.
