## Why

The user's xLights logs surfaced three issue families. (1) `ApplySetting: Unable to find: ID_SLIDER_SingleStrand_Speed` (also Twinkle, Color Wash): our `effect_speed_setting` blanket-writes `E_SLIDER_<Effect>_Speed`, but that's a real key for only a handful of effects — the intensity→speed feature silently never worked for most (SingleStrand has no Speed slider; Color Wash speed is `E_TEXTCTRL_ColorWash_Cycles`; Spirals is `_Movement`; On/Bars are Cycles), and every UI selection logs an error. (2) `Unable to find: ID_CHECKBOX_Chase_3dFade1`: 125 mined SingleStrand looks carry a key removed from current xLights. (3) `Actual Grid Size of 819 exceeded the Max Grid Size of 400`: SEM_ groups get xLights' default GridSize=400, so larger groups' canvas buffers are downscaled and warn on every render — a direct quality ceiling for the upcoming group-canvas sweeps.

## What Changes

- **Corpus-verified `SPEED_KEYS` map** replaces the blanket speed key: each effect's REAL speed/cycles/movement parameter with its observed value range (sliders int-scaled, Cycles/Movement textctrls float-scaled); effects with no speed parameter emit nothing.
- **`DROP_KEYS` strip at look assembly**: settings keys absent from current xLights (starting with `E_CHECKBOX_Chase_3dFade1`) are removed from mined looks before placement.
- **SEM_ group `GridSize`**: `layout_semantics.patch_rgbeffects` sets GridSize on SEM_ groups from member extent (capped 1200), idempotently; user-authored groups untouched.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `show-orchestration`: effect speed SHALL be set via each effect's real speed parameter (corpus-verified per effect; none emitted when the effect has no speed parameter); placements SHALL NOT carry settings keys absent from the current xLights version; semantic groups SHALL carry a grid size covering their actual extent so group-canvas buffers render at full resolution.

## Impact

- `xlights-orchestrator/pipeline/beats.py` (`effect_speed_setting` → SPEED_KEYS), all call sites unchanged in shape.
- `xlights-core`: `editing.py`/`preset_library.py` (DROP_KEYS strip), `knowledge/layout_semantics.py` (GridSize).
- Behavior: effects that previously got a meaningless key now get real speed control — Carol/candy regenerations may render slightly differently (intended: speed finally works).
- Stacks on `change/add-directional-sweeps` (PR workflow; user merges).
