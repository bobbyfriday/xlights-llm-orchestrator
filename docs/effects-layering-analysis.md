# Critical Analysis: Our Effects & Layering vs. Community Practice

*2026-06-11. Data: 130,229 effects mined from the 17 community/vendor `.xsq` in the show folder,
vs 2,265 effects across our two generated shows (Candy Cane Lane, Mad Russian Christmas).*

## 1. The fabric is inverted — motion vs punctuation

| | community | ours |
|---|---|---|
| continuous-MOTION effects (SingleStrand, Spirals, Pinwheel, Ripple, Wave, Bars) | **~58%** | **~16%** |
| punctuation/static fills (On, Twinkle, Strobe, Shockwave, Lightning, Shimmer) | ~31% | **~83%** |
| `On` alone | 3% | 22% |
| `Twinkle` alone | <1% | 23% |
| `Spirals` | 10% | ~0.5% |

Community shows are **woven from motion** — chases are the single biggest family (26%!). Ours is
**pulses over a thin bed**: our deterministic layers (beat accents = On, sparkles = Twinkle,
features = Lightning) dominate the count while the motion fabric barely exists. This is the
"it's just kind of there, moving around" feeling, quantified.

## 2. Everything is short — there are no washes in community practice

Median durations across **all** top community effects: **0.3–0.9s** (p90 ≤ ~2–3s). Even Spirals
(0.6s), Wave (0.6s), Pinwheel (0.9s) — the effects our duration taxonomy classed "sustained" —
are placed as **beat/bar-quantized cells, continuously re-decided**. Community density:
**~1,300 effects/min** typical (up to 3,200) vs our ~270. Our 49–88s washes simply do not exist
in community sequencing. (Our hit-class fix was right — community Shockwave median is 0.3s,
matching our converted cells — but the "sustained = unbounded" class was wrong as *practice*:
sustained-capable ≠ sustained-used.)

## 3. Blend modes are used — and they ARE settable (false assumption #4)

Community blends: **Brightness 36%, Layered 23%, masks/unmasks ~16%, Effect 1 8%** — the layering
guide's recipes in live use. We set none. The claim "blend modes are not settable via addEffect"
(baked into the Generator prompt) was **re-tested today and is FALSE**: `T_CHOICE_LayerMethod=Max`
round-trips perfectly through `addEffect` (T_ keys ride the settings string like B_/E_/C_).

## 4. Value curves shape MOTION there, brightness here

Community curved params: **Rotation 30%, Spirals_Rotation 14%, Fill_Position 7%, Pinwheel_Twist
7%, Shockwave_End_Radius/Width 8%** — the expanding ring IS a curved radius. Ours: **66%
Brightness**. We shape loudness; they shape movement.

## 5. Other gaps

- **Transitions:** community cells carry Wipe (68% of non-fade) / Circle Explode / Fold in-out
  transitions; we set none.
- **Layer depth:** community hero rows stack up to 19 layers; 22% of rows are multi-layer.
  Ours max 4.
- **Sparkle slider:** essentially unused both sides (community uses Twinkle layers instead — as
  rare accent, not 23% of the show).

## 6. Recommendations (ordered)

1. **Cell-woven fabric (the paradigm fix):** sections composed of beat/bar-quantized MOTION cells
   (chases, spirals, ripples, waves, pinwheels) alternating across groups — not long washes +
   pulses. Deterministic weaver + Generator guidance; target ≥3× current density. Demote
   On/Twinkle to the rare accents they are in practice (our beat-carrier should be **SingleStrand
   chase cells** — the community's #1 effect and the guide's "canonical beat-carrier").
2. **Blend modes via `extra_settings`** (now proven settable): Max for sparkle overlays,
   Brightness for envelopes; correct the Generator prompt; cookbook stacks become realizable.
3. **Motion value curves:** curve Rotation/Twist/Position/Radius on cells per the catalog's "key
   parameters" — not just brightness.
4. **Cell transitions:** Wipe/dissolve in-out on cells for flow between them.
5. Revisit the duration taxonomy: hit ≤1 bar stays; "sustained" becomes "cell-able" (default
   1–2 bar cells) with explicit long-bed exceptions (Color Wash/Plasma beds only).

## Vindications

- The hit-class duration fix matches community practice exactly (Shockwave 0.3s).
- Our render-style distribution (Per-Model heavy) is in line with community (44% Per-Model
  variants there).
- Scene cookbook + subtractive groups point the same direction as vendor group lists.
