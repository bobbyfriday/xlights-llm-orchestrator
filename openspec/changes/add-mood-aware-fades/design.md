## Context

The cell weaver (`pipeline/weave.py`) expands a few LLM-designed `CellRecipe`s into hundreds of
beat-snapped cells. Each cell occupies an abutting beat span `[beat_i, beat_{i+1})` and is placed
with no fade, so cells turn fully on at their start and fully off at their end. On energetic
sections this crisp edge is correct (it reads as rhythm); on low-energy / introspective sections
it reads as "rapid erratic flashing" — the exact defect the Judge flagged on Christmas Canon
verses 4 & 5 and could not fix, because the brief was fine and only the *realization* was wrong.

What already exists:
- `_cell()` (weave.py:286–290) emits `T_CHOICE_In/Out_Transition_Type` + adjust=50 **only** when
  a `CellRecipe.transition` is set — which the generation LLM rarely does. Dormant, not wrong.
- Layer blend (`T_CHOICE_LayerMethod`) is actively used (cells `Max` over a bed). Not the gap.
- Effect-level **fades** (`T_TEXTCTRL_Fadein/Fadeout`, in seconds) are never synthesized by code.
- `SectionPlan.intensity` (0..1) is already set per section by the Director.
- Synthesized settings already flow via `EffectInstruction.extra_settings → place_preset`.

Constraint from xLights: two effects cannot overlap in time on a single layer. A true crossfade
(both cells lit, blending) therefore requires alternating cells across two layers/groups. This is
why real overlap is deferred to phase 2 — phase 1 stays single-layer and uses fades only.

## Goals / Non-Goals

**Goals:**
- Give the Director an explicit, optional per-section dial for phrasing (legato vs staccato).
- Realize legato phrasing as soft effect-level fades (and longer cells) deterministically in code.
- Default phrasing from `intensity` so undirected and cached plans behave well with no LLM change.
- Keep energetic sections crisp (no regression to the current staccato behavior at high intensity).
- Fully hermetic tests for the mapping, the default, and the fade math.

**Non-Goals:**
- True overlapping cross-layer crossfade (phase 2; noted below, not built here).
- Changing layer blend, the cell budget, or the beat-accent / sparkle / trigger layers.
- Exposing the **full** xLights transition menu (Wipe/Clock/Bars/Star/Zoom/Pinwheel/…), or any
  Director-level transition-*type* selection. The Director picks mood only; code picks from a
  curated two-option primitive (Fade, Dissolve). The shaped reveals are excluded because they do
  not read on sparse pixel props (arches/canes/mini-trees lack the pixels to show the shape).
- Per-cell LLM control of fade milliseconds or transition adjust — numbers stay in code.

## Decisions

**1. Phrasing is a `SectionPlan` field owned by the Director, not a `CellRecipe` field.**
The judgment "this section is introspective, let it evolve" is a section-level mood call, which is
the Director's job; the Generator/weaver should not each re-decide it per recipe. So add
`SectionPlan.phrasing: str = ""` with the contract `"legato" | "staccato" | ""`.
*Alternative considered:* put it on `CellRecipe`. Rejected — it would scatter one mood decision
across 3–6 recipes and bypass the Director, and cached plans without it would lose the default.

**2. The weaver resolves phrasing once per section, with an intensity-derived default.**
`expand_weave()` computes `resolved = phrasing or ("legato" if intensity < THRESHOLD else
"staccato")`. A single threshold (start at `intensity < 0.5`, the same band QA already uses for
"energetic") keeps it predictable and testable. This means a blank/old plan still softens quiet
sections automatically.
*Alternative considered:* a continuous fade fraction = f(intensity) with no enum. Rejected for
phase 1 — harder to direct explicitly and harder to assert in tests; the enum + default gives the
Director a clean handle and a deterministic mapping. (A continuous curve can layer on later.)

**3. Legato is realized by a curated soft-edge primitive chosen in code from the effect family —
not a single hardcoded fade.** A pure helper `soft_edge_settings(effect_type, cell_len_ms,
phrasing) -> dict` returns the realization:
- **staccato** → `{}` (identical to today → no regression).
- **legato, line/chase/point effects** (SingleStrand, Butterfly, On, Twinkle, Bars, …) → a linear
  opacity fade: `fade_s = round(min(MAX_FADE_S, FADE_FRACTION * cell_len_s), 2)` on both
  `T_TEXTCTRL_Fadein` and `T_TEXTCTRL_Fadeout` (seconds, xLights' unit). Start `FADE_FRACTION ≈
  0.35`, cap `MAX_FADE_S`.
- **legato, textural fill/wash effects** (Plasma, Fill, Color Wash, Shimmer, …) → a `Dissolve`
  transition: `T_CHOICE_In/Out_Transition_Type = "Dissolve"` with `T_SLIDER_In/Out_Transition_Adjust`
  set from the same fade fraction — a grainy melt-in/out that reads better than a flat opacity ramp
  on a full-canvas texture.

The effect-family → primitive map is a small curated constant (defaulting unknown families to the
linear fade, the safe choice). Both primitives produce the same "evolving" intent; code owns which
one and all numbers.

*Precedence:* an explicit `CellRecipe.transition` set by the Generator still wins — the existing
`_cell()` transition-type path is left intact, and the phrasing-derived primitive only fills in
when the recipe named no transition. So the Generator can still override per recipe; phrasing is
the mood-level default.

*Alternatives considered:* (a) only ever emit `Fadein/Fadeout` — rejected, a flat opacity ramp on a
full-canvas texture reads as a dip, not an evolution; Dissolve suits textures. (b) Expose the full
transition menu / let the Director pick the type — rejected per Non-Goals (shaped reveals don't read
on sparse pixel props, and type selection is realization, not judgment).

**4. Legato lengthens the effective cell.** Short one-beat cells can't "evolve." For legato,
raise the effective `cell_beats` floor (e.g. `max(recipe.cell_beats, 2)`) so fades have room and
fewer, longer cells replace the staccato chatter. Density stays inside the existing intensity
budget (quiet sections already weave sparsely), so this reduces, never inflates, placement count.

**5. Director prompt gains a short phrasing instruction** tied to the existing per-section look /
intensity guidance, so the Director sets `phrasing` deliberately (e.g. legato for melancholy
verses) but is free to omit it and rely on the energy default.

## Risks / Trade-offs

- **Dip-to-black between abutting legato cells** → Phase-1 fades fade each cell out then the next
  in, so a same-target legato run momentarily dims at boundaries. Mitigation: lengthening cells
  (decision 4) makes boundaries rare, and the "evolving" dip actually suits melancholy. True
  crossfade is phase 2.
- **Over-softening kills rhythm if the threshold is wrong** → Mitigation: default only triggers
  below the 0.5 energetic band; energetic sections are untouched; threshold is a single constant
  to tune and is asserted in tests. Live-verify on Christmas Canon 4/5 (legato) and a peak
  (must stay staccato).
- **Fade seconds vs cell length units** → cell spans are ms internally; fades are seconds in
  xLights. Mitigation: convert explicitly and test the ms→s math and the `MAX_FADE_S` cap.
- **Cached plans lack `phrasing`** → additive defaulted field + intensity fallback means old
  caches still benefit; no cache invalidation needed.

## Open Questions

- Exact `FADE_FRACTION`, `MAX_FADE_S`, and the legato `cell_beats` floor — seed with 0.35 / a few
  seconds / 2 beats, then tune against the live render of verses 4/5.
- The exact effect-family → primitive split (which effects count as "textural" and get Dissolve vs
  the linear fade) — seed from the effects-catalog families, refine against the render. Dissolve's
  visible graininess on sparse props should be sanity-checked live before widening its use.
- Whether the long bed cell should also carry a gentle fade-in at section entry (likely yes, small)
  — settle during implementation against the render.
