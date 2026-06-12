## Context

Cells light their target groups uniformly and have no notion of direction — every beat fires the same way. User feedback (Carol of the Bells): alternate the beats — left to right, right to left, bounce, out from center, into center, up/down. The direction belongs to the EFFECTS' OWN SETTINGS (user decision — no grouping changes): the mined looks carry a complete, corpus-observed direction vocabulary per effect (SingleStrand Chase_Type1 incl. Bounce from Left/Right/Middle, Dual Bounce, From/To Middle; Bars up/down/expand/compress/H-expand/H-compress; Garlands directional + built-in bounces; Meteors Up/Down/Explode/Implode; Fill/Wave/Curtain/Butterfly/Marquee/Fan/Galaxy/Pinwheel direction or reverse knobs). All values are valid by construction (observed in community .xsq).

## Goals / Non-Goals

**Goals:** per-recipe `direction` realized purely through effect-native settings; per-bar direction alternation for effects whose knobs are static (Fill/Wave/Meteors); bar-alternating beat-accent rotation order; LLM-directable with a sweeping deterministic default; graceful no-op when an effect has no mapped knob.

**Non-Goals:** ANY grouping/target changes (no `_LTR` substitution, no buffer-style forcing — explicitly rejected by the user); new ensembles; per-model targeting; radial matrix work; peak coverage balance (separate change).

## Decisions

**D1 — A per-effect DIRECTION_KNOBS map (settings-only realization).** `direction ∈ {ltr, rtl, bounce, center_out, center_in, up, down}` → `(key, value)` per effect type, values strictly from the corpus:
- SingleStrand `E_CHOICE_Chase_Type1`: ltr→Left-Right, rtl→Right-Left, bounce→Dual Bounce (variants Bounce from Left/Right rotate per slot for variety), center_out→From Middle, center_in→To Middle
- Bars `E_CHOICE_Bars_Direction`: up/down→up/down, ltr→Right (xLights "Right" = movement to the right)/rtl→Left, center_out→H-expand, center_in→H-compress (vertical props: expand/compress)
- Garlands `E_CHOICE_Garlands_Direction`: ltr→Right, rtl→Left, up/down→Up/Down, bounce→"Left then Right"/"Up then Down"
- Meteors `E_CHOICE_Meteors_Effect`: up/down→Up/Down, center_out→Explode, center_in→Implode
- Fill `E_CHOICE_Fill_Direction`, Wave `E_CHOICE_Wave_Direction`, Curtain edge+effect, Butterfly/Marquee/Fan/Galaxy Reverse, Pinwheel `E_CHECKBOX_Pinwheel_Rotation` (bounce→alternate CW/CCW per bar)
Unknown (effect, direction) pairs emit nothing — never a skip.

**D2 — Bounce = the effect's native bounce when it has one; otherwise a per-bar VALUE flip.** SingleStrand/Garlands bounce inside the effect. Fill/Wave/Meteors/Bars have static directions → `bounce` alternates ltr/rtl (or up/down for vertical-natured effects) at bar boundaries (bar = 4 beats, slot·cell_beats//4). Within a bar, direction is constant.

**D3 — Beat accents alternate rotation order per bar** (`place_beat_accents`): even bars walk the group list forward, odd bars backward. Group order is already spatial. Deterministic; no LLM surface.

**D4 — LLM directs; the fallback sweeps.** `CellRecipe.direction` documented in the generator prompt (builds→up, releases→down, call-and-response→bounce/ltr+rtl pairs). `fallback_weave` carrier gets `bounce`. `direction=""` expands byte-identically to today.

**D5 — Knobs ride `extra_settings`** — the emitter's duplicate-key override already gives them precedence over the look's frozen values. One live round-trip sanity check (a Bounce from Left placement read back) — values are corpus-observed so no acceptance probe is needed.

## Risks / Trade-offs

- [A direction knob means something different on some buffer styles] → values are corpus-observed in real shows on real groups; live re-run is the gate.
- [Per-bar flips on candy's 4-bar choruses = 4 flips/8s] → native bounce types (Dual Bounce etc.) carry most of the load; the per-bar flip only applies to static-direction effects. If busy, the flip period is one constant.
- [LLM emits junk directions] → unmapped values no-op.

## Migration Plan

Additive; `direction=""` default everywhere. First change under the PR workflow: branch `change/add-directional-sweeps` → PR → user merges. Rollback = revert the PR.

## Open Questions

- Whether the beat-accent layer should also use chase-type knobs on its `On` pulses (On has no direction) — out of scope; the accents get direction from rotation order only.
