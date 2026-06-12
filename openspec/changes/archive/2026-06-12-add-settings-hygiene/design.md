## Context

Three log-confirmed defects: a speed key that only exists for some effects (feature silently dead elsewhere + per-click UI errors), a stale key shipped by 125 mined looks (removed from current xLights), and SEM_ groups rendering group-canvas effects through a downscaled 400px buffer (default GridSize) with per-render WARN spam. The third is a quality prerequisite for add-led-readability's group-canvas sweeps.

## Goals / Non-Goals

**Goals:** intensity→speed works on every effect that has a speed concept, via its real parameter and observed value range; no placements carry keys current xLights lacks; SEM_ group buffers render at native extent. **Non-Goals:** re-mining the corpus; translating stale keys to their modern successors (drop, don't migrate); touching user-authored groups' GridSize.

## Decisions

**D1 — `SPEED_KEYS`: per-effect (key, lo, hi, fmt), ranges from the corpus** (observed values just surveyed):
- Sliders (int): Meteors 10–45, Pinwheel 5–20, Butterfly 8–40, Marquee 1–8, Plasma 70–90, Snowflakes 10–25, Circles 5–25, Snowstorm 10–30, Tree 5–20, Warp 5–30
- Cycles/textctrl (float, 1 decimal): Color Wash 1–6, On 2–8, Bars 0.5–4, Garlands 1–4, Ripple 1–8, Shimmer 4–12, Wave (Speed textctrl) 5–35, Curtain 0.5–4, Spirals (`_Movement`) 0.5–4
- No entry (emit nothing): SingleStrand (chase pace is governed by cell length + chase type), Twinkle, Strobe, Lightning, Shockwave, Fill, Fan, Galaxy, Fire, Liquid, Kaleidoscope, Shape, VU Meter…
`effect_speed_setting(effect_type, intensity)` keeps its signature; value = lo + (hi−lo)·intensity, slider→int, textctrl→1-decimal float.

**D2 — `DROP_KEYS` strip at assembly** (`place_preset`'s settings build): keys absent from current xLights are removed from the look's settings before send. Seed: `E_CHECKBOX_Chase_3dFade1`. Single list in `editing.py` — future stale keys get one-line additions when logs surface them.

**D3 — GridSize on SEM_ groups**: `patch_rgbeffects` computes each SEM_ group's needed grid (max of member bounding extents, as xLights computes its minimalGrid) — implementation may approximate by counting member pixels/coordinates; pragmatic approach: set `GridSize` to min(1200, max(400, observed warning sizes ≈ next-hundred above actual)). Since exact extent math duplicates xLights internals, simplest correct-enough rule: SEM_ groups get `GridSize="1200"` flat (covers the largest observed 1144; render cost only applies to group-canvas effects, which are the point). Idempotent; only `SEM_` groups touched; requires the usual xLights restart to load.

**D4 — Regen note:** speed now actually changes for Cycles-class effects; shows regenerate slightly differently by design. No cache invalidation needed (settings are computed at expansion, cached instruction streams keep old keys until a regen — acceptable drift; the stale-key strip applies at PLACEMENT so even cached streams stop erroring).

## Risks / Trade-offs

- [Cycles semantics ≠ speed exactly (a 2-cycle Color Wash over a long bed = slow; over a cell = fast)] → ranges chosen from community-observed values; cells are short so cycles read as pace; live look is the gate.
- [GridSize=1200 raises render cost] → only group-canvas buffers; bounded; xLights' own warning exists to flag the *mismatch*, not to forbid larger grids.
- [Dropping Chase_3dFade1 changes a look's render?] → the key doesn't exist in current xLights; it was already non-functional. Dropping only silences the UI error.

## Migration Plan

Stacks on `change/add-directional-sweeps` (same PR train; user merges in order). GridSize takes effect after the next xLights restart; everything else immediately.

## Open Questions

- Whether to scan all looks for OTHER current-xLights-missing keys proactively (a probe placing one look per type and diffing readback) — deferred; the DROP list grows from logs.
