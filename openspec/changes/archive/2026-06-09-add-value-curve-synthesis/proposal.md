## Why

The guide leans on value curves constantly — *"value curves are your friend,"* *"Spirals with a value-curve on speed is the workhorse build,"* ramped brightness, swells, fades, attack/release. We already **parse** value curves (`settings.py`) and **apply** knob overrides (`place_preset(knob_values=…)`), but we never **synthesize** them, so the pipeline can't make anything ramp, swell, or fade. This is the foundation the dynamics work (#2 brightness, build/escalation, the drop) stands on.

## What Changes

- A **`value_curve(param, lo, hi, shape)`** synthesizer producing the corpus `C_VALUECURVE_<param>=Active=TRUE|Id=…|Type=Ramp|Min|Max|P1|P2|RV=TRUE` string (round-trips through the existing `parse_value_curve`).
- An **`EffectInstruction.extra_settings`** field + `place_preset(extra_settings=…)` that **appends** synthesized settings to the assembled string (value-curve values contain `|` but never `,`, so appending is safe). This is needed because `assemble()` only overrides a look's existing knobs — a value curve is an *added* key.
- Shapes for the common cases: ramp-up (build/fade-in), ramp-down (fade-out), swell (up-then-down).

**Non-goals:** the energy→brightness decision logic (that's #2); custom/timing-track curves (parametric Ramp only for now); per-bar build orchestration (#9-class, later).

## Capabilities

### Modified Capabilities
- `show-orchestration`: effects can carry synthesized value curves (e.g. a brightness ramp) so they fade/build/swell over their duration, attached as appended settings.

## Impact

- **`xlights-core`**: a `knowledge/value_curves.py` synthesizer; `place_preset` appends `extra_settings`.
- **`xlights-orchestrator`**: `EffectInstruction.extra_settings` (additive); the emitter passes it.
- **Builds on** the existing value-curve parser and the `knob_values`/`assemble` seam. Foundation for #2 and the build/drop work.
