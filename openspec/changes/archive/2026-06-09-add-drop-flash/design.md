## Context
`ShowPlan.key_moments: list[KeyMoment{at_ms, kind, treatment}]` (kind ∈ accent|climax|lyric). The targetable groups are `st.available_groups`. White = a bright neutral that reads on any wash.
## Goals / Non-Goals
**Goals:** brief white flash across many groups at climax/accent moments; bounded. **Non-Goals:** pre-flash blackout; strobe; lyric-moment flashes (that's #7); call-and-response (existing pulse_groups).
## Decisions
### `key_moment_flashes(show_plan, available_groups) -> list[EffectInstruction]`
For each key_moment whose kind ∈ {climax, accent, drop, hit}, place a `FLASH_MS`≈150ms `On`/`On#0` at `at_ms` on each group in `available_groups` (capped to `FLASH_GROUPS`≈24 to bound count), `palette_colors=["white"]`, full brightness via `extra_settings` value-curve Brightness (e.g. 300). Tag `section_index=None`. Skip lyric-only kinds (those are #7). Bound total moments (e.g. top 8 by some order) so the count stays sane.
### Wiring
After all sections are generated in run.py, `instrs += key_moment_flashes(st.show_plan, st.available_groups)`.
## Risks / Trade-offs
- **Count** — moments×groups; cap groups (24) + moments (8). White flash at full brightness is brief.
- **Overlap with wash** — the flash is a separate layer (emitter bumps layers); 150ms over the wash reads as a hit.
- **"white" resolves** — `palette_from_colors(["white"])` → #FFFFFF (in NAMED_COLORS).
## Open Questions
- Pre-flash blackout (clear beat accents ~250ms before) — defer.
