"""Tests for canonical render order (view + xsq reorder)."""
import xml.etree.ElementTree as ET

from xlights_core.knowledge.layout_semantics import canonical_order, patch_view, patch_xsq_render_order


def test_canonical_precedence():
    out = canonical_order(["Gingerbread Man-1", "SEM_SNOWFLAKES", "SEM_FOCAL", "SEM_ALL",
                           "SEM_ARCHES", "SEM_OUTLINE", "Null 7", "SEM_BAND_GROUND"])
    assert out[0] == "SEM_ALL" and out[1] == "SEM_BAND_GROUND"      # beds first (painted over)
    assert out[-1] == "SEM_SNOWFLAKES"                              # accents last (win)
    assert out.index("SEM_FOCAL") > out.index("Gingerbread Man-1")  # focal over plain props
    assert "Null 7" not in out
    # the whole-display base bed ranks ABOVE the zone beds even when the layout lists them first
    base_first = canonical_order(["SEM_BAND_ROOF", "SEM_SIDE_LEFT", "SEM_BAND_GROUND", "SEM_ALL"])
    assert base_first[0] == "SEM_ALL"


_XSQ = ('<?xml version="1.0" encoding="UTF-8"?><xsequence><head/>'
        '<DisplayElements>'
        '<Element type="timing" name="Beats"/>'
        '<Element type="model" name="SEM_SNOWFLAKES"/>'
        '<Element type="model" name="SEM_ALL"/>'
        '<Element type="model" name="SEM_FOCAL"/>'
        '</DisplayElements>'
        '<ElementEffects>'
        '<Element type="model" name="SEM_SNOWFLAKES"/>'
        '<Element type="model" name="SEM_ALL"/>'
        '<Element type="model" name="SEM_FOCAL"/>'
        '</ElementEffects></xsequence>')


def test_xsq_reorder(tmp_path):
    f = tmp_path / "s.xsq"; f.write_text(_XSQ)
    assert patch_xsq_render_order(f) is True
    r = ET.parse(f).getroot()
    de = [e.get("name") for e in r.find("DisplayElements")]
    assert de == ["Beats", "SEM_ALL", "SEM_FOCAL", "SEM_SNOWFLAKES"]   # timing kept, beds→focal→accents
    ee = [e.get("name") for e in r.find("ElementEffects")]
    assert ee == ["SEM_ALL", "SEM_FOCAL", "SEM_SNOWFLAKES"]


def test_view_authored_idempotently(tmp_path):
    f = tmp_path / "rgb.xml"
    f.write_text('<xrgb><models><model name="Tree" DisplayAs="Tree 360"/></models>'
                 '<modelGroups><modelGroup name="SEM_ALL" models="Tree"/>'
                 '<modelGroup name="SEM_FOCAL" models="Tree"/></modelGroups></xrgb>')
    assert patch_view(f) and patch_view(f)                          # twice → still one view
    r = ET.parse(f).getroot()
    views = r.find("views").findall("view")
    assert len(views) == 1
    assert views[0].get("models").startswith("SEM_ALL")             # beds first
