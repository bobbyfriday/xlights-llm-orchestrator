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


def test_rotate_selects_energetic_subset():
    spec = T.TriggerSpec(name="r", detector="drum_onsets", select="rotate", sections="any")
    secs = [_sec(0, intensity=0.2), _sec(1, intensity=0.9), _sec(2, intensity=0.3),
            _sec(3, intensity=0.95)]
    sel = T._select(spec, [0, 1, 2, 3], 0, secs)
    assert sel == {1, 3}                                # the two MOST energetic, not positional
    assert sel != {0, 1, 2, 3}                          # still a subset (not every section)


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


def test_triggers_are_on_top_and_clamp_exempt():
    from xlights_orchestrator.effect_emitter import clamp_layer_budget
    from xlights_orchestrator.show_plan import EffectInstruction
    sa = _sa(drums_onsets=[0.5, 1.5], drums_arc=[(0.5, 0.8), (1.5, 0.8)],
             section_inst=[_inst(0, 0.5)])
    spec = T.TriggerSpec(name="pop", detector="drum_onsets", effect="On", render="per_model",
                         sections="drum_prominent", select="all", density="per_onset",
                         color="anchor_alternate", direction="none")
    trigs = T.realize_triggers([spec], sa, [_sec(0)], AVAIL)
    assert trigs and all(t.on_top for t in trigs)               # marked punch-through
    # 4 fabric layers already saturate the prop at the trigger's time → fabric clamps, triggers don't
    fabric = [EffectInstruction(target=trigs[0].target, effect_type="Spirals", look_id="x",
                                start_ms=0, end_ms=3000) for _ in range(6)]
    kept, dropped = clamp_layer_budget(fabric + trigs)
    assert dropped > 0                                           # excess fabric trimmed
    assert all(t in kept for t in trigs)                        # every trigger survives


def test_top_layer_sits_above_a_higher_spanning_layer():
    from xlights_orchestrator.effect_emitter import _top_layer, _free_layer
    # SEM_ARCHES: layer 0 has a short cell (gap after), layer 3 has a full-section wash spanning
    occ = {("SEM_ARCHES", 0): [(0, 250)], ("SEM_ARCHES", 3): [(0, 10000)]}
    # _free_layer would drop a 500ms pop at t=300 into layer 0 (free there) — UNDER the layer-3 wash
    assert _free_layer(occ, "SEM_ARCHES", 300, 800, 0) == 0
    # _top_layer puts it above the spanning layer-3 wash → visible
    assert _top_layer(occ, "SEM_ARCHES", 300, 800) == 4
    # nothing overlapping → layer 0
    assert _top_layer(occ, "SEM_CANES", 300, 800) == 0


# -- stem-parameterized triggers (add-melodic-triggers) ------------------------

def _inst_sh(start_ms, end_ms, shares):
    return SimpleNamespace(start_ms=start_ms, end_ms=end_ms, shares=dict(shares))


def _sa_stem(stem, onsets, arc=((0, 1.0),), section_inst=None):
    s = SimpleNamespace(stem=stem, onsets=list(onsets), energy_arc=[_ep(t, r) for t, r in arc])
    return SimpleNamespace(stems=[s], lyrics=None, section_instrumentation=section_inst or [])


def test_stem_onsets_fires_on_named_stem():
    sa = _sa_stem("piano", [1.0, 2.0, 3.0])
    spec = T.TriggerSpec(name="P", detector="stem_onsets", stem="piano")
    evs = T._stem_onsets(sa, [], spec)
    assert [e.time_ms for e in evs] == [1000, 2000, 3000]
    assert all(e.stem == "piano" for e in evs)


def test_stem_onsets_default_stem_is_drums():
    sa = _sa_stem("drums", [0.5, 1.5])
    spec = T.TriggerSpec(name="D", detector="stem_onsets")        # no stem → default "drums"
    assert [e.time_ms for e in T._stem_onsets(sa, [], spec)] == [500, 1500]


def test_drum_onsets_alias_forces_drums():
    # even if a spec names piano, the drum_onsets detector reads drums (back-compat)
    sa = SimpleNamespace(stems=[
        SimpleNamespace(stem="drums", onsets=[1.0], energy_arc=[_ep(0, 1.0)]),
        SimpleNamespace(stem="piano", onsets=[2.0, 3.0], energy_arc=[_ep(0, 1.0)])],
        lyrics=None, section_instrumentation=[])
    spec = T.TriggerSpec(name="X", detector="drum_onsets", stem="piano")
    assert [e.stem for e in T._drum_onsets(sa, [], spec)] == ["drums"]


def test_absent_stem_yields_no_events():
    sa = _sa_stem("drums", [1.0])
    spec = T.TriggerSpec(name="P", detector="stem_onsets", stem="piano")  # no piano stem present
    assert T._stem_onsets(sa, [], spec) == []


def test_stem_prominent_eligibility_uses_spec_stem():
    sections = [_sec(0), _sec(1)]
    inst = [_inst_sh(0, 10000, {"piano": 0.05}), _inst_sh(10000, 20000, {"piano": 0.5})]
    sa = SimpleNamespace(stems=[], lyrics=None, section_instrumentation=inst)
    spec = T.TriggerSpec(name="P", detector="stem_onsets", sections="stem_prominent", stem="piano")
    assert T._eligible_sections(spec, sa, sections) == [1]        # only the piano-prominent one


def test_piano_trigger_rotates_groups_per_note():
    onsets = [1.0, 2.0, 3.0, 4.0]
    inst = [_inst_sh(0, 10000, {"piano": 0.6})]
    sa = _sa_stem("piano", onsets, section_inst=inst)
    spec = T.TriggerSpec(name="Piano", detector="stem_onsets", effect="On", render="per_model",
                         groups="rhythm", sections="stem_prominent", stem="piano",
                         select="all", density="per_onset")
    out = T.realize_triggers([spec], sa, [_sec(0)], AVAIL)
    assert len(out) == 4
    rhythm = {"SEM_ARCHES", "SEM_CANES", "SEM_MINITREES"}
    assert all(o.target in rhythm for o in out)
    assert len({o.target for o in out}) >= 2                      # walks across groups
    assert all(o.on_top and o.effect_type == "On" for o in out)
