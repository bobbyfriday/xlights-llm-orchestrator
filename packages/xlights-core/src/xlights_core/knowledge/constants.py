"""Constants and classifiers for the effect-preset library."""

from __future__ import annotations

import re

# Effect types whose settings reference external resources not guaranteed to exist
# in a target sequence. Excluded from mining.
ASSET_BOUND_TYPES = frozenset({"Faces", "Pictures", "Video", "Shader", "DMX"})

# Map an xLights setting key to a control "kind" via its self-describing prefix,
# e.g. E_SLIDER_Foo -> "slider", B_CHOICE_Bar -> "choice".
_KIND_BY_TOKEN = {
    "SLIDER": "slider",
    "CHOICE": "choice",
    "CHECKBOX": "checkbox",
    "VALUECURVE": "valuecurve",
    "TEXTCTRL": "text",
    "NOTEBOOK": "notebook",
    "BUTTON": "button",
}

_KEY_RE = re.compile(r"^[EBTC]_([A-Z0-9]+)_")


def classify_kind(key: str) -> str:
    """Return the control kind for a setting key; unknown prefixes -> 'other'."""
    m = _KEY_RE.match(key)
    if m:
        return _KIND_BY_TOKEN.get(m.group(1), "other")
    return "other"


# Value-curve Type values that depend on a named timing track (asset-bound inside a VC).
def is_timing_track_curve_type(curve_type: str) -> bool:
    return curve_type.strip().lower().startswith("timing track")
