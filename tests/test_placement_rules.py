"""Tests for the catalog §11 placement-rules QA + hard caps."""
from types import SimpleNamespace

from xlights_orchestrator.qa.rules import clamp_hard_caps, evaluate
from xlights_orchestrator.show_plan import EffectInstruction


def _ins(effect, target, si=0, start=0, end=2000):
    return EffectInstruction(target=target, effect_type=effect, look_id="x",
                             start_ms=start, end_ms=end, section_index=si)


def _plan(intensities):
    return SimpleNamespace(sections=[SimpleNamespace(intensity=x) for x in intensities])


def test_texture_on_linear_flagged():
    score, f = evaluate([_ins("Plasma", "SEM_ARCHES")], _plan([0.5]))
    assert score < 100 and f[0].metric == "rules" and "linear" in f[0].detail
    # texture on a canvas is fine
    assert evaluate([_ins("Plasma", "SEM_FOCAL")], _plan([0.5]))[0] == 100


def test_energy_band_mismatch_flagged():
    score, f = evaluate([_ins("Strobe", "SEM_FOCAL", si=0)], _plan([0.2]))   # energy-2 verse
    assert f and "defect" in f[0].detail
    # Strobe in a full-energy section is fine
    assert evaluate([_ins("Strobe", "SEM_FOCAL", si=0)], _plan([1.0]))[0] == 100


def test_same_feature_same_moment_is_one_gesture():
    a = _ins("Shockwave", "SEM_ALL", start=0, end=2000)
    b = _ins("Shockwave", "SEM_FOCAL", start=0, end=2000)     # same effect, same window, 2 groups
    assert evaluate([a, b], _plan([0.9]))[1] == []             # ONE gesture, not a violation


def test_overlapping_features_flagged():
    a = _ins("Shockwave", "SEM_ALL", start=0, end=2000)
    b = _ins("Fireworks", "SEM_FOCAL", start=1000, end=3000)
    score, f = evaluate([a, b], _plan([0.9]))
    assert any("one high-attention feature" in x.detail for x in f)
    # sequential features are fine
    b2 = _ins("Fireworks", "SEM_FOCAL", start=2500, end=4000)
    assert not [x for x in evaluate([a, b2], _plan([0.9]))[1] if "high-attention" in x.detail]


def test_clean_show_scores_100():
    assert evaluate([_ins("Spirals", "SEM_FOCAL", si=0)], _plan([0.8])) == (100, [])


def test_hard_caps_clamp():
    strobe = _ins("Strobe", "SEM_ALL", start=0, end=10000)
    shimmer = _ins("Shimmer", "SEM_ALL", start=0, end=20000)
    keep = _ins("Spirals", "SEM_FOCAL", start=0, end=20000)
    n = clamp_hard_caps([strobe, shimmer, keep], tempo_bpm=120)   # bar=2000ms → shimmer cap 4000
    assert n == 2
    assert strobe.end_ms == 1000 and shimmer.end_ms == 4000 and keep.end_ms == 20000
