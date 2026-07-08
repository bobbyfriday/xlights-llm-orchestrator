"""Synthesize xLights value-curve settings (the parametric Ramp the corpus uses) so effects can
ramp/swell/spin over their duration. We already PARSE these (`settings.py`); this is the write
side. Returned as `{key: value}` ready to drop into `EffectInstruction.extra_settings`.

CANONICAL FORMAT (live-verified by round-trip + matches the mined corpus): `Min`/`Max` are the
PARAMETER'S full range, `P1`/`P2` are the ramp's start/end as REAL values, `RV=TRUE`. Sending
the ramp endpoints in Min/Max instead makes xLights rescale them into the real range — our old
84→120 brightness ramp round-tripped as 1027→-84 (a flash-to-black crash, not a build).
"""

from __future__ import annotations

# Brightness is on a 0–400 scale where 100 == normal; other params use their own scales.
BRIGHTNESS_RANGE = (0.0, 400.0)


def _ramp_value(param: str, lo: float, hi: float, start: float, end: float) -> str:
    """A parametric Ramp from `start`→`end` over the param's real range [lo, hi]."""
    clamp = lambda v: min(hi, max(lo, v))
    return (f"Active=TRUE|Id=ID_VALUECURVE_{param}|Type=Ramp|"
            f"Min={lo:.2f}|Max={hi:.2f}|P1={clamp(start):.2f}|P2={clamp(end):.2f}|RV=TRUE|")


def value_curve_setting(param: str, start: float, end: float,
                        rng: tuple[float, float] = BRIGHTNESS_RANGE) -> dict[str, str]:
    """`{C_VALUECURVE_<param>: <ramp>}` — ready for `EffectInstruction.extra_settings`."""
    return {f"C_VALUECURVE_{param}": _ramp_value(param, *rng, start, end)}


def brightness_ramp(start_pct: float, end_pct: float) -> dict[str, str]:
    """A brightness ramp (0–400 scale, 100=normal) as an `extra_settings` entry."""
    return value_curve_setting("Brightness", start_pct, end_pct)


def brightness_setting(level: float) -> dict[str, str]:
    """A CONSTANT brightness as a static `C_SLIDER_Brightness` (0–400 scale, 100=normal).

    Use this for a flat level — value curves are for VARYING a param over the effect (a constant
    Min==Max Ramp is degenerate and xLights mangles it to inf/nan).
    """
    return {"C_SLIDER_Brightness": str(int(round(level)))}


# -- motion curves (the community's value-curve use: shape MOVEMENT, not loudness) --
# (effect_type, curve) -> (param key suffix, range_lo, range_hi, kind)
#   kind "spin":  accelerate from rest → an intensity-scaled rate (rotation-like params)
#   kind "sweep": travel low→high across an intensity-scaled span (radius/position-like)
# Keys + ranges verified against the mined corpus looks (E_VALUECURVE_* frozen values).
MOTION_CURVES: dict[tuple[str, str], tuple[str, float, float, str]] = {
    ("Spirals", "rotation"):  ("Spirals_Rotation", -300.0, 300.0, "spin"),
    ("Spirals", "movement"):  ("Spirals_Movement", -200.0, 200.0, "spin"),
    ("Pinwheel", "twist"):    ("Pinwheel_Twist", -360.0, 360.0, "spin"),
    ("Pinwheel", "thickness"): ("Pinwheel_Thickness", 0.0, 100.0, "sweep"),
    ("Ripple", "rotation"):   ("Ripple_Rotation", -360.0, 360.0, "spin"),
    ("Ripple", "twist"):      ("Ripple_Twist", 0.0, 20.0, "sweep"),
    ("Shockwave", "radius"):  ("Shockwave_End_Radius", 0.0, 750.0, "sweep"),
    ("Shockwave", "width"):   ("Shockwave_End_Width", 0.0, 255.0, "sweep"),
    ("Fill", "position"):     ("Fill_Position", 0.0, 100.0, "sweep"),
    ("Bars", "cycles"):       ("Bars_Cycles", 0.0, 300.0, "sweep"),
    ("Wave", "height"):       ("Wave_Height", 0.0, 100.0, "sweep"),
}


def motion_curve_setting(effect_type: str, curve: str, intensity: float = 0.5,
                         *, sign: int = 1) -> dict[str, str]:
    """`{E_VALUECURVE_<param>: <ramp>}` shaping the effect's MOTION over its duration.

    Unknown (effect, curve) pairs return `{}` — a recipe asking for a curve the effect doesn't
    have degrades to no curve, never a placement failure.

    `sign` (-1 or 1) flips the ramp direction for spin-kind curves (negative = counter-clockwise).
    Sweep-kind curves ignore `sign` (their range is inherently unsigned).
    """
    spec = MOTION_CURVES.get((effect_type, (curve or "").lower()))
    if spec is None:
        return {}
    param, lo, hi, kind = spec
    level = max(0.0, min(1.0, intensity))
    if kind == "spin":                       # accelerate from rest to an intensity-scaled rate
        start, end = 0.0, (hi if sign >= 0 else lo) * (0.3 + 0.7 * level)
    else:                                    # sweep across an intensity-scaled span (sign ignored)
        start, end = lo + 0.1 * (hi - lo), lo + (0.3 + 0.6 * level) * (hi - lo)
    return {f"E_VALUECURVE_{param}": _ramp_value(param, lo, hi, start, end)}
