"""Tests for the catalog §11 placement-rules QA + hard caps."""
from types import SimpleNamespace

from xlights_orchestrator.pipeline.tuning import MOTION_SHARE_MIN
from xlights_orchestrator.qa.rules import MOTION_SHARE_INTENSITY, clamp_hard_caps, evaluate
from xlights_orchestrator.show_plan import EffectInstruction


def _ins(effect, target, si=0, start=0, end=2000):
    return EffectInstruction(target=target, effect_type=effect, look_id="x",
                             start_ms=start, end_ms=end, section_index=si)


def _plan(intensities, treatments=None):
    treatments = treatments or [""] * len(intensities)
    return SimpleNamespace(sections=[SimpleNamespace(intensity=x, treatment=t)
                                     for x, t in zip(intensities, treatments)])


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
    findings = evaluate([a, b], _plan([0.9]))[1]               # ONE gesture, not a violation
    assert [f for f in findings if f.objective] == []          # (motion-share advisory may appear)


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


# -- motion-share advisory floor (2026-07 re-measurement: 0.30 → 0.40) --------------------------
def _motion_findings(motion_n, static_n, *, intensity=0.9, treatment=""):
    instrs = ([_ins("SingleStrand", "SEM_FOCAL") for _ in range(motion_n)]
              + [_ins("On", "SEM_YARD") for _ in range(static_n)])
    _, findings = evaluate(instrs, _plan([intensity], [treatment]))
    return [f for f in findings if "motion-effect share" in f.detail]


def test_motion_share_floor_is_the_remeasured_value():
    assert MOTION_SHARE_MIN == 0.40                              # cites the 2026-07 re-measurement


def test_advisory_fires_below_and_is_silent_above_the_floor():
    # 3 motion / 10 total = 30% < 40% → advisory fires (this is what the raised floor now catches)
    fired = _motion_findings(3, 7)
    assert fired and not fired[0].objective                     # advisory, never gating
    # 6 motion / 10 total = 60% ≥ 40% → silent
    assert _motion_findings(6, 4) == []
    # exactly at the floor (4/10 = 40%) is not below → silent
    assert _motion_findings(4, 6) == []


def test_advisory_gated_by_intensity():
    # a 30%-motion section BELOW the intensity gate is not flagged (deliberate quiet)
    assert _motion_findings(3, 7, intensity=MOTION_SHARE_INTENSITY - 0.1) == []
    # at/above the gate, the same fabric IS flagged
    assert _motion_findings(3, 7, intensity=MOTION_SHARE_INTENSITY) != []


def test_advisory_exempts_rest_and_gesture_treatments():
    # a loud (i=0.9) but rest/gesture-treated section is deliberately still → not a regression
    assert _motion_findings(3, 7, treatment="rest") == []
    assert _motion_findings(3, 7, treatment="gesture") == []
    # a full-treatment loud section with the same fabric IS flagged
    assert _motion_findings(3, 7, treatment="full") != []


def test_advisory_detail_cites_the_remeasurement():
    fired = _motion_findings(3, 7)
    assert fired and "2026-07 re-measurement" in fired[0].detail


# -- demote_offpeak_hits -----------------------------------------------------------------
def test_demote_strobe_to_shockwave_off_peak():
    from xlights_orchestrator.qa.rules import demote_offpeak_hits
    from xlights_orchestrator.pipeline.effect_meta import SHOCKWAVE_SETTINGS
    strobe = _ins("Strobe", "SEM_ALL", start=0, end=500)
    spiral = _ins("Spirals", "SEM_FOCAL", start=0, end=2000)
    instrs = [strobe, spiral]
    n = demote_offpeak_hits(instrs, is_peak=False)
    assert n == 1
    assert instrs[0].effect_type == "Shockwave"
    assert instrs[1].effect_type == "Spirals"    # untouched
    for k in SHOCKWAVE_SETTINGS:
        assert instrs[0].extra_settings.get(k) == SHOCKWAVE_SETTINGS[k]


def test_demote_strobe_is_noop_at_peak():
    from xlights_orchestrator.qa.rules import demote_offpeak_hits
    strobe = _ins("Strobe", "SEM_ALL", start=0, end=500)
    instrs = [strobe]
    n = demote_offpeak_hits(instrs, is_peak=True)
    assert n == 0
    assert instrs[0].effect_type == "Strobe"


def test_shimmer_capped_per_section():
    from xlights_orchestrator.qa.rules import demote_offpeak_hits
    from xlights_orchestrator.pipeline.tuning import SHIMMER_MAX_PER_SECTION
    shimmers = [_ins("Shimmer", "SEM_FOCAL", si=0, start=i * 1000, end=i * 1000 + 800)
                for i in range(SHIMMER_MAX_PER_SECTION + 2)]
    spiral = _ins("Spirals", "SEM_FOCAL", si=0, start=0, end=3000)
    instrs = shimmers + [spiral]
    n = demote_offpeak_hits(instrs, is_peak=False)
    remaining_shimmers = [x for x in instrs if x.effect_type == "Shimmer"]
    assert len(remaining_shimmers) == SHIMMER_MAX_PER_SECTION
    assert n == 2                                              # the 2 excess Shimmers removed
    assert any(x.effect_type == "Spirals" for x in instrs)   # non-Shimmer untouched


def test_shimmer_excess_keeps_earliest():
    from xlights_orchestrator.qa.rules import demote_offpeak_hits
    from xlights_orchestrator.pipeline.tuning import SHIMMER_MAX_PER_SECTION
    # earliest starts must survive
    shimmers = [_ins("Shimmer", "SEM_FOCAL", si=0, start=i * 1000, end=i * 1000 + 500)
                for i in range(SHIMMER_MAX_PER_SECTION + 1)]
    instrs = list(shimmers)
    demote_offpeak_hits(instrs, is_peak=False)
    surviving_starts = sorted(x.start_ms for x in instrs if x.effect_type == "Shimmer")
    expected = sorted(x.start_ms for x in shimmers[:SHIMMER_MAX_PER_SECTION])
    assert surviving_starts == expected


def test_accent_shockwave_excluded_from_feature_rule():
    """Accent-sourced Shockwaves must NOT trip rule #4 even when overlapping a feature Shockwave."""
    sw_accent = _ins("Shockwave", "SEM_SPINNERS", start=0, end=600)
    sw_accent.source = "accents"
    sw_feature = _ins("Shockwave", "SEM_FOCAL", start=200, end=2000)
    sw_feature.source = "generator"
    score, findings = evaluate([sw_accent, sw_feature], _plan([0.9]))
    assert not any("high-attention" in f.detail for f in findings), (
        "accent Shockwaves must not fire rule #4 — they are short punctuation, not features")


def test_flat_flash_advisory_fires():
    """An energetic section dominated by On/Strobe/Shimmer/Twinkle/Lightning triggers advisory."""
    flat_flashes = [_ins(eff, "SEM_ALL") for eff in ("On", "Strobe", "Twinkle", "Shimmer", "On")]
    motion = [_ins("Spirals", "SEM_FOCAL")]       # 1 motion / 6 total ≈ 17% < 30%
    _, findings = evaluate(flat_flashes + motion, _plan([0.9]))
    ff = [f for f in findings if "flat-flash" in f.detail]
    assert ff and not ff[0].objective


def test_flat_flash_advisory_silent_below_threshold():
    """Sections with low flat-flash share don't trigger the advisory."""
    from xlights_orchestrator.pipeline.tuning import FLAT_FLASH_SHARE_MAX
    motion = [_ins("Spirals", "SEM_FOCAL") for _ in range(8)]
    flash = [_ins("On", "SEM_ALL")]               # 1/9 ≈ 11% < FLAT_FLASH_SHARE_MAX
    _, findings = evaluate(motion + flash, _plan([0.9]))
    assert not any("flat-flash" in f.detail for f in findings)
