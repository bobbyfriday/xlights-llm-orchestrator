"""Mood phrasing → soft-edge realization, shared by the cell weaver and the beat-accent layer.

`legato` (calm/introspective) softens edges; `staccato` (energetic) keeps them crisp. The Director
directs it per section (`SectionPlan.phrasing`); left blank it resolves from the section's intensity.
Kept in its own module so both `weave` and `beats` can use it without an import cycle.
"""

from __future__ import annotations

from .tuning import LEGATO_FADE_FRACTION, LEGATO_MAX_FADE_S, PHRASING_INTENSITY_THRESHOLD

# Legato realization picks a soft-edge primitive per effect FAMILY: full-canvas fills/washes/
# textures melt better with a Dissolve; everything else (line/chase/point effects) softens with a
# linear opacity fade — the safe default for any effect not listed here.
_DISSOLVE_FAMILY = {"Plasma", "Color Wash", "Fill", "Shimmer", "Fire", "Liquid", "Life", "Galaxy"}


def resolve_phrasing(phrasing: str, intensity: float) -> str:
    """A section's effective phrasing: the Director's value when given, else inferred from energy
    (low intensity → legato/soft, energetic → staccato/crisp). Always returns 'legato'|'staccato'.

    The Director sometimes answers with a descriptive phrase ('legato and sweeping') rather than the
    bare enum, so match the keyword anywhere in the value before falling back to the energy default —
    its explicit intent shouldn't be lost to a stray adjective."""
    p = (phrasing or "").strip().lower()
    if "legato" in p:
        return "legato"
    if "staccato" in p:
        return "staccato"
    i = max(0.0, min(1.0, intensity or 0.0))
    return "legato" if i < PHRASING_INTENSITY_THRESHOLD else "staccato"


def soft_edge_settings(effect_type: str, cell_len_ms: int, phrasing: str) -> dict[str, str]:
    """The legato soft-edge keys for a cell/accent; `{}` for staccato (crisp on/off, as before).

    The primitive is chosen in code from the effect family — a Dissolve melt for full-canvas
    fills/washes, a linear opacity fade (scaled to the gesture's own length, capped) for line/chase/
    point effects. All numbers are owned here, never by the LLM.
    """
    if phrasing != "legato":
        return {}
    if effect_type in _DISSOLVE_FAMILY:
        adj = str(int(round(LEGATO_FADE_FRACTION * 100)))
        return {"T_CHOICE_In_Transition_Type": "Dissolve",
                "T_CHOICE_Out_Transition_Type": "Dissolve",
                "T_SLIDER_In_Transition_Adjust": adj,
                "T_SLIDER_Out_Transition_Adjust": adj}
    fade = round(min(LEGATO_MAX_FADE_S, LEGATO_FADE_FRACTION * max(0, cell_len_ms) / 1000.0), 2)
    s = f"{fade:g}"                            # xLights fade is seconds, e.g. "0.42" | "1.5"
    return {"T_TEXTCTRL_Fadein": s, "T_TEXTCTRL_Fadeout": s}


def tail_fade_settings(effect_type: str, fade_out_s: float) -> dict[str, str]:
    """A fade-OUT scaled to an explicit length, for the song-end envelope fade.

    Same soft-edge primitive as the legato cell path, but the time is given (the trailing region)
    rather than derived from a cell's own length, and only the OUT edge fades (the song is ending —
    nothing fades in). A linear opacity fade dims the effect with the music; full-canvas fills/washes
    additionally melt with a Dissolve-out, matching `soft_edge_settings`.
    """
    s = f"{round(max(0.0, fade_out_s), 2):g}"
    keys = {"T_TEXTCTRL_Fadeout": s}
    if effect_type in _DISSOLVE_FAMILY:
        keys["T_CHOICE_Out_Transition_Type"] = "Dissolve"
        keys["T_SLIDER_Out_Transition_Adjust"] = str(int(round(LEGATO_FADE_FRACTION * 100)))
    return keys
