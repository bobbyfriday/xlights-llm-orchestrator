## Context

`place_beat_accents` colors accents with `section.palette` (== the wash) and caps at 24, chasing 4 groups → 6/group → once-per-bar-per-prop, low contrast. We have `NAMED_COLORS` (name→hex) so luminance is computable; `SectionPlan.palette` and the run.py wash code-pass (`ins.palette_colors = section.palette`) are the seams.

## Goals / Non-Goals

**Goals:** beats contrast the wash (base/accent color split); an accent on ~every beat (bounded); downbeats emphasized. Deterministic, hermetic-testable, bounded count.

**Non-Goals (next change):** onsets, chord→color, energy-scaled density. Also: wash effect/look, per-stem color, new effect types.

## Decisions

### `split_palette(colors) -> (base, accent)` (`knowledge/colors.py`)
Resolve each color to hex (via `_resolve`/`NAMED_COLORS`); luminance `L = 0.299R+0.587G+0.114B`.
- **≥2 colors:** `accent = [brightest]`; `base = the rest` (the darker/calmer colors). e.g. `[Gold(202), Deep Blue(16)]` → base `[Deep Blue]`, accent `[Gold]`.
- **1 color:** `base = [c]`; `accent = [_brighten(c)]` — blend ~65% toward white for a brighter flash (already-bright colors stay light; that's fine for a calm mono section).
- **none resolvable:** `([], [])` — callers fall back to today's behavior (single `section.palette`).
Returns hex lists (which `palette_from_colors` accepts via hex passthrough).

### Apply base→wash, accent→beats
- run.py wash code-pass: `base, _ = split_palette(section.palette); ins.palette_colors = base or section.palette` (fallback if split empty).
- `place_beat_accents`: `_, accent = split_palette(section.palette)`; the beat instructions get `palette_colors = accent or section.palette`. So a 2-color section renders the wash and the beats in **different** colors.

### Every-beat chase + downbeat emphasis (`place_beat_accents`)
- Times = the section's beats (default), **not** downsampled unless the count exceeds a higher `MAX_ACCENTS_PER_SECTION` (raise 24 → ~80 upper bound; downsample only past that).
- For the i-th beat: if it's a **bar start** (`i % BEATS_PER_BAR == 0`) → emit an accent on **every** `pulse_group` at that time (a bigger simultaneous hit); else → emit one accent on the **rotating** group (`pulse_groups[i % len]`). So motion every beat + a fuller hit on the downbeat.
- Count: ~32 beats → ~8 downbeats×4 groups + ~24×1 ≈ 56/section (≤ the ~80 bound). The upper bound still caps pathological sections.

### Bound
`MAX_ACCENTS_PER_SECTION` becomes the hard upper bound (~80). If the assembled accents exceed it, downsample the off-beat (non-downbeat) accents first so downbeats survive.

## Risks / Trade-offs

- **Higher effect count** — ~56/section × 14 ≈ ~780 accents + washes (~800 total vs 363). Placement ~16–24s; we've placed hundreds fine. The ~80/section bound + downbeat-priority downsample cap it; the live check asserts the total stays sane and nothing skips.
- **Low-contrast palettes** — `[Amber, Gold]` (188/202) splits but barely contrasts; acceptable (the brighter still pops slightly), and energetic sections tend to have wider spreads (`Gold/Deep Blue`). Calm mono sections get a subtle brightened accent — appropriate.
- **Visual busyness** — every-beat + downbeat hits could look busy in quiet sections; energy-scaled density (next change) will calm those. For now uniform; the visual critic will flag if overdone.
- **Wash loses a color** — giving the wash only `base` (dropping the bright color to the beats) could make a wash duller; acceptable (the beats now carry the bright color, and the wash keeps the mood color). Fallback to full palette if split empty.

## Open Questions

- `_brighten` blend factor and whether mono sections should instead use a complementary hue — start with brighten-toward-white; revisit if mono sections look flat.
- Whether the downbeat hit should also be longer/brighter (not just more groups) — keep to "more groups" now; brightness/length scaling can come with the energy pass.
