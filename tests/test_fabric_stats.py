"""Fabric-measurement unit tests + the hermetic golden canary (capability `fabric-measurement`).

Two parser tests (`stats_from_instructions` over hand-built instruction lists with known
shares/durations; `stats_from_xsq` over a small synthetic `.xsq` written by the test) and the
canary that guards `tests/fixtures/golden_instructions.json` against silent fabric re-inversion —
energetic sections only, quiet/rest/gesture exempt.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from measure_fabric import (
    COMMUNITY,
    FabricStats,
    effect_family,
    expansion_from_rgbeffects,
    stats_from_effect_instructions,
    stats_from_instructions,
    stats_from_xsq,
)
from xlights_orchestrator.show_plan import EffectInstruction

GOLDEN = Path(__file__).parent / "fixtures" / "golden_instructions.json"

# The golden fixture's two known sections (see tests/test_golden_pipeline.py::_show_plan):
# §0 intensity 0.45 (quiet build), §1 intensity 0.92 (peak). No treatments (pre-Phase 2).
GOLDEN_SECTIONS = {
    0: {"intensity": 0.45, "treatment": None, "start_ms": 0, "end_ms": 12000},
    1: {"intensity": 0.92, "treatment": None, "start_ms": 12000, "end_ms": 24000},
}


def _ins(effect, target="SEM_ARCHES", *, start=0, end=1000, layer=0, si=0, extra=None):
    return {"effect_type": effect, "target": target, "start_ms": start, "end_ms": end,
            "layer": layer, "section_index": si, "extra_settings": extra or {}, "knob_values": {}}


# -- family classification ----------------------------------------------------------------------
def test_effect_family_split():
    assert effect_family("SingleStrand") == "motion"      # the community's #1
    assert effect_family("Spirals") == "motion"
    assert effect_family("On") == "punctuation"           # the inversion target
    assert effect_family("Twinkle") == "punctuation"
    assert effect_family("Shockwave") == "punctuation"    # a hit, counted as punctuation (§1)
    assert effect_family("Color Wash") == "bed"
    assert effect_family("Fireworks") == "feature"
    assert effect_family("Nonexistent") == "other"


def test_effect_family_canonicalizes_display_names():
    # xLights writes the display name into a finalized .xsq ('Single Strand'); it must classify the
    # same as the placeable form, else our own output measures a false 'other' bucket.
    assert effect_family("Single Strand") == "motion"
    assert effect_family("SingleStrand") == effect_family("Single Strand")


# -- stats_from_instructions --------------------------------------------------------------------
def test_stats_from_instructions_known_shares_and_durations():
    # 4 motion + 4 On + 2 Twinkle = 10 effects over 60s → 10/min. motion 40%, punctuation 60%.
    instrs = (
        [_ins("SingleStrand", start=0, end=1000) for _ in range(4)]
        + [_ins("On", start=0, end=500) for _ in range(4)]
        + [_ins("Twinkle", start=0, end=250) for _ in range(2)]
    )
    stats = stats_from_instructions(instrs, duration_s=60.0)
    assert isinstance(stats, FabricStats)
    assert stats.total == 10
    assert stats.effects_per_min == 10.0
    assert stats.share_by_family["motion"] == 0.4
    assert stats.share_by_family["punctuation"] == 0.6
    assert stats.share_by_type["On"] == 0.4
    assert stats.share_by_type["Twinkle"] == 0.2
    # median durations by type
    assert stats.duration_p50_by_type["SingleStrand"] == 1000.0
    assert stats.duration_p50_by_type["On"] == 500.0
    assert stats.duration_p50_by_type["Twinkle"] == 250.0


def test_stats_blend_transition_and_value_curve_shares():
    instrs = [
        _ins("SingleStrand", extra={"T_CHOICE_LayerMethod": "Max"}),
        _ins("Bars", extra={"T_CHOICE_In_Transition_Type": "Wipe"}),
        _ins("On", extra={"C_VALUECURVE_Brightness": "Active=TRUE|Type=Ramp|"}),
        _ins("Spirals", extra={"E_VALUECURVE_Spirals_Rotation": "Active=TRUE|Type=Ramp|"}),
        _ins("Pinwheel", extra={"E_VALUECURVE_Pinwheel_Twist": "Active=FALSE|Type=Ramp|"}),  # inert
    ]
    stats = stats_from_instructions(instrs, duration_s=60.0)
    assert stats.blend_mode_share == 0.2            # 1 of 5
    assert stats.transition_share == 0.2            # 1 of 5
    # 2 active value curves: 1 brightness, 1 motion (the inactive Twist is not counted)
    assert stats.value_curve_kinds["brightness"] == 0.5
    assert stats.value_curve_kinds["motion"] == 0.5


def test_per_section_energy_bucketing():
    # §0 quiet (i=0.2): mostly punctuation. §1 peak (i=0.9): mostly motion.
    instrs = (
        [_ins("On", si=0, start=0, end=1000) for _ in range(8)]
        + [_ins("SingleStrand", si=1, start=12000, end=13000) for _ in range(8)]
        + [_ins("On", si=1, start=12000, end=13000) for _ in range(2)]
    )
    sections = {
        0: {"intensity": 0.2, "treatment": None, "start_ms": 0, "end_ms": 12000},
        1: {"intensity": 0.9, "treatment": None, "start_ms": 12000, "end_ms": 24000},
    }
    stats = stats_from_instructions(instrs, duration_s=24.0, sections=sections)
    by_si = {s.section_index: s for s in stats.per_section}
    assert by_si[0].intensity == 0.2 and not by_si[0].energetic       # quiet exempt
    assert by_si[1].intensity == 0.9 and by_si[1].energetic           # peak evaluated
    assert by_si[0].motion_share == 0.0
    assert by_si[1].motion_share == 0.8
    assert by_si[1].on_twinkle_share == 0.2
    # the energetic accessor selects only the peak
    assert [s.section_index for s in stats.energetic_sections] == [1]


def test_treatment_exempts_rest_and_gesture():
    instrs = [_ins("On", si=0), _ins("On", si=1)]
    sections = {
        0: {"intensity": 0.9, "treatment": "rest", "start_ms": 0, "end_ms": 1000},     # loud but rest
        1: {"intensity": 0.9, "treatment": "full", "start_ms": 0, "end_ms": 1000},
    }
    stats = stats_from_instructions(instrs, duration_s=2.0, sections=sections)
    by_si = {s.section_index: s for s in stats.per_section}
    assert not by_si[0].energetic          # rest treatment exempts even a loud section
    assert by_si[1].energetic              # full is evaluated


def test_prop_row_expansion_scales_group_targets():
    # 5 group-targeted rows (SEM_) + 5 per-prop rows over 60s. expansion 10 → group rows count ×10.
    instrs = ([_ins("SingleStrand", target="SEM_ARCHES") for _ in range(5)]
              + [_ins("SingleStrand", target="Arch-01") for _ in range(5)])
    stats = stats_from_instructions(instrs, duration_s=60.0, per_prop_expansion=10.0)
    # raw = 10/min; prop-row = (5*10 + 5)/1 = 55/min
    assert stats.effects_per_min == 10.0
    assert stats.prop_row_effects_per_min == 55.0
    assert stats.per_prop_expansion == 10.0


def test_prop_row_absent_when_no_expansion():
    stats = stats_from_instructions([_ins("On", target="SEM_ALL")], duration_s=60.0)
    assert stats.prop_row_effects_per_min is None          # null column when unavailable
    assert stats.per_prop_expansion is None


# -- stats_from_xsq -----------------------------------------------------------------------------
def _write_synthetic_xsq(path: Path) -> None:
    """A ≤20-effect synthetic .xsq (ElementTree, no xLights): an EffectDB + two model rows."""
    root = ET.Element("xsequence")
    edb = ET.SubElement(root, "EffectDB")
    ET.SubElement(edb, "Effect").text = "E_CHOICE_Chase_Type1=Left-Right,T_CHOICE_LayerMethod=Max"
    ET.SubElement(edb, "Effect").text = "E_VALUECURVE_Spirals_Rotation=Active=TRUE|Type=Ramp|"
    ET.SubElement(edb, "Effect").text = ""                              # a plain On, no settings
    ee = ET.SubElement(root, "ElementEffects")
    m1 = ET.SubElement(ee, "Element", {"type": "model", "name": "SEM_ARCHES"})
    lay1 = ET.SubElement(m1, "EffectLayer")
    # two SingleStrand chase cells (ref 0) and one Spirals (ref 1)
    ET.SubElement(lay1, "Effect", {"ref": "0", "name": "SingleStrand",
                                   "startTime": "0", "endTime": "500"})
    ET.SubElement(lay1, "Effect", {"ref": "0", "name": "SingleStrand",
                                   "startTime": "500", "endTime": "1000"})
    ET.SubElement(lay1, "Effect", {"ref": "1", "name": "Spirals",
                                   "startTime": "1000", "endTime": "1600"})
    m2 = ET.SubElement(ee, "Element", {"type": "model", "name": "SEM_FOCAL"})
    lay2 = ET.SubElement(m2, "EffectLayer")
    ET.SubElement(lay2, "Effect", {"ref": "2", "name": "On", "startTime": "0", "endTime": "2000"})
    # a timing track element must be ignored
    t = ET.SubElement(ee, "Element", {"type": "timing", "name": "Bars"})
    tl = ET.SubElement(t, "EffectLayer")
    ET.SubElement(tl, "Effect", {"label": "x", "startTime": "0", "endTime": "500"})
    ET.ElementTree(root).write(path, encoding="UTF-8", xml_declaration=True)


def test_stats_from_xsq_parses_placed_effects(tmp_path):
    xsq = tmp_path / "synthetic.xsq"
    _write_synthetic_xsq(xsq)
    stats = stats_from_xsq(xsq)
    assert stats.total == 4                          # timing-track effect excluded
    # span 0..2000ms → duration 2s → 4 effects / (2/60) min = 120/min
    assert stats.duration_s == 2.0
    assert stats.effects_per_min == 120.0
    # 3 motion (2 SingleStrand + 1 Spirals) + 1 punctuation (On)
    assert stats.share_by_family["motion"] == 0.75
    assert stats.share_by_family["punctuation"] == 0.25
    # blend rides ref 0 (SingleStrand ×2); the active value curve is a motion param (Spirals rotation)
    assert stats.blend_mode_share == 0.5             # 2 of 4
    assert stats.value_curve_kinds["motion"] == 1.0
    # same report shape as the instruction mode
    assert set(stats.share_by_family) == {"motion", "punctuation", "bed", "feature", "other"}


def test_stats_from_xsq_same_shape_as_instructions(tmp_path):
    xsq = tmp_path / "s.xsq"
    _write_synthetic_xsq(xsq)
    a = stats_from_xsq(xsq)
    b = stats_from_instructions([_ins("SingleStrand")], duration_s=1.0)
    assert type(a) is type(b) is FabricStats
    assert set(vars(a)) == set(vars(b))              # identical field set → directly comparable


def test_stats_from_xsq_canonicalizes_display_names(tmp_path):
    """A finalized .xsq may store the display name 'Single Strand' — it must count as motion, not
    fall into 'other' (the real-output miscount that hid our motion share)."""
    root = ET.Element("xsequence")
    ET.SubElement(root, "EffectDB")
    ee = ET.SubElement(root, "ElementEffects")
    m = ET.SubElement(ee, "Element", {"type": "model", "name": "SEM_ARCHES"})
    lay = ET.SubElement(m, "EffectLayer")
    ET.SubElement(lay, "Effect", {"name": "Single Strand", "startTime": "0", "endTime": "500"})
    ET.SubElement(lay, "Effect", {"name": "Single Strand", "startTime": "500", "endTime": "1000"})
    p = tmp_path / "spaced.xsq"
    ET.ElementTree(root).write(p, encoding="UTF-8", xml_declaration=True)
    stats = stats_from_xsq(p)
    assert stats.share_by_family["motion"] == 1.0            # both 'Single Strand' → motion
    assert stats.share_by_type["SingleStrand"] == 1.0        # collapsed to the placeable key


# -- expansion from rgbeffects ------------------------------------------------------------------
def test_expansion_from_rgbeffects(tmp_path):
    root = ET.Element("xrgb")
    mg = ET.SubElement(root, "modelGroups")
    ET.SubElement(mg, "modelGroup", {"name": "SEM_ARCHES", "models": "A,B,C,D"})   # 4
    ET.SubElement(mg, "modelGroup", {"name": "SEM_FOCAL", "models": "F,G"})        # 2
    ET.SubElement(mg, "modelGroup", {"name": "UserGroup", "models": "X,Y,Z"})      # non-SEM, ignored
    p = tmp_path / "rgbeffects.xml"
    ET.ElementTree(root).write(p)
    assert expansion_from_rgbeffects(p) == 3.0                 # mean(4, 2)
    assert expansion_from_rgbeffects(p, {"SEM_ARCHES"}) == 4.0  # only the targeted group
    assert expansion_from_rgbeffects(tmp_path / "missing.xml") is None


# -- the golden canary --------------------------------------------------------------------------
# Loose bounds so ordinary tuning has headroom, but a re-inversion (motion collapses / On+Twinkle
# balloons) in the golden fixture's ENERGETIC section trips the guard. Quiet/rest/gesture exempt.
CANARY_MOTION_FLOOR = 0.20           # energetic-section motion share must not fall below this
CANARY_ON_TWINKLE_CEIL = 0.75        # ...nor On+Twinkle rise above this


def _golden_stats() -> FabricStats:
    instrs = json.loads(GOLDEN.read_text())
    return stats_from_instructions(instrs, duration_s=24.0, sections=GOLDEN_SECTIONS)


def test_golden_energetic_section_is_identified():
    stats = _golden_stats()
    energetic = stats.energetic_sections
    assert energetic, "the golden fixture must have at least one energetic section to guard"
    # §1 (i=0.92) is energetic; §0 (i=0.45) is exempt (below 0.5)
    assert {s.section_index for s in energetic} == {1}


def test_golden_fabric_not_reinverted():
    """Canary: the energetic section's motion share stays above the floor and On+Twinkle below the
    ceiling. A change that re-inverts the fabric (motion → punctuation) trips this, naming the share.
    """
    stats = _golden_stats()
    for s in stats.energetic_sections:
        assert s.motion_share >= CANARY_MOTION_FLOOR, (
            f"§{s.section_index} motion share {s.motion_share:.0%} < floor "
            f"{CANARY_MOTION_FLOOR:.0%} — the fabric re-inverted toward punctuation")
        assert s.on_twinkle_share <= CANARY_ON_TWINKLE_CEIL, (
            f"§{s.section_index} On+Twinkle {s.on_twinkle_share:.0%} > ceiling "
            f"{CANARY_ON_TWINKLE_CEIL:.0%} — punctuation re-dominated the energetic fabric")


def test_canary_exempts_quiet_sections():
    """A quiet section that is all punctuation must NOT trip the canary (deliberate stillness)."""
    instrs = [_ins("On", si=0) for _ in range(10)]
    sections = {0: {"intensity": 0.2, "treatment": None, "start_ms": 0, "end_ms": 12000}}
    stats = stats_from_instructions(instrs, duration_s=12.0, sections=sections)
    assert stats.energetic_sections == []          # nothing to assert → the canary stays silent


def test_community_aggregates_frozen():
    """The frozen §2.1 goalpost is present so the comparison runs without the corpus."""
    assert COMMUNITY.motion_share == 0.58
    assert COMMUNITY.effects_per_min_typical == 1300.0
    assert COMMUNITY.max_layer_depth == 19


# -- source attribution (transient; report-only) ------------------------------------------------
def test_source_tag_excluded_from_dump_but_read_for_report():
    """The `source` provenance is excluded from model_dump (cache/golden byte-identical) yet the
    per-type-per-source breakdown reads it off the live objects — the tuning-visibility feature."""
    ins = EffectInstruction(target="SEM_ARCHES", effect_type="On", look_id="On#0",
                            start_ms=0, end_ms=1000, source="accents")
    assert "source" not in ins.model_dump()                 # transient — never persisted
    # an On row could be a bed, an accent, or an LLM wash; the report tells them apart:
    rows = [
        EffectInstruction(target="SEM_ALL", effect_type="On", look_id="On#0",
                          start_ms=0, end_ms=12000, source="bed"),
        EffectInstruction(target="SEM_ARCHES", effect_type="On", look_id="On#0",
                          start_ms=0, end_ms=250, source="accents"),
        EffectInstruction(target="SEM_CANES", effect_type="On", look_id="On#0",
                          start_ms=0, end_ms=250, source="accents"),
    ]
    stats = stats_from_effect_instructions(rows, duration_s=60.0)
    assert stats.source_by_type["On"] == {"bed": 1, "accents": 2}


def test_source_absent_from_cache_dumps():
    """Measuring the on-disk instructions cache (dumps, no source) yields an empty source table."""
    stats = stats_from_instructions([_ins("On")], duration_s=60.0)
    assert stats.source_by_type == {}
