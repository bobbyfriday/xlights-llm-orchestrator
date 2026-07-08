"""Per-effect metadata — the single source of truth for what each xLights effect can do.

Four parallel per-effect tables (speed keys, direction knobs, energy bands, duration classes)
plus three private capability sets used to live in `beats.py`, `weave.py`, and `qa/rules.py`,
duplicated and cross-imported. They collapse here into one `EffectMeta` row per effect type; the
old names are rebuilt as DERIVED VIEWS so every existing caller keeps working (each original module
re-exports the view it needs). Provenance for each datum stays in its row comment.

Consolidation: 2026-07-05-add-engineering-hardening (I3). No values change — the derived views are
frozen-literal-checked in tests/test_effect_meta.py so a transcription typo can't silently no-op at
emit time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

DurationClass = Literal["hit", "phrase", "cellable", "free"]


@dataclass(frozen=True)
class EffectMeta:
    """One effect type's placement metadata (all fields optional beyond the type name).

    - `speed`: the effect's REAL speed/cycles/movement key + corpus range `(key, lo, hi, fmt)`
      (`fmt`: "int" slider | "f1" one-decimal textctrl); `None` when the effect has no speed concept.
    - `directions`: `direction -> (key, value)` effect-native settings; `{}` when unmapped.
    - `energy_band`: catalog §2 `(min, max)` energy band; `None` = unconstrained.
    - `duration_class`: "hit" (≤1-bar punctuation) | "phrase" (bounded gesture) | "cellable"
      (1–2 bar motion cells) | "free" (no duration rule / long beds).
    - `bed_capable` / `native_bounce` / `chase_family`: capability flags used by the weaver.
    """

    speed: tuple[str, float, float, str] | None = None
    directions: dict[str, tuple[str, str]] = field(default_factory=dict)
    energy_band: tuple[int, int] | None = None
    duration_class: DurationClass = "free"
    bed_capable: bool = False
    native_bounce: bool = False
    chase_family: bool = False


# One row per effect type. Speed ranges: provenance 2026-06-12-add-settings-hygiene (the old blanket
# `E_SLIDER_<Effect>_Speed` was a real key for only a few effects — the intensity→speed feature
# silently no-op'd elsewhere AND xLights logged ApplySetting errors; effects with no speed concept
# emit nothing). Direction values: provenance 2026-06-12-add-directional-sweeps (strictly
# corpus-observed community .xsq — valid by construction; missing pairs no-op). Energy bands: catalog
# §2 (±1 allowed at enforcement). Duration classes: catalog §2.1 v0.3.
EFFECT_META: dict[str, EffectMeta] = {
    # -- chase family (SingleStrand/Garlands native-bounce; all cell-able) ----------------------
    "SingleStrand": EffectMeta(
        directions={"ltr": ("E_CHOICE_Chase_Type1", "Left-Right"),
                    "rtl": ("E_CHOICE_Chase_Type1", "Right-Left"),
                    "bounce": ("E_CHOICE_Chase_Type1", "Dual Bounce"),
                    "center_out": ("E_CHOICE_Chase_Type1", "From Middle"),
                    "center_in": ("E_CHOICE_Chase_Type1", "To Middle")},
        energy_band=(2, 4), duration_class="cellable", native_bounce=True, chase_family=True),
    "Garlands": EffectMeta(
        speed=("E_TEXTCTRL_Garlands_Cycles", 1, 4, "f1"),
        directions={"ltr": ("E_CHOICE_Garlands_Direction", "Right"),
                    "rtl": ("E_CHOICE_Garlands_Direction", "Left"),
                    "up": ("E_CHOICE_Garlands_Direction", "Up"),
                    "down": ("E_CHOICE_Garlands_Direction", "Down"),
                    "bounce": ("E_CHOICE_Garlands_Direction", "Left then Right")},
        energy_band=(2, 2), duration_class="cellable", native_bounce=True, chase_family=True),
    "Bars": EffectMeta(
        speed=("E_TEXTCTRL_Bars_Cycles", 0.5, 4, "f1"),
        directions={"ltr": ("E_CHOICE_Bars_Direction", "Right"),
                    "rtl": ("E_CHOICE_Bars_Direction", "Left"),
                    "up": ("E_CHOICE_Bars_Direction", "up"),
                    "down": ("E_CHOICE_Bars_Direction", "down"),
                    "center_out": ("E_CHOICE_Bars_Direction", "H-expand"),
                    "center_in": ("E_CHOICE_Bars_Direction", "H-compress")},
        energy_band=(2, 4), duration_class="cellable", chase_family=True),
    "Marquee": EffectMeta(
        speed=("E_SLIDER_Marquee_Speed", 1, 8, "int"),
        directions={"ltr": ("E_CHECKBOX_Marquee_Reverse", "0"),
                    "rtl": ("E_CHECKBOX_Marquee_Reverse", "1")},
        energy_band=(2, 3), chase_family=True),
    "Wave": EffectMeta(
        speed=("E_TEXTCTRL_Wave_Speed", 5, 35, "f1"),
        directions={"ltr": ("E_CHOICE_Wave_Direction", "Left to Right"),
                    "rtl": ("E_CHOICE_Wave_Direction", "Right to Left")},
        energy_band=(2, 3), duration_class="cellable", chase_family=True),
    # -- other cell-able motion effects --------------------------------------------------------
    # E_SLIDER_Spirals_Rotation: 84 corpus looks carry the key (66 positive, 16 negative);
    # ±20 is the corpus mode. Negative = counter-clockwise (signed slider, corpus-observed).
    "Spirals": EffectMeta(
        speed=("E_TEXTCTRL_Spirals_Movement", 0.5, 4, "f1"),
        directions={"ltr": ("E_SLIDER_Spirals_Rotation", "20"),
                    "rtl": ("E_SLIDER_Spirals_Rotation", "-20")},
        energy_band=(2, 5), duration_class="cellable"),
    "Pinwheel": EffectMeta(
        speed=("E_SLIDER_Pinwheel_Speed", 5, 20, "int"),
        directions={"ltr": ("E_CHECKBOX_Pinwheel_Rotation", "1"),
                    "rtl": ("E_CHECKBOX_Pinwheel_Rotation", "0")},
        energy_band=(2, 5), duration_class="cellable"),
    # E_SLIDER_Ripple_Rotation: 22 corpus looks carry the key (13 more via E_VALUECURVE); ±20 matched.
    "Ripple": EffectMeta(
        speed=("E_TEXTCTRL_Ripple_Cycles", 1, 8, "f1"),
        directions={"ltr": ("E_SLIDER_Ripple_Rotation", "20"),
                    "rtl": ("E_SLIDER_Ripple_Rotation", "-20")},
        energy_band=(2, 3), duration_class="cellable"),
    "Butterfly": EffectMeta(
        speed=("E_SLIDER_Butterfly_Speed", 8, 40, "int"),
        directions={"ltr": ("E_CHOICE_Butterfly_Direction", "Normal"),
                    "rtl": ("E_CHOICE_Butterfly_Direction", "Reverse")},
        energy_band=(2, 3), duration_class="cellable"),
    "Meteors": EffectMeta(
        speed=("E_SLIDER_Meteors_Speed", 10, 45, "int"),
        directions={"ltr": ("E_CHOICE_Meteors_Effect", "Right"),
                    "up": ("E_CHOICE_Meteors_Effect", "Up"),
                    "down": ("E_CHOICE_Meteors_Effect", "Down"),
                    "center_out": ("E_CHOICE_Meteors_Effect", "Explode"),
                    "center_in": ("E_CHOICE_Meteors_Effect", "Implode")},
        energy_band=(2, 4), duration_class="cellable"),
    # -- bed-capable / wash effects ------------------------------------------------------------
    "On": EffectMeta(
        # "On" deliberately has NO speed row: On_Cycles would make steady beds PULSE — pulses are
        # the beat layer's job; beds stay flat.
        energy_band=(1, 5), bed_capable=True),
    "Color Wash": EffectMeta(
        speed=("E_TEXTCTRL_ColorWash_Cycles", 1, 6, "f1"), bed_capable=True),
    "Plasma": EffectMeta(
        speed=("E_SLIDER_Plasma_Speed", 70, 90, "int"),
        energy_band=(1, 3), bed_capable=True),
    # -- phrase-class effects ------------------------------------------------------------------
    "Curtain": EffectMeta(
        speed=("E_TEXTCTRL_Curtain_Speed", 0.5, 4, "f1"),
        energy_band=(2, 3), duration_class="phrase"),
    "Fill": EffectMeta(
        directions={"ltr": ("E_CHOICE_Fill_Direction", "Right"),
                    "rtl": ("E_CHOICE_Fill_Direction", "Left"),
                    "up": ("E_CHOICE_Fill_Direction", "Up"),
                    "down": ("E_CHOICE_Fill_Direction", "Down")},
        energy_band=(2, 3), duration_class="phrase"),
    "Morph": EffectMeta(energy_band=(2, 4), duration_class="phrase"),
    "Fan": EffectMeta(
        directions={"center_out": ("E_CHECKBOX_Fan_Reverse", "0"),
                    "center_in": ("E_CHECKBOX_Fan_Reverse", "1")},
        energy_band=(2, 4), duration_class="phrase"),
    "Fireworks": EffectMeta(energy_band=(3, 5), duration_class="phrase"),
    "Shimmer": EffectMeta(
        speed=("E_TEXTCTRL_Shimmer_Cycles", 4, 12, "f1"),
        energy_band=(2, 4), duration_class="phrase"),
    # -- hit-class effects ---------------------------------------------------------------------
    "Shockwave": EffectMeta(energy_band=(3, 5), duration_class="hit"),
    "Strobe": EffectMeta(energy_band=(4, 5), duration_class="hit"),
    "Lightning": EffectMeta(energy_band=(3, 5), duration_class="hit"),
    # -- motion-share extras (energy-banded, motion fabric; not cell-able themselves) ----------
    "Galaxy": EffectMeta(
        directions={"center_out": ("E_CHECKBOX_Galaxy_Reverse", "0"),
                    "center_in": ("E_CHECKBOX_Galaxy_Reverse", "1")},
        energy_band=(2, 4)),
    "Fire": EffectMeta(energy_band=(2, 4)),
    # -- remaining energy-banded / speed-only effects (no direction/duration/flags) ------------
    "Circles": EffectMeta(
        speed=("E_SLIDER_Circles_Speed", 5, 25, "int"), energy_band=(2, 3)),
    "Tree": EffectMeta(
        speed=("E_SLIDER_Tree_Speed", 5, 20, "int"), energy_band=(2, 2)),
    "Warp": EffectMeta(speed=("E_SLIDER_Warp_Speed", 5, 30, "int")),
    "Snowflakes": EffectMeta(
        speed=("E_SLIDER_Snowflakes_Speed", 10, 25, "int"), energy_band=(1, 2)),
    "Snowstorm": EffectMeta(
        speed=("E_SLIDER_Snowstorm_Speed", 10, 30, "int"), energy_band=(2, 3)),
    "Kaleidoscope": EffectMeta(energy_band=(3, 4)),
    "Liquid": EffectMeta(energy_band=(2, 3)),
    "Twinkle": EffectMeta(energy_band=(1, 3)),
    "Shape": EffectMeta(energy_band=(1, 4)),
    "Tendril": EffectMeta(energy_band=(2, 3)),
    "VU Meter": EffectMeta(energy_band=(2, 5)),
}


# -- derived views: the historical names, rebuilt from EFFECT_META --------------------------------
# Each original module re-exports the subset it needs (`from .effect_meta import SPEED_KEYS`), so no
# caller — tests or external scripts — breaks. Ordering within these dicts follows EFFECT_META, which
# doesn't match the old literal order; dict/set equality is by content, so the table-integrity test
# still passes (values, not insertion order, are the contract).

SPEED_KEYS: dict[str, tuple[str, float, float, str]] = {
    et: m.speed for et, m in EFFECT_META.items() if m.speed is not None
}
DIRECTION_KNOBS: dict[str, dict[str, tuple[str, str]]] = {
    et: dict(m.directions) for et, m in EFFECT_META.items() if m.directions
}
ENERGY_BAND: dict[str, tuple[int, int]] = {
    et: m.energy_band for et, m in EFFECT_META.items() if m.energy_band is not None
}
DURATION_HIT: set[str] = {et for et, m in EFFECT_META.items() if m.duration_class == "hit"}
DURATION_PHRASE: set[str] = {et for et, m in EFFECT_META.items() if m.duration_class == "phrase"}
DURATION_CELLABLE: set[str] = {et for et, m in EFFECT_META.items() if m.duration_class == "cellable"}
# The community fabric is woven from continuous-motion effects — cell-able types plus Fire/Galaxy
# (banded motion textures the rest are already cellable).
MOTION_EFFECTS: set[str] = DURATION_CELLABLE | {"Fire", "Galaxy"}

# capability flags (private-today sets in weave.py; no import-compat needed but consolidated here)
BED_EFFECTS: set[str] = {et for et, m in EFFECT_META.items() if m.bed_capable}
NATIVE_BOUNCE: set[str] = {et for et, m in EFFECT_META.items() if m.native_bounce}
CHASE_FAMILY: set[str] = {et for et, m in EFFECT_META.items() if m.chase_family}


def duration_class(effect_type: str) -> DurationClass:
    """The effect's catalog §2.1 duration class ('free' for unlisted effects)."""
    m = EFFECT_META.get(effect_type)
    return m.duration_class if m else "free"


# -- Shockwave accent settings (shared across beats.py + triggers.py) -------------------------
# A radiating Shockwave that reads on an accent prop — hand-authored settings (snowflakes/spinners,
# 0:30–0:44): a modest ring expanding from center. Overrides the frozen look base via extra_settings.
# Moved here (from triggers.py) so beats.py can import it without creating an import cycle.
SHOCKWAVE_SETTINGS: dict[str, str] = {
    "E_NOTEBOOK_Shockwave": "Position", "E_CHECKBOX_Shockwave_Blend_Edges": "1",
    "E_CHECKBOX_Shockwave_Scale": "1", "E_SLIDER_Shockwave_Accel": "0",
    "E_SLIDER_Shockwave_CenterX": "50", "E_SLIDER_Shockwave_CenterY": "50",
    "E_SLIDER_Shockwave_Cycles": "1", "E_SLIDER_Shockwave_Start_Radius": "1",
    "E_SLIDER_Shockwave_End_Radius": "76", "E_SLIDER_Shockwave_Start_Width": "5",
    "E_SLIDER_Shockwave_End_Width": "43",
}
