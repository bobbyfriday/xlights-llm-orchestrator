"""Tests for LED readability (visible sweeps + hue-contrast floor) and settings hygiene."""

from __future__ import annotations

from xlights_core.knowledge.colors import contrast_anchors, ensure_contrast, hue_spread

from xlights_orchestrator.pipeline.beats import effect_speed_setting, place_beat_accents
from xlights_orchestrator.pipeline.weave import expand_weave
from xlights_orchestrator.show_plan import CellRecipe, SectionPlan, SectionWeave

GOLDS = ["#FFF1D0", "#FFBF00", "#FFF7E5", "#FFDB70", "#FFD674"]   # the real carol cell palette
GROUPS = ["SEM_ARCHES", "SEM_CANES", "SEM_MINITREES", "SEM_YARD"]


def _sec(**kw):
    kw.setdefault("start_ms", 0); kw.setdefault("end_ms", 16000)
    kw.setdefault("target_groups", ["SEM_YARD"]); kw.setdefault("effect_family", "On")
    kw.setdefault("intensity", 0.8); kw.setdefault("palette", ["gold", "amber"])
    return SectionPlan(**kw)


def _rhythm(n=32, step=500):
    return {"beats_ms": [i * step for i in range(n)], "prominent_stem": None,
            "onsets_by_stem": {}, "chords_ms": [], "tempo": 120}


# -- contrast machinery --------------------------------------------------------

def test_warm_cluster_gains_a_cool_anchor():
    assert hue_spread(GOLDS) < 10
    floored = ensure_contrast(GOLDS)
    assert len(floored) == len(GOLDS) + 1
    a, b = contrast_anchors(GOLDS)
    assert hue_spread([a, b]) > 120                       # the pair is REALLY different


def test_contrasting_palette_untouched():
    pal = ["deep blue", "gold"]
    assert ensure_contrast(pal) == pal
    a, b = contrast_anchors(pal)
    assert {a, b} == {"#00008B", "#FFD700"}


def test_achromatics_do_not_fake_contrast():
    # gold + white is still ONE hue — must trigger injection
    assert hue_spread(["gold", "white", "warm white"]) < 10
    assert len(ensure_contrast(["gold", "white"])) == 3


# -- sweeps render visibly -----------------------------------------------------

def test_directional_chase_renders_group_canvas_with_dwell():
    w = SectionWeave(cells=[CellRecipe(effect_type="SingleStrand", role="carrier",
                                       direction="bounce", cell_beats=1, groups=["SEM_ARCHES"])])
    out = expand_weave(_sec(), w, _rhythm(), 0.8, GROUPS)
    assert all(c.render_style == "Default" for c in out)          # group canvas: it TRAVELS
    assert all(c.end_ms - c.start_ms >= 1000 for c in out)        # floored to 2 beats


def test_nondirectional_and_explicit_unchanged():
    w = SectionWeave(cells=[
        CellRecipe(effect_type="SingleStrand", role="carrier", cell_beats=1, groups=["SEM_ARCHES"]),
        CellRecipe(effect_type="Spirals", role="texture", direction="ltr",
                   render_style="Per Model Default", groups=["SEM_YARD"]),
    ])
    out = expand_weave(_sec(), w, _rhythm(), 0.8, GROUPS)
    ss = [c for c in out if c.effect_type == "SingleStrand"]
    sp = [c for c in out if c.effect_type == "Spirals"]
    assert all(c.render_style == "Per Model Default" for c in ss)  # no direction → per-model
    assert all(c.render_style == "Per Model Default" for c in sp)  # explicit style wins


# -- anchor alternation --------------------------------------------------------

def test_carrier_cells_alternate_anchors():
    w = SectionWeave(cells=[CellRecipe(effect_type="SingleStrand", role="carrier",
                                       cell_beats=1, groups=["SEM_ARCHES"])])
    out = expand_weave(_sec(palette=["gold", "amber", "warm white"]), w, _rhythm(), 0.8, GROUPS)
    colors = [tuple(c.palette_colors) for c in out[:4]]
    assert colors[0] != colors[1] and colors[0] == colors[2]      # A/B/A/B
    assert all(len(c.palette_colors) == 1 for c in out[:4])
    assert hue_spread([colors[0][0], colors[1][0]]) > 120         # the alternation IS contrast


def test_texture_keeps_the_family():
    w = SectionWeave(cells=[CellRecipe(effect_type="Spirals", role="texture",
                                       cell_beats=1, groups=["SEM_YARD"])])
    out = expand_weave(_sec(), w, _rhythm(8), 0.8, GROUPS)
    assert all(len(c.palette_colors) >= 3 for c in out)           # expanded family, not anchors


def test_beat_accents_use_hue_distant_anchor():
    sec = _sec(palette=["gold", "amber"])
    acc = place_beat_accents(sec, _rhythm(8), GROUPS)
    assert acc
    accent_hex = acc[0].palette_colors[0]
    assert hue_spread([accent_hex, "#FFBF00"]) > 90               # far from the gold wash


# -- settings hygiene ----------------------------------------------------------

def test_speed_uses_real_keys_only():
    assert "E_SLIDER_Meteors_Speed" in effect_speed_setting("Meteors", 0.8)
    assert effect_speed_setting("Color Wash", 1.0) == {"E_TEXTCTRL_ColorWash_Cycles": "6.0"}
    assert effect_speed_setting("Spirals", 0.0) == {"E_TEXTCTRL_Spirals_Movement": "0.5"}
    for speedless in ("SingleStrand", "Twinkle", "On", "Strobe", "Shockwave"):
        assert effect_speed_setting(speedless, 0.8) == {}


def test_stale_keys_stripped_from_assembly():
    from xlights_core.editing import DROP_KEYS
    assert "E_CHECKBOX_Chase_3dFade1" in DROP_KEYS
    settings = "E_CHECKBOX_Chase_3dFade1=1,E_CHOICE_Chase_Type1=Left-Right"
    kept = ",".join(p for p in settings.split(",") if p.split("=", 1)[0] not in DROP_KEYS)
    assert "Chase_3dFade1" not in kept and "Chase_Type1" in kept


def test_sem_gridsize_patch(tmp_path):
    from xlights_core.knowledge.layout_semantics import patch_sem_gridsize
    rgb = tmp_path / "xlights_rgbeffects.xml"
    rgb.write_text('<xrgb><modelGroups>'
                   '<modelGroup name="SEM_ARCHES" GridSize="400" models="a"/>'
                   '<modelGroup name="Matrixes" GridSize="400" models="m"/>'
                   '</modelGroups></xrgb>')
    assert patch_sem_gridsize(rgb) == 1                           # only the SEM_ group
    text = rgb.read_text()
    assert 'name="SEM_ARCHES" GridSize="1200"' in text.replace("' ", '" ') or "1200" in text
    assert text.count('GridSize="400"') == 1                      # user group untouched
    assert patch_sem_gridsize(rgb) == 0                           # idempotent
