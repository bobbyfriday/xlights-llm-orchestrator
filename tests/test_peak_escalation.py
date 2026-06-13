"""Tests for peak escalation — the show's payoff section reads display-wide and bright."""

from __future__ import annotations

from types import SimpleNamespace

from xlights_orchestrator.pipeline.beats import (
    BED_BRIGHTNESS_FACTOR,
    ensemble_bed,
    peak_fill,
    peak_sections,
    wash_brightness,
)
from xlights_orchestrator.show_plan import SectionPlan

AVAIL = ["SEM_ALL", "SEM_BAND_GROUND", "SEM_ARCHES", "SEM_FOCAL"]


def _plan(intensities):
    return SimpleNamespace(sections=[
        SectionPlan(start_ms=i * 1000, end_ms=i * 1000 + 1000, target_groups=["SEM_ARCHES"],
                    effect_family="On", intensity=v, palette=["gold", "blue"])
        for i, v in enumerate(intensities)])


def test_peak_is_max_within_band_and_floor():
    p = _plan([0.1, 0.35, 0.81, 0.69, 1.0, 0.72])
    assert peak_sections(p) == {4}                       # only the 1.0 section


def test_tie_peaks_both_qualify():
    # max 0.95, band 0.12 -> threshold 0.83: a double-chorus all qualifies
    assert peak_sections(_plan([0.2, 0.9, 0.85, 0.95])) == {1, 2, 3}
    assert peak_sections(_plan([0.2, 0.95, 0.5, 0.92])) == {1, 3}   # 0.5 excluded


def test_quiet_show_has_no_peak():
    assert peak_sections(_plan([0.1, 0.4, 0.55, 0.5])) == set()     # max 0.55 < floor 0.66


def test_peak_fill_is_full_bright_whole_display():
    sec = _plan([1.0]).sections[0]
    fill = peak_fill(sec, 1.0, AVAIL, [])
    assert fill.target == "SEM_ALL"                       # broadest ensemble
    full = wash_brightness(1.0)
    assert fill.extra_settings["C_SLIDER_Brightness"] == str(int(round(full)))   # NOT 0.6x


def test_peak_fill_brighter_than_the_dim_bed():
    sec = _plan([1.0]).sections[0]
    fill = int(peak_fill(sec, 1.0, AVAIL, []).extra_settings["C_SLIDER_Brightness"])
    bed = int(ensemble_bed(sec, 1.0, AVAIL, set()).extra_settings["C_SLIDER_Brightness"])
    assert fill > bed                                     # the payoff outshines the frame
    assert abs(bed - wash_brightness(1.0) * BED_BRIGHTNESS_FACTOR) < 1


def test_high_but_not_peak_keeps_dim_bed():
    # the run wiring picks ensemble_bed for non-peak sections; verify a 0.7 section still beds dim
    sec = _plan([0.7]).sections[0]
    assert ensemble_bed(sec, 0.7, AVAIL, set()) is not None


def test_peak_fill_skips_only_a_real_spanning_bed():
    from xlights_orchestrator.show_plan import EffectInstruction
    sec = _plan([1.0]).sections[0]
    # a 0.3s Strobe blip on SEM_ALL is punctuation, NOT a bed → fill still fires (the bug)
    blip = [EffectInstruction(target="SEM_ALL", effect_type="Strobe", look_id="x",
                              start_ms=0, end_ms=300)]
    assert peak_fill(sec, 1.0, AVAIL, blip).target == "SEM_ALL"
    # a section-spanning On bed on SEM_ALL → skip it, fall to the next broad group
    bed = [EffectInstruction(target="SEM_ALL", effect_type="On", look_id="x",
                             start_ms=0, end_ms=1000)]
    assert peak_fill(sec, 1.0, AVAIL, bed).target == "SEM_BAND_GROUND"
    # both broad targets bedded → nothing to add
    both = bed + [EffectInstruction(target="SEM_BAND_GROUND", effect_type="On", look_id="x",
                                    start_ms=0, end_ms=1000)]
    assert peak_fill(sec, 1.0, AVAIL, both) is None
