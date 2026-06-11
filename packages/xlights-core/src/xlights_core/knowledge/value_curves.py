"""Synthesize xLights value-curve settings (the parametric Ramp the corpus uses) so effects can
ramp/fade/swell over their duration. We already PARSE these (`settings.py`); this is the write
side. Returned as `{key: value}` ready to drop into `EffectInstruction.extra_settings` (appended
to the assembled settings as `key=value`)."""

from __future__ import annotations

# Brightness is on a 0–400 scale where 100 == normal; other params use their own scales.


def _curve_value(param: str, start: float, end: float) -> str:
    """The VALUE side of a parametric Ramp from `start`→`end` (Min/Max sorted; RV marks descending)."""
    lo, hi = (start, end) if start <= end else (end, start)
    rv = "TRUE" if start > end else "FALSE"
    return (f"Active=TRUE|Id=ID_VALUECURVE_{param}|Type=Ramp|"
            f"Min={lo:.2f}|Max={hi:.2f}|P1=100.00|RV={rv}|")


def value_curve_setting(param: str, start: float, end: float) -> dict[str, str]:
    """`{C_VALUECURVE_<param>: <value>}` — ready for `EffectInstruction.extra_settings`."""
    return {f"C_VALUECURVE_{param}": _curve_value(param, start, end)}


def brightness_ramp(start_pct: float, end_pct: float) -> dict[str, str]:
    """A brightness ramp (0–400 scale, 100=normal) as an `extra_settings` entry."""
    return value_curve_setting("Brightness", start_pct, end_pct)


def brightness_setting(level: float) -> dict[str, str]:
    """A CONSTANT brightness as a static `C_SLIDER_Brightness` (0–400 scale, 100=normal).

    Use this for a flat level — value curves are for VARYING a param over the effect (a constant
    Min==Max Ramp is degenerate and xLights mangles it to inf/nan).
    """
    return {"C_SLIDER_Brightness": str(int(round(level)))}
