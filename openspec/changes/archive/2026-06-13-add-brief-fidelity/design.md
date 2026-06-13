## Context

`run.py` generation places the Generator's brief effects, then unconditionally adds: the weave
(LLM recipes, else `fallback_weave`), `place_beat_accents`, `ensemble_bed`/`peak_fill`, triggers,
flashes. `fallback_weave` calls `rhythm_pool(section, available)`, which builds from `pulse_groups`
then **injects** `RHYTHM_POOL` (SEM_ARCHES/CANES/MINITREES) to reach ≥3 groups — even when the brief
left them out. That injection + the always-on beat accents are what override a deliberately-quiet
section (Christmas Canon §0: pulse_groups empty, intensity 0.2 → 112 injected chases + 88 pops).

## Goals / Non-Goals

**Goals:** deterministic rhythm layers respect the brief — fire only where the brief opts into
rhythm, and don't light excluded groups; quiet/still sections render as directed. **Non-Goals:**
guaranteeing the chosen effect lands (acceptable exception, per direction); changing energetic
sections; touching the LLM's own weave (its realization of the brief is honored).

## Decisions

**D1 — `section_is_rhythmic(section)` is the gate.** True when the brief opts into a beat layer:
- `pulse_groups` is non-empty (explicit beat-layer request), OR
- `target_groups` intersects the rhythm pool (the brief chose rhythm props), OR
- `intensity >= RHYTHM_FLOOR` (≈0.35 — an energetic section is rhythmic by nature).
Otherwise False: a quiet section with no rhythm groups requested is deliberately still.

**D2 — `rhythm_pool` stops injecting beyond the brief.** Build from `pulse_groups ∩ available`;
else rhythm-capable groups in `target_groups ∩ available`; else inject the default `RHYTHM_POOL`/
`SIDE` groups **only when the section is rhythmic**. Non-rhythmic + nothing chosen → `[]` (no
deterministic rhythm groups). This is the core change — the brief's group choices are honored.

**D3 — `fallback_weave` is empty for non-rhythmic sections.** No synthesized carrier/texture; the
section shows the LLM's own instructions (glow + the chosen effect). The fallback exists to prevent
*dead* sections — but a still section the brief asked for is not dead.

**D4 — beat accents gated.** `run.py` calls `place_beat_accents` only when `section_is_rhythmic`.
(The hero-onset feature layer and key-moment flashes are separate and unchanged — they're already
intensity/onset-gated and tied to explicit moments, not blanket rhythm.)

**D5 — LLM weave honored as-is.** If the Generator emitted a weave (its realization of the brief),
it still expands. We only stop CODE from synthesizing rhythm the brief didn't ask for. So fidelity =
"the brief and the LLM drive; deterministic layers fill in only where invited."

## Risks / Trade-offs

- [A section meant to be lively but with intensity just under the floor and no pulse_groups goes too quiet] → three independent opt-ins (pulse_groups OR rhythm target groups OR intensity≥floor); a genuinely lively section clears at least one. Floor tunable.
- [Quiet sections now look too sparse] → they still get the section wash (On/ensemble), the LLM's chosen effects, the hero-onset feature, and any LLM weave — just not injected chases/pops. That's the intended stillness.
- [Regressions in carol/candy/DJ energetic shows] → those sections are rhythmic (high intensity / rhythm targets) → unchanged. Verify no drop in their objective.

## Migration Plan

Additive gate; energetic sections unchanged. Branch `change/add-brief-fidelity`, PR (user merges).
Re-verify Christmas Canon (the still intro) + a known energetic show (no regression).

## Open Questions

- `RHYTHM_FLOOR` exact value (0.35 start) — tune if a mid-energy section reads too quiet.
- Whether to also constrain the LLM weave / beat accents to `target_groups` in rhythmic sections (stop lighting excluded groups even when energetic) — deferred; the quiet-section fix is the reported problem.
