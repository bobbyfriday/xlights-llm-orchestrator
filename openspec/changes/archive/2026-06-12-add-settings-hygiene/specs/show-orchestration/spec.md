## ADDED Requirements

### Requirement: Effect speed uses each effect's real speed parameter
The intensity-to-speed realization SHALL set each effect's actual speed/cycles/movement parameter (corpus-verified key and value range per effect type) and SHALL emit nothing for effects that have no speed parameter, so no placement carries a speed key the effect does not define.

#### Scenario: Cycles-class effect gets real speed control
- **WHEN** a Color Wash placement is realized at high section intensity
- **THEN** its settings carry `E_TEXTCTRL_ColorWash_Cycles` with a value in the corpus-observed range, and no `E_SLIDER_Color Wash_Speed` key

#### Scenario: Speedless effects emit nothing
- **WHEN** a Twinkle or SingleStrand placement is realized
- **THEN** no speed key is added to its settings

### Requirement: Placements carry no stale settings keys
Settings keys known to be absent from the current xLights version SHALL be stripped from mined looks at placement, so the editor logs no ApplySetting errors for our effects.

#### Scenario: Stale chase key stripped
- **WHEN** a mined SingleStrand look whose frozen settings include `E_CHECKBOX_Chase_3dFade1` is placed
- **THEN** the assembled settings string does not contain that key

### Requirement: Semantic groups render at native buffer resolution
The layout patcher SHALL set a grid size on the SEM_ groups that covers their actual extent, so group-canvas effects render at full resolution without max-grid warnings; user-authored groups SHALL NOT be modified.

#### Scenario: Large semantic group renders without downscaling
- **WHEN** the layout is patched and xLights reloads it
- **THEN** SEM_ groups whose extent exceeds 400 carry a larger GridSize and rendering logs no max-grid-size warnings for them
