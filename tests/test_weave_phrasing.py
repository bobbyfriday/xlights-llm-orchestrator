"""Tests for mood-aware phrasing: legato/staccato resolution, the per-effect soft-edge primitive
(fade vs dissolve), and how the weaver applies them (cell fades, the legato cell-beats floor, the
explicit-recipe-transition precedence, and the bed's gentle entrance)."""

from __future__ import annotations

from xlights_orchestrator.pipeline.tuning import (
    LEGATO_BED_FADE_S,
    LEGATO_CELL_BEATS_FLOOR,
    LEGATO_MAX_FADE_S,
)
from xlights_orchestrator.pipeline.weave import (
    expand_weave,
    resolve_phrasing,
    soft_edge_settings,
)
from xlights_orchestrator.show_plan import CellRecipe, SectionPlan, SectionWeave

GROUPS = ["SEM_ARCHES", "SEM_CANES", "SEM_MINITREES", "SEM_YARD", "SEM_BAND_GROUND", "SEM_FOCAL"]


def _sec(start=0, end=8000, intensity=0.8, **kw):
    kw.setdefault("target_groups", ["SEM_YARD", "SEM_ARCHES"])
    kw.setdefault("effect_family", "On")
    kw.setdefault("palette", ["Gold", "Deep Blue"])
    return SectionPlan(start_ms=start, end_ms=end, intensity=intensity, **kw)


def _rhythm(n_beats=16, step=500):
    return {"beats_ms": [i * step for i in range(n_beats)], "prominent_stem": "drums",
            "onsets_by_stem": {}, "chords_ms": [], "tempo": 120}


def _carrier(**kw):
    kw.setdefault("effect_type", "SingleStrand")
    kw.setdefault("role", "carrier")
    kw.setdefault("groups", ["SEM_ARCHES", "SEM_CANES"])
    kw.setdefault("cell_beats", 1)
    return CellRecipe(**kw)


def _fades(cells):
    return [c for c in cells if "T_TEXTCTRL_Fadein" in c.extra_settings]


# -- model back-compat --------------------------------------------------------

def test_section_plan_phrasing_is_optional_and_round_trips():
    assert _sec().phrasing == ""                              # defaulted (old plans deserialize)
    s = _sec(intensity=0.2, phrasing="legato")
    assert SectionPlan.model_validate(s.model_dump()).phrasing == "legato"   # round-trips


# -- resolve_phrasing ---------------------------------------------------------

def test_resolve_phrasing_directed_wins_over_intensity():
    assert resolve_phrasing("legato", 0.95) == "legato"     # directed beats a loud section
    assert resolve_phrasing("staccato", 0.05) == "staccato"  # directed beats a quiet section
    assert resolve_phrasing("LEGATO", 0.95) == "legato"      # case-insensitive
    assert resolve_phrasing("legato and sweeping", 0.9) == "legato"   # descriptive phrase, keyword wins
    assert resolve_phrasing("staccato, punchy", 0.1) == "staccato"


def test_resolve_phrasing_defaults_from_intensity():
    assert resolve_phrasing("", 0.2) == "legato"             # quiet → soft
    assert resolve_phrasing("", 0.8) == "staccato"           # loud → crisp
    assert resolve_phrasing("", 0.49) == "legato"            # just below threshold
    assert resolve_phrasing("", 0.5) == "staccato"           # AT threshold → staccato (not < )
    assert resolve_phrasing("garbage", 0.2) == "legato"      # unknown value falls back to energy


# -- effect family -> primitive ----------------------------------------------

def test_line_and_chase_effects_get_a_fade():
    for eff in ("SingleStrand", "On", "Twinkle", "Bars", "WeirdUnknownEffect"):
        s = soft_edge_settings(eff, 1200, "legato")
        assert "T_TEXTCTRL_Fadein" in s and "T_CHOICE_In_Transition_Type" not in s


def test_textural_fill_effects_get_a_dissolve():
    for eff in ("Plasma", "Color Wash", "Fill", "Shimmer"):
        s = soft_edge_settings(eff, 4000, "legato")
        assert s["T_CHOICE_In_Transition_Type"] == "Dissolve"
        assert s["T_CHOICE_Out_Transition_Type"] == "Dissolve"
        assert "T_TEXTCTRL_Fadein" not in s


# -- soft_edge_settings numbers ----------------------------------------------

def test_fade_scales_to_cell_length_in_seconds():
    assert soft_edge_settings("SingleStrand", 1200, "legato")["T_TEXTCTRL_Fadein"] == "0.42"
    assert soft_edge_settings("SingleStrand", 2000, "legato")["T_TEXTCTRL_Fadein"] == "0.7"


def test_fade_is_capped_for_long_cells():
    s = soft_edge_settings("SingleStrand", 100_000, "legato")   # 0.35*100s = 35s, must clamp
    assert s["T_TEXTCTRL_Fadein"] == f"{LEGATO_MAX_FADE_S:g}"


def test_staccato_emits_no_soft_edge_keys():
    assert soft_edge_settings("SingleStrand", 1200, "staccato") == {}
    assert soft_edge_settings("Plasma", 4000, "staccato") == {}


# -- expand_weave end-to-end --------------------------------------------------

def test_low_intensity_line_section_cells_fade():
    w = SectionWeave(cells=[_carrier()])
    out = expand_weave(_sec(intensity=0.2), w, _rhythm(16), 0.2, GROUPS)
    assert out and _fades(out) == out                  # every woven cell carries a fade
    assert all("T_TEXTCTRL_Fadeout" in c.extra_settings for c in out)


def test_legato_textural_section_dissolves():
    w = SectionWeave(cells=[CellRecipe(effect_type="Plasma", role="texture",
                                       groups=["SEM_YARD"], alternation="all", cell_beats=2)])
    out = expand_weave(_sec(intensity=0.2), w, _rhythm(16), 0.2, GROUPS)
    assert out and all(c.extra_settings.get("T_CHOICE_In_Transition_Type") == "Dissolve"
                       for c in out)
    assert not _fades(out)                             # dissolve, not linear fade


def test_energetic_section_stays_crisp():
    w = SectionWeave(cells=[_carrier()])
    out = expand_weave(_sec(intensity=0.9), w, _rhythm(16), 0.9, GROUPS)
    assert out and not _fades(out)
    assert all("T_CHOICE_In_Transition_Type" not in c.extra_settings for c in out)


def test_directed_legato_overrides_energetic_intensity():
    w = SectionWeave(cells=[_carrier()])
    out = expand_weave(_sec(intensity=0.9, phrasing="legato"), w, _rhythm(16), 0.9, GROUPS)
    assert out and _fades(out) == out                  # directed legato softens a loud section


def test_explicit_recipe_transition_is_preserved():
    w = SectionWeave(cells=[_carrier(transition="Wipe")])
    out = expand_weave(_sec(intensity=0.2), w, _rhythm(16), 0.2, GROUPS)   # legato section
    assert out and all(c.extra_settings.get("T_CHOICE_In_Transition_Type") == "Wipe" for c in out)
    assert not _fades(out)                             # the recipe's Wipe wins, no fade injected


def test_legato_floors_cell_beats_and_stays_within_budget():
    # same recipe + grid, only intensity differs: legato lengthens 1-beat cells to the floor,
    # so it weaves no MORE cells than staccato (longer cells = fewer placements).
    w_leg = SectionWeave(cells=[_carrier(cell_beats=1)])
    w_sta = SectionWeave(cells=[_carrier(cell_beats=1)])
    leg = expand_weave(_sec(intensity=0.2), w_leg, _rhythm(16), 0.2, GROUPS)
    sta = expand_weave(_sec(intensity=0.2, phrasing="staccato"), w_sta, _rhythm(16), 0.2, GROUPS)
    assert leg[0].end_ms - leg[0].start_ms >= LEGATO_CELL_BEATS_FLOOR * 500  # ≥ floor beats long
    assert len(leg) <= len(sta)


def test_bed_gets_a_gentle_capped_fade_in_legato():
    w = SectionWeave(cells=[CellRecipe(effect_type="Color Wash", role="bed", groups=["SEM_YARD"]),
                            _carrier()])
    out = expand_weave(_sec(intensity=0.2), w, _rhythm(16), 0.2, GROUPS)
    bed = next(c for c in out if c.start_ms == 0 and c.end_ms == 8000)
    assert bed.extra_settings["T_TEXTCTRL_Fadein"] == f"{LEGATO_BED_FADE_S:g}"
    assert bed.extra_settings["T_TEXTCTRL_Fadeout"] == f"{LEGATO_BED_FADE_S:g}"
