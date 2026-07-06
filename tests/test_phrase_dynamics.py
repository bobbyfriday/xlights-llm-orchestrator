"""Phase 3 — phrase dynamics: sustained beds/washes carry an energy-shaped brightness curve
(rising swells, falling decays, flat holds); features/accents keep crisp constant levels."""
from __future__ import annotations

from xlights_orchestrator.pipeline.beats import section_energy_shape
from xlights_orchestrator.pipeline.generate import _phrase_brightness
from xlights_orchestrator.show_plan import EffectInstruction, SectionPlan
from xlights_core.audio import EnergyPoint, SongAnalysis


def _sa(pairs):
    return SongAnalysis(path="s", duration_s=24.0, sample_rate=44100,
                        energy_arc=[EnergyPoint(time=t, rms=r) for t, r in pairs])


def _sec(start=0, end=16000):
    return SectionPlan(start_ms=start, end_ms=end, target_groups=["G1"],
                       effect_family="On", intensity=0.6)


# -- energy shape -------------------------------------------------------------

def test_energy_shape_rising_falling_flat():
    sec = _sec(0, 12000)
    rising = _sa([(t, 0.2 + 0.05 * t) for t in range(0, 13)])
    falling = _sa([(t, 0.9 - 0.05 * t) for t in range(0, 13)])
    flat = _sa([(t, 0.5) for t in range(0, 13)])
    assert section_energy_shape(rising, sec) == "rising"
    assert section_energy_shape(falling, sec) == "falling"
    assert section_energy_shape(flat, sec) == "flat"


def test_energy_shape_sparse_is_flat():
    assert section_energy_shape(_sa([(0, 0.5)]), _sec()) == "flat"


# -- phrase brightness on beds/washes -----------------------------------------

def _bed(effect="On", start=0, end=16000):
    return EffectInstruction(target="G1", effect_type=effect, look_id=f"{effect}#0",
                             start_ms=start, end_ms=end)


BAR_MS = 2000.0


def test_rising_bed_gets_an_upward_ramp():
    out = _phrase_brightness(_bed(), "rising", 180.0, BAR_MS)
    # a value curve (ramp), not a flat C_SLIDER_Brightness
    assert any("ValueCurve" in k or "VALUECURVE" in k.upper() for k in out) or \
        "C_SLIDER_Brightness" not in out
    assert "C_SLIDER_Brightness" not in out                 # a curve replaced the flat level


def test_falling_bed_gets_a_downward_ramp():
    out = _phrase_brightness(_bed(), "falling", 180.0, BAR_MS)
    assert "C_SLIDER_Brightness" not in out                 # a ramp, not a flat level


def test_flat_bed_is_a_constant_level():
    out = _phrase_brightness(_bed(), "flat", 180.0, BAR_MS)
    assert out.get("C_SLIDER_Brightness") == "180"          # crisp constant (unchanged behavior)


def test_short_bed_stays_flat_even_when_rising():
    short = _bed(end=1000)                                   # < 2 bars → no phrase curve
    out = _phrase_brightness(short, "rising", 180.0, BAR_MS)
    assert out.get("C_SLIDER_Brightness") == "180"


def test_feature_effect_keeps_crisp_level():
    # a non-bed/wash effect (a moving feature) never gets a phrase curve, even over a rising slice
    feature = EffectInstruction(target="G1", effect_type="Butterfly", look_id="Butterfly#0",
                                start_ms=0, end_ms=16000)
    out = _phrase_brightness(feature, "rising", 180.0, BAR_MS)
    assert out.get("C_SLIDER_Brightness") == "180"
