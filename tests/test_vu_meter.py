"""The deterministic VU Meter layer: a music-reactive feature on energetic sections."""

from __future__ import annotations

from xlights_orchestrator.pipeline.beats import VU_MIN_INTENSITY, place_vu_meter
from xlights_orchestrator.show_plan import SectionPlan

WIDE = ["SEM_BAND_GROUND", "SEM_ALL", "SEM_ARCHES", "SEM_FOCAL"]


def _sec(intensity=0.8, **kw):
    kw.setdefault("target_groups", ["SEM_ARCHES"])
    kw.setdefault("effect_family", "On")
    kw.setdefault("palette", ["Red", "Green", "Blue"])
    return SectionPlan(start_ms=12000, end_ms=24000, intensity=intensity, **kw)


def test_places_vu_meter_on_wide_group_for_energetic_section():
    vu = place_vu_meter(_sec(intensity=0.9), WIDE, 0.9)
    assert vu is not None
    assert vu.effect_type == "VU Meter"
    assert vu.target == "SEM_BAND_GROUND"            # preferred wide group
    assert vu.look_id.startswith("VU Meter")
    assert (vu.start_ms, vu.end_ms) == (12000, 24000)   # spans the section
    assert vu.render_style == "Per Preview"          # bars span the group


def test_skips_quiet_sections():
    assert place_vu_meter(_sec(intensity=0.3), WIDE, 0.3) is None
    assert place_vu_meter(_sec(), WIDE, VU_MIN_INTENSITY - 0.01) is None


def test_skips_when_no_wide_group():
    assert place_vu_meter(_sec(intensity=0.9), ["SEM_ARCHES", "SEM_FOCAL"], 0.9) is None


def test_look_rotates_by_seed():
    a = place_vu_meter(_sec(intensity=0.9), WIDE, 0.9, seed=0)
    b = place_vu_meter(_sec(intensity=0.9), WIDE, 0.9, seed=1)
    assert a.look_id != b.look_id                    # different sections get different looks
