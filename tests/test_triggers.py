"""Tests for curated trigger effects (cookbook-defined semantic accents)."""

from __future__ import annotations

from types import SimpleNamespace

from xlights_orchestrator.pipeline import triggers as T
from xlights_orchestrator.show_plan import SectionPlan

AVAIL = ["SEM_ALL", "SEM_HOUSE", "SEM_FOCAL", "SEM_ARCHES", "SEM_CANES", "SEM_MINITREES"]


def _sec(i, intensity=0.8, palette=("gold", "blue")):
    return SectionPlan(start_ms=i * 10000, end_ms=i * 10000 + 10000, target_groups=["SEM_ARCHES"],
                       effect_family="On", intensity=intensity, palette=list(palette))


def _ep(t, rms):  # EnergyPoint-like
    return SimpleNamespace(time=t, rms=rms)


def _sa(*, drums_onsets=(), drums_arc=(), guitar_share=0.0, lyrics=None, stems_extra=None,
        section_inst=None):
    stems = []
    if drums_onsets or drums_arc:
        stems.append(SimpleNamespace(stem="drums", onsets=list(drums_onsets),
                                     energy_arc=[_ep(t, r) for t, r in drums_arc]))
    for s in (stems_extra or []):
        stems.append(s)
    return SimpleNamespace(stems=stems, lyrics=lyrics,
                           section_instrumentation=section_inst or [])


# -- cookbook parse ------------------------------------------------------------

def test_parse_cookbook_valid_and_bad():
    text = """
## Good One
- detector: drum_onsets
- effect: Shockwave
- render: per_model
- enabled: true

## No Detector
- effect: On

## Disabled
- detector: drum_onsets
- enabled: false
"""
    specs = T.parse_cookbook(text)
    names = {s.name for s in specs}
    assert "Good One" in names and "No Detector" not in names   # detector-less dropped
    good = next(s for s in specs if s.name == "Good One")
    assert good.effect == "Shockwave" and good.render == "per_model" and good.enabled
    assert next(s for s in specs if s.name == "Disabled").enabled is False


def test_unknown_detector_skipped_not_fatal():
    specs = [T.TriggerSpec(name="X", detector="does_not_exist", effect="On")]
    assert T.realize_triggers(specs, _sa(), [_sec(0)], AVAIL) == []   # logged, no crash


# -- magnitude helper ----------------------------------------------------------

def test_energy_at_normalizes_to_peak():
    arc = [_ep(0, 0.0), _ep(1, 0.5), _ep(2, 1.0)]
    assert T.energy_at(arc, 2.0) == 1.0
    assert T.energy_at(arc, 1.0) == 0.5
    assert T.energy_at([], 1.0) == 0.0


# -- detectors -----------------------------------------------------------------

def test_drum_onsets_carry_magnitude():
    sa = _sa(drums_onsets=[1.0, 2.0], drums_arc=[(1.0, 0.2), (2.0, 1.0)])
    evs = T._drum_onsets(sa, [])
    assert [e.time_ms for e in evs] == [1000, 2000]
    assert evs[1].magnitude > evs[0].magnitude          # the 1.0-rms hit is bigger


def test_big_moment_is_top_magnitude_drum_hits_capped():
    # big moment = drum_onsets gated to top magnitude + whole_house + per-section cap (not 1)
    sa = _sa(drums_onsets=[1.0, 2.0, 5.0, 9.0],
             drums_arc=[(1.0, 0.3), (2.0, 0.95), (5.0, 0.9), (9.0, 0.2)],
             section_inst=[_inst(0, 0.5)])
    spec = T.TriggerSpec(name="big", detector="drum_onsets", effect="Shockwave",
                         render="whole_house", sections="any", select="all", density="10",
                         magnitude="top:50", color="fixed:white", direction="out")
    out = T.realize_triggers([spec], sa, [_sec(0)], AVAIL)
    assert len(out) == 2                                # top 50% of 4 hits = the two strongest
    assert all(o.render_style == "Per Preview" and o.target == "SEM_ALL" for o in out)
    starts = sorted(o.start_ms for o in out)
    assert starts == [2000, 5000]                       # the 0.95 and 0.9 hits, not 0.3/0.2


def test_lyric_color_word_event_word_precise():
    lyr = {"lines": [{"text": "paint it red tonight", "start": 4.0, "end": 6.0,
                      "words": [{"word": "paint", "start": 4.0, "end": 4.3},
                                {"word": "red", "start": 4.8, "end": 5.1}]}]}
    evs = T._lyric_color(_sa(lyrics=lyr), [])
    assert len(evs) == 1 and evs[0].color == "red" and evs[0].time_ms == 4800   # the word, not line


def test_lyric_color_line_precise_fallback():
    lyr = {"lines": [{"text": "everything is blue", "start": 4.0, "end": 6.0}]}   # no words
    evs = T._lyric_color(_sa(lyrics=lyr), [])
    assert len(evs) == 1 and evs[0].color == "blue" and evs[0].time_ms == 4000


# -- selection + realization ---------------------------------------------------

def _inst(i, drums):
    return SimpleNamespace(start_ms=i * 10000, end_ms=i * 10000 + 10000,
                           shares={"drums": drums}, dominant=["drums"])


def test_rotate_selects_subset_of_eligible():
    spec = T.TriggerSpec(name="r", detector="drum_onsets", select="rotate", sections="any")
    elig = [0, 1, 2, 3]
    s0 = T._select(spec, elig, 0)
    s1 = T._select(spec, elig, 1)
    assert s0 == {0, 2} and s1 == {1, 3}                # offset → different sections per trigger
    assert s0 != set(elig)                              # NOT every section


def test_drum_prominent_eligibility():
    sa = _sa(section_inst=[_inst(0, 0.4), _inst(1, 0.05)])
    spec = T.TriggerSpec(name="d", detector="drum_onsets", sections="drum_prominent")
    assert T._eligible_sections(spec, sa, [_sec(0), _sec(1)]) == [0]   # only the drum-heavy one


def test_periodic_drum_shockwaves_render_per_model_with_variety():
    sa = _sa(drums_onsets=[0.5, 1.5, 2.5, 3.5], drums_arc=[(t, 0.8) for t in (0.5, 1.5, 2.5, 3.5)],
             section_inst=[_inst(0, 0.5)])
    spec = T.TriggerSpec(name="p", detector="drum_onsets", effect="Shockwave", render="per_model",
                         sections="drum_prominent", select="all", density="per_onset",
                         color="anchor_alternate", direction="alternate")
    out = T.realize_triggers([spec], sa, [_sec(0)], AVAIL)
    assert len(out) == 4
    assert all(o.render_style == "Per Model Default" for o in out)
    assert len({o.target for o in out}) > 1                          # rotates across the pool
    assert out[0].palette_colors != out[1].palette_colors           # color alternates
    # direction alternates: out (start<end) then in (start>end)
    r0 = out[0].extra_settings; r1 = out[1].extra_settings
    assert int(r0["E_SLIDER_Shockwave_Start_Radius"]) < int(r0["E_SLIDER_Shockwave_End_Radius"])
    assert int(r1["E_SLIDER_Shockwave_Start_Radius"]) > int(r1["E_SLIDER_Shockwave_End_Radius"])


def test_density_cap_limits_per_section():
    sa = _sa(drums_onsets=[float(i) for i in range(1, 9)],
             drums_arc=[(float(i), 0.8) for i in range(1, 9)], section_inst=[_inst(0, 0.5)])
    spec = T.TriggerSpec(name="cap", detector="drum_onsets", effect="Shockwave",
                         render="whole_house", sections="any", select="all", density="3",
                         magnitude="any", color="fixed:white", direction="out")
    out = T.realize_triggers([spec], sa, [_sec(0)], AVAIL)
    assert len(out) == 3                                # 8 hits capped to 3 per section


def test_empty_cookbook_no_triggers():
    assert T.place_triggers(_sa(), [_sec(0)], AVAIL, "") == []
