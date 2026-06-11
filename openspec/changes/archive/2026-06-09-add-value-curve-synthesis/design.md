## Context
We parse value curves (`settings.py parse_value_curve`) but never synthesize them. `assemble()` only emits a look's `key_order` keys and KeyErrors on unknown `knob_values`, so an *added* curve must be APPENDED to the assembled settings. Value-curve values contain `|` but never `,`, so `settings + ",KEY=VALUE"` is safe. Corpus Ramp format: `Type=Ramp|Min|Max|P1|P2|RV=TRUE` (Brightness Min/Max in a 0–400 scale where 100=normal).

## Goals / Non-Goals
**Goals:** synthesize valid parametric Ramp curves; attach via appended `extra_settings`; round-trip-validate. **Non-Goals:** energy→brightness logic (#2); custom/timing-track curves; build orchestration.

## Decisions
### `value_curve(param, lo, hi, shape="ramp_up") -> str` (`knowledge/value_curves.py`)
Emit `C_VALUECURVE_{param}=Active=TRUE|Id=ID_VALUECURVE_{param}|Type=Ramp|Min={lo:.2f}|Max={hi:.2f}|P1=100.00|RV={RV}|`. Shapes map to (Min,Max,RV): `ramp_up`→(lo,hi,FALSE), `ramp_down`→(lo,hi,TRUE) [RV reverses], `swell`→use Min=lo,Max=hi with a sine/parabolic Type later; for v1 ramp_up/ramp_down cover build/fade. Convenience: `brightness_ramp(lo_pct, hi_pct)` (0–400 scale). Output must satisfy `value_curve_is_active` + `classify_value_curve=="parametric"`.

### Attach via `extra_settings`
`EffectInstruction.extra_settings: dict[str,str] = {}`. `place_preset(..., extra_settings=None)`: after `settings = lib.assemble(...)`, if `extra_settings`: `settings = settings + "," + ",".join(f"{k}={v}" for k,v in extra_settings.items())`. Emitter passes `ins.extra_settings or None`. The probe/other callers default None (unchanged).

## Risks / Trade-offs
- **Ramp direction is empirical** — whether `Min<Max,RV=FALSE` ramps brightness UP must be confirmed live; hermetic tests cover format/round-trip, the live check confirms direction (flip RV if needed).
- **Append correctness** — duplicate keys if a look already has the param; we only attach curves for params the look lacks (caller's responsibility) or accept xLights using the last occurrence. Keep extra_settings for *added* keys only.
- **Brightness scale (0–400)** — 100=normal; document so callers pass sane ranges.

## Open Questions
- Exact P1/P2 semantics for Ramp vs Sine — match corpus Ramp; add Sine/swell once direction is confirmed live.
