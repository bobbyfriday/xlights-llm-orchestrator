## Why

Watching Carol of the Bells (user feedback): every-beat effects always fire the same way — no left→right, right→left, bounce, center-out/in, or up/down alternation. The direction belongs to the effects' own settings (user decision — no grouping changes): the mined community looks carry a complete direction vocabulary per effect — SingleStrand `Chase_Type1` (Left-Right, Right-Left, Bounce from Left/Right/Middle, Dual Bounce, From/To Middle), Bars (up/down/expand/compress/H-expand/H-compress), Garlands (directional + built-in bounces), Meteors (Up/Down/Explode/Implode), Fill/Wave/Curtain/Butterfly/Marquee/Fan/Galaxy/Pinwheel direction or reverse knobs — all values corpus-observed, valid by construction.

## What Changes

- **`CellRecipe.direction`** (additive, default `""`): `ltr | rtl | bounce | center_out | center_in | up | down`, realized purely via a per-effect DIRECTION_KNOBS settings map (e.g. SingleStrand center_out → `From Middle`; Bars center_in → `H-compress`; Meteors center_out → `Explode`). Effects with native bounce types bounce inside the effect; static-direction effects (Fill/Wave/Meteors) alternate their direction value at bar boundaries under `bounce`. Unknown (effect, direction) pairs emit nothing.
- **Beat-accent directionality**: the deterministic every-beat chase alternates its rotation order per bar (forward through the spatial group order on even bars, backward on odd) — pure function of bar index, no new LLM surface.
- **Fallback weave** carrier defaults to `bounce` — every show gets directional variety even when the LLM omits direction.
- **Generator prompt** documents the direction vocabulary (builds → up, releases → down, call-and-response → bounce/ltr+rtl pairs).
- NO grouping/target changes: cells keep their groups and render styles exactly as today.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `show-orchestration`: beat-synchronized cells SHALL support directional realization (left/right sweeps across spatially-ordered ensembles, vertical band runs, center-out/in), LLM-directable per recipe and alternating deterministically per bar by default, degrading gracefully (no direction → current behavior) when ordered ensembles or direction knobs are unavailable.

## Impact

- `xlights-orchestrator`: `show_plan.py` (direction field), `pipeline/weave.py` (DIRECTION_KNOBS map + bar-flip), `pipeline/beats.py` (bar-alternating accent order), `agents/generator.py` (prompt vocabulary).
- No core/xlights-core changes (knobs ride `extra_settings`; the emitter's override machinery already handles key precedence). No layout/grouping changes.
- Back-compat: `direction=""` expands byte-identically to today.
- Process: first change under the PR workflow — branch `change/add-directional-sweeps`, PR for user merge.
