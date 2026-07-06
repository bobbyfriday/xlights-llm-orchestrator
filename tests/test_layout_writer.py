"""F-E slice 3 — the SEM_ group writer (spec §5/§5.6/§5.7)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from xlights_core.knowledge.layout_semantics import (
    LAYOUT_MODE_ENSEMBLE,
    LAYOUT_MODE_ORDERED,
    layout_modes,
    write_sem_groups,
)

FIX = Path(__file__).parent / "fixtures"


def _base_layout(tmp_path, extra_groups=""):
    rgb = tmp_path / "xlights_rgbeffects.xml"
    rgb.write_text(
        '<xrgb><models>'
        '<model name="A" DisplayAs="Arches" parm1="1" parm2="25" LayoutGroup="Default"/>'
        '<model name="B" DisplayAs="Arches" parm1="1" parm2="25" LayoutGroup="Default"/>'
        '</models><modelGroups>'
        '<modelGroup name="My User Group" models="A" GridSize="400" layout="grid"/>'
        f'{extra_groups}'
        '</modelGroups></xrgb>')
    return rgb


def _read_groups(rgb):
    root = ET.parse(rgb).getroot()
    return {g.get("name"): g for g in root.find("modelGroups").findall("modelGroup")}


def test_write_creates_groups_and_reparses():
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    rgb = _base_layout(tmp)
    plan = {"SEM_ARCHES": ["A", "B"], "SEM_ARCHES_LTR": ["A", "B"], "SEM_ALL": ["A", "B"]}
    report = write_sem_groups(rgb, plan, modes=layout_modes(plan))
    assert report.changed and set(report.created) == set(plan)
    groups = _read_groups(rgb)
    assert groups["SEM_ARCHES"].get("models") == "A,B"
    assert groups["SEM_ARCHES"].get("GridSize") == "1200"
    # §5.7: the _LTR group gets the ordered mode; ensembles get the ensemble mode
    assert groups["SEM_ARCHES_LTR"].get("layout") == LAYOUT_MODE_ORDERED
    assert groups["SEM_ALL"].get("layout") == LAYOUT_MODE_ENSEMBLE


def test_user_groups_untouched():
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    rgb = _base_layout(tmp)
    plan = {"SEM_ARCHES": ["A", "B"]}
    report = write_sem_groups(rgb, plan)
    groups = _read_groups(rgb)
    assert "My User Group" in groups                      # user group preserved
    assert groups["My User Group"].get("models") == "A"   # exactly as it was
    assert groups["My User Group"].get("layout") == "grid"
    assert report.kept_user_groups == ["My User Group"]


def test_stale_sem_group_disappears():
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    rgb = _base_layout(tmp, extra_groups='<modelGroup name="SEM_OLD" models="A" GridSize="1200"/>')
    write_sem_groups(rgb, {"SEM_ARCHES": ["A", "B"]})
    groups = _read_groups(rgb)
    assert "SEM_OLD" not in groups                        # fully replaced (spec §6)
    assert "SEM_ARCHES" in groups


def test_no_op_on_second_run():
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    rgb = _base_layout(tmp)
    plan = {"SEM_ARCHES": ["A", "B"], "SEM_ALL": ["A", "B"]}
    r1 = write_sem_groups(rgb, plan)
    assert r1.changed and r1.backup is not None
    before = rgb.read_bytes()
    r2 = write_sem_groups(rgb, plan)                      # identical plan → no-op
    assert not r2.changed and r2.backup is None
    assert rgb.read_bytes() == before                    # byte-identical, not rewritten


def test_backup_created_once_per_real_write():
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    rgb = _base_layout(tmp)
    plan = {"SEM_ARCHES": ["A", "B"]}
    r = write_sem_groups(rgb, plan)
    assert r.backup and Path(r.backup).exists()
    # the no-op re-run creates no new backup
    baks_before = list(tmp.glob("*.bak"))
    write_sem_groups(rgb, plan)
    assert list(tmp.glob("*.bak")) == baks_before


def test_output_reparses_under_parse_models():
    """The written file must still parse under the preview layout parser."""
    import tempfile

    from xlights_core.preview.layout import parse_models
    tmp = Path(tempfile.mkdtemp())
    (tmp / "xlights_networks.xml").write_text(
        '<Networks><Controller Id="1" Name="C1" Protocol="E131">'
        '<network MaxChannels="600"/></Controller></Networks>')
    rgb = tmp / "xlights_rgbeffects.xml"
    rgb.write_text(
        '<xrgb><models>'
        '<model name="A" DisplayAs="Arches" StartChannel="!C1:1" parm1="1" parm2="25" '
        'ScaleX="1" ScaleY="1" WorldPosX="0" WorldPosY="0" LayoutGroup="Default"/>'
        '</models><modelGroups/></xrgb>')
    write_sem_groups(rgb, {"SEM_ARCHES": ["A"]})
    from xlights_core.preview.layout import parse_controllers
    ctl = parse_controllers(tmp / "xlights_networks.xml")
    models = parse_models(rgb, ctl)
    assert [m.name for m in models] == ["A"]


def test_roundtrip_fixture_attribute_shape():
    """The writer emits the same `layout` attribute NAME xLights serializes (round-trip fixture)."""
    root = ET.parse(FIX / "layout_modes_roundtrip.xml").getroot()
    for g in root.find("modelGroups").findall("modelGroup"):
        assert "layout" in g.attrib          # xLights stores the mode as the `layout` attribute
        assert g.get("GridSize") is not None
