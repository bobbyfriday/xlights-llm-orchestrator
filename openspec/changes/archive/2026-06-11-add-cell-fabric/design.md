## Context

Generation today produces, per section: a few LLM wash instructions + deterministic layers (beat-accent On chase, downbeat Twinkle sparkle, hero onsets, ensemble bed, instrument features). The community audit (docs/effects-layering-analysis.md) shows real shows are instead a *fabric* of short, beat-quantized MOTION cells — ~1,300 effects/min woven from ~49 distinct designs/min, 12× reuse, motion params curved, blends and Wipe transitions set per cell. The repo already has every realization primitive the weaver needs: `section_rhythm` (beat grid per section), `effect_palette`/`expand_palette`, `resolve_buffer_style`, the value-curve serializer, `clamp_hard_caps`, and an emitter whose `_free_layer` auto-stacks overlapping placements.

## Goals / Non-Goals

**Goals:**
- Sections realized as beat-snapped motion cells expanded deterministically from ~3–6 LLM-designed `CellRecipe`s per section.
- Blend modes, motion value curves, and in/out transitions on cells, with corpus-verified settings keys.
- Bounded density scaling with intensity; deterministic fallback weave; back-compat (`weave=None` → today's stream).
- Correct the Generator prompt's false "blend modes are not settable" claim; remove the duplicated scene-note block.

**Non-Goals:** per-model pixel choreography; new preset mining; Director/scene redesign; Text/Faces; timing tracks; render order.

## Decisions

**D1 — LLM emits recipes, code expands cells.** The Generator returns `SectionEffects.weave: SectionWeave|None` with `cells: list[CellRecipe]`. The weaver (`pipeline/weave.py`, pure function) expands each recipe across the section's beat grid. Alternative — LLM emits all placements: rejected (token explosion, timing drift; the 12× repetition is mechanical). Same judgment/realization split as palettes/beats/brightness.

**D2 — CellRecipe schema (additive, all defaulted):**
```
CellRecipe: effect_type, look_id="", render_style="", role: carrier|texture|accent|bed,
            groups: list[str], cell_beats: int (1|2|4), alternation: chase|pingpong|all|sparse,
            blend="" (T_CHOICE_LayerMethod value), motion_curve="" (logical param name),
            transition="" (e.g. Wipe), palette: list[str] = [] (defaults to section palette)
SectionWeave: cells: list[CellRecipe]
```
`sparse` = every other slot (texture breathing room). `bed` role = ONE section-spanning placement (the long-bed exception), not cells.

**D3 — Expansion semantics.** Cell boundaries snap to real beats from `section_rhythm` (`cell_beats` beats per cell; trailing partial cell merges into the previous one). Targets rotate per alternation as a pure function of (slot index, groups): chase = `groups[i % n]`, pingpong = reflect, all = every group each slot, sparse = chase on even slots. Per-cell realization reuses existing helpers: `effect_palette(palette, effect_type, slot)` (color cycling across slots), `resolve_buffer_style`, `effect_speed_setting`, static brightness. Invalid groups are dropped; a recipe with no valid groups falls back to the rhythm pool.

**D4 — Density bound.** `cell_budget(intensity, section_ms) = int(section_ms/1000/60 * (BASE + intensity * SCALE))` with BASE=120, SCALE=480 cells/min (peak ≈ 600 cells/min ≈ community 1,300 scaled to our ~15-group weave surface vs their per-prop rows). Budget is split across recipes round-robin; when over budget, slots are downsampled evenly (like `_downsample`), never truncated from the front. Layer pressure capped: at most 3 concurrent woven layers per target + bed (emitter `_free_layer` handles stacking; `clamp_hard_caps` still applies).

**D5 — Blend on the upper layer only.** A recipe with `blend` set emits `T_CHOICE_LayerMethod=<v>` in `extra_settings` on its own cells; the weaver orders recipes so blended recipes land on layers >0 of a target that has a base (bed or carrier). Verified values from the corpus: Brightness, Layered, Max/Average, masks (`1 is Mask`, `2 reveals 1`, …). The emitter needs no change.

**D6 — Motion value curves: new `motion_curve_setting` (E_-prefixed).** The existing `value_curve_setting` hardcodes the `C_` prefix (brightness lives on the C_ bus); motion params ride `E_VALUECURVE_<param>`. Add `motion_curve_setting(effect_type, curve, start, end)` in `value_curves.py` with a corpus-verified key map (logical → real key + sane range):
- Spirals: rotation→`E_VALUECURVE_Spirals_Rotation`, movement→`…_Movement`
- Pinwheel: twist→`E_VALUECURVE_Pinwheel_Twist`, thickness→`…_Thickness`
- Ripple: rotation→`E_VALUECURVE_Ripple_Rotation`, twist→`…_Twist`
- Shockwave: radius→`E_VALUECURVE_Shockwave_End_Radius`, width→`…_End_Width`
- Fill: position→`E_VALUECURVE_Fill_Position`; Bars: cycles→`E_VALUECURVE_Bars_Cycles`; Wave: height→`E_VALUECURVE_Wave_Height`
Unknown (effect, curve) pairs no-op (return `{}`) — never a skip. Constant values stay static sliders (the inf/nan lesson).

**D7 — Transitions.** `transition` emits `T_CHOICE_In_Transition_Type` + `T_CHOICE_Out_Transition_Type` (+ `T_SLIDER_In/Out_Transition_Adjust=50`) — the corpus's dominant keys. Default "" = no keys (xLights Fade default).

**D8 — Beat-layer dedup.** When a weave contains a `carrier` recipe whose groups intersect the rhythm pool, `place_beat_accents` skips its every-beat chase (keeps downbeat sparkle, hero onsets, chord coloring). The carrier IS the beat-carrier — community practice (SingleStrand 26%) and the sequencing guide agree. Implemented as a `carrier_covers: bool` parameter, default False (back-compat).

**D9 — Fallback weave.** `fallback_weave(section, available_groups)`: carrier = SingleStrand chase (cell_beats=1) on the rhythm pool; texture = first motion-capable type from `section.effect_types` (cell_beats=4, sparse) on the section's non-focal groups. Used when `weave is None` **on fresh generation only** — cached instruction lists replay untouched (cells were already expanded before caching).

**D10 — Duration taxonomy v0.3.** Catalog §2.1: "sustained" → "cell-able" (default 1–2 bar cells; long-bed exceptions: ColorWash/Plasma/On in a `bed` role or on `SEM_BAND_*`/`SEM_ALL*` targets). `normalize_durations` chops non-bed placements of cell-able motion types (Spirals, SingleStrand, Pinwheel, Ripple, Wave, Bars, Butterfly) longer than 2 bars into 2-bar cells (reusing the HIT-chop machinery). Hit class unchanged.

**D11 — QA motion-share advisory.** `rules.evaluate` adds a per-section advisory finding when motion-effect share < 30% of that section's placements at intensity ≥0.5 (motion set = the cell-able list + Meteors/Fire/Garlands). Advisory only — surfaces to the Judge, never gates `objective_score` (the fabric shouldn't fight the refine loop on day one).

**D12 — Prompt surgery.** `render_input`: delete the dead first scene-note block (the one claiming "blend modes are not settable" — both blocks currently concatenate); add a WEAVE section documenting recipe fields and the carrier guidance (motion effects as carriers; SingleStrand chase canonical; On/Twinkle demoted to accent/bed roles).

## Risks / Trade-offs

- [Placement time: ~600+ cells/section peak → thousands of addEffect calls/run] → density cap is the dial; cells are tiny GETs (~10–20/s observed); accept minutes-scale placement, log progress per section.
- [LLM recipe quality varies] → every field defaulted + validated; invalid groups/effects drop to fallback; the weave can never produce a skip storm (weaver only emits placeable types from the recipe or fallback).
- [Visual overload — motion everywhere reads as noise] → roles force structure (one carrier, ≤2 textures); sparse alternation; brightness untouched (wash_brightness still scales); QA dark/coverage checks unchanged; live verdict is the user's.
- [Blend ordering wrong → masks hide everything] → blends only emitted when the recipe's target also gets a base layer that section; hermetic test asserts layer ordering; live .xsq inspection in verification.
- [Curve ranges wrong per param] → ranges frozen in the key map from corpus observation; unknown pairs no-op.
- [Doubling with place_beat_accents] → explicit dedup decision D8 with a default that preserves today's behavior when no weave exists.

## Migration Plan

Additive throughout; `weave=None` reproduces today's stream. Old caches replay unchanged. Rollback = Generator stops being asked for weaves (prompt revert) — the weaver simply never runs. Catalog §2.1 edit ships with the code that enforces it.

## Open Questions

- Density constants (BASE/SCALE) may need one live tuning pass after the first candy-cane run — treat as tunable constants, not spec.
- Whether scene-stack sections should suppress the fallback weave (scene rows may already provide the carrier) — initial answer: scene sections still weave, but the carrier recipe should be the scene's rhythm row when the Generator follows the prompt; revisit on live evidence.
