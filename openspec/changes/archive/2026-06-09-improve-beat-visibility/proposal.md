## Why

Looking at the rendered show, two things stood out:

1. **Beats are invisible** — the beat accents use the *same* palette as the wash they sit on (confirmed: every section, e.g. sec 3 wash `[Gold, Deep Blue]` == accent `[Gold, Deep Blue]`). A flash the same color as its background doesn't read.
2. **Beats look "once per bar"** — `place_beat_accents` caps at 24 accents, then chases across the 4 `04_BEAT_*` groups: ~32 beats/section → 24 → **6 per group** → each prop flashes ~once per bar, and ~25% of beats get nothing. It *is* the beat grid, but the cap + 4-way split thin it out.

This change makes the beats **pop** (a contrasting accent color) and **read as beats** (one on ~every beat, with the bar marked).

## What Changes

- **Base/accent palette split** (`split_palette` in `knowledge/colors.py`): rank the section's colors by luminance; the **wash uses the base** (calmer/darker), the **beats use a distinct brighter accent** (e.g. wash Deep Blue, beats flash Gold). A single-color section gets a brightened accent so it still contrasts.
- **Every-beat chase**: place an accent on ~every beat (raise the cap so a normal section isn't downsampled), rotating the group each beat — a real 1‑2‑3‑4 sweep — with a sane upper bound so a long section still can't explode.
- **Downbeat emphasis**: bar starts (every 4th beat, derived 4/4) flash **all** `pulse_groups` together; the in-between beats are the single-group chase — so the bar structure reads.

**Non-goals (next change, `rhythmic-musicality`):** onset-driven hits, chord-driven color shifts, energy-scaled density. Also out: changing the wash effect/look, per-stem color, new effect types.

## Capabilities

### Modified Capabilities
- `show-orchestration`: beat accents use a color that contrasts the wash, are placed on ~every beat (bounded), and emphasize bar starts — so the rhythm is both visible and reads as the beat.

## Impact

- **`xlights-orchestrator`**: `split_palette` in `knowledge/colors.py`; `beats.py` density/chase/downbeat logic; the run.py code-pass applies `base` to the wash and `accent` to the beat layer (replacing the single shared `section.palette`).
- **Builds on** palette realization (`palette_from_colors`, `NAMED_COLORS`) and the beat layer. Keeps the mined-palette fallback. Directly addresses the two issues seen in the rendered show.
