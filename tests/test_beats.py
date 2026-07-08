"""Tests for the beat-aware accent layer."""

from __future__ import annotations

from types import SimpleNamespace

from xlights_orchestrator.pipeline.beats import (
    MAX_ACCENTS_PER_SECTION,
    PHRASE_MIN_BARS,
    place_beat_accents,
    place_phrase_gesture,
    section_rhythm,
)
from xlights_orchestrator.show_plan import SectionPlan


def _sa(beats_s, stem_onsets):
    return SimpleNamespace(
        beats=[SimpleNamespace(time=t) for t in beats_s],
        stems=[SimpleNamespace(stem=k, onsets=v) for k, v in stem_onsets.items()],
        tempo_overall=120.0)


# -- section_rhythm -----------------------------------------------------------

def test_section_rhythm_window_and_prominent_stem():
    sa = _sa([0.5, 1.5, 2.5, 3.5], {"drums": [1.0, 2.0], "other": [0.6, 1.2], "guitar": [1.1]})
    sec = SectionPlan(start_ms=1000, end_ms=3000, target_groups=["G"], effect_family="On",
                      intensity=0.5, stem_shares={"other": 0.5, "drums": 0.3, "guitar": 0.2})
    r = section_rhythm(sa, sec)
    assert r["beats_ms"] == [1500, 2500]                  # only in-window beats
    assert r["prominent_stem"] == "drums"                 # most non-"other" onsets in-window
    assert r["onsets_by_stem"]["drums"] == [1000, 2000]   # drums onsets in-window


def test_section_rhythm_no_stems_graceful():
    sa = SimpleNamespace(beats=[SimpleNamespace(time=1.0)], stems=None, tempo_overall=None)
    sec = SectionPlan(start_ms=0, end_ms=2000, target_groups=["G"], effect_family="On", intensity=0.5)
    r = section_rhythm(sa, sec)
    assert r["beats_ms"] == [1000] and r["prominent_stem"] is None and r["onsets_by_stem"] == {}


# -- place_beat_accents -------------------------------------------------------

def _rhythm(beats, onsets=None, chords=None, melodic=None, bass=None, drum_mags=None, bpb=4):
    obs, omag = {}, {}
    if onsets:
        obs["drums"] = onsets
        omag["drums"] = drum_mags or [1.0] * len(onsets)
    if melodic:
        obs["piano"] = melodic
    if bass:
        obs["bass"] = bass
    return {"beats_ms": beats, "beats_per_bar": bpb,
            "prominent_stem": "drums" if onsets else None,
            "melodic_stem": "piano" if melodic else None,
            "onsets_by_stem": obs, "onset_mag_by_stem": omag,
            "chords_ms": chords or [], "tempo": 120}


def test_beats_contrast_color_and_meter_walk():
    sec = SectionPlan(start_ms=0, end_ms=4000, target_groups=["X"], effect_family="On", intensity=0.8,
                      palette=["Gold", "Deep Blue"], pulse_groups=["G1", "G2"])     # ring = [G1, G2]
    acc = place_beat_accents(sec, _rhythm([0, 1000, 2000, 3000]), ["G1", "G2"])
    from xlights_core.knowledge.colors import hue_spread
    accent = acc[0].palette_colors[0]                    # accents = the CONTRAST anchor
    assert hue_spread([accent, "#FFD700"]) > 90          # hue-distant from the Gold wash (LED contrast)
    by_t = {a.start_ms: a.target for a in acc}
    assert by_t[0] == "G1"                               # beat 1 (downbeat) → ring[0]
    assert by_t[1000] == "G2"                            # beat 2 → the NEXT ring group (the walk)
    assert sum(1 for a in acc if a.start_ms == 1000) == 1           # one distinct group per off-beat
    assert "C_SLIDER_Brightness" in acc[0].extra_settings           # the downbeat anchor reads bigger
    assert acc[0].end_ms == 250                                      # crisp (staccato at intensity 0.8)


def test_default_groups_are_sem_sides():
    sec = SectionPlan(start_ms=0, end_ms=2000, target_groups=["Mega"], effect_family="On", intensity=0.5)
    acc = place_beat_accents(sec, _rhythm([0, 500]), ["SEM_FOCAL", "SEM_SIDE_LEFT", "SEM_SIDE_RIGHT"])
    assert {a.target for a in acc} <= {"SEM_SIDE_LEFT", "SEM_SIDE_RIGHT"}   # defaulted to SEM_SIDE_* chase


def test_every_beat_not_downsampled():
    sec = SectionPlan(start_ms=0, end_ms=20000, target_groups=["G"], effect_family="On", intensity=0.8,
                      palette=["Gold", "Deep Blue"], pulse_groups=["04_BEAT_1", "04_BEAT_2"])
    acc = place_beat_accents(sec, _rhythm([i * 500 for i in range(32)]), ["04_BEAT_1", "04_BEAT_2"])
    assert len(acc) >= 32                                            # ~every beat (downbeats add extra), not 24


def test_density_bounded_for_huge_section():
    sec = SectionPlan(start_ms=0, end_ms=100000, target_groups=["G"], effect_family="On", intensity=1.0,
                      pulse_groups=["G"])
    acc = place_beat_accents(sec, _rhythm(list(range(0, 100000, 200))), ["G"])  # 500 beats
    assert len(acc) <= MAX_ACCENTS_PER_SECTION                       # hard upper bound (80)


def test_unplaceable_accent_falls_back_to_on():
    sec = SectionPlan(start_ms=0, end_ms=2000, target_groups=["G"], effect_family="On", intensity=0.5,
                      pulse_groups=["G"], accent_effect="Pulse")        # Pulse is NOT placeable
    acc = place_beat_accents(sec, _rhythm([0, 1000]), ["G"])
    assert acc and all(a.effect_type == "On" and a.look_id for a in acc)   # fell back, valid look


def test_energy_scaled_density():
    beats = [i * 500 for i in range(16)]
    quiet = SectionPlan(start_ms=0, end_ms=8000, target_groups=["M"], effect_family="On", intensity=0.2,
                        palette=["Gold", "Deep Blue"], pulse_groups=["04_BEAT_1", "04_BEAT_2"])
    loud = quiet.model_copy(update={"intensity": 0.9})
    nq = len(place_beat_accents(quiet, _rhythm(beats), ["04_BEAT_1", "04_BEAT_2"]))
    nl = len(place_beat_accents(loud, _rhythm(beats), ["04_BEAT_1", "04_BEAT_2"]))
    assert nq < nl                                                   # quiet sparser than loud
    assert nq > 0                                                    # downbeats still present


def test_hero_layer_follows_the_melodic_lead():
    sec = SectionPlan(start_ms=0, end_ms=8000, target_groups=["Mega"], effect_family="On", intensity=0.9,
                      palette=["Gold", "Deep Blue"], pulse_groups=["G1"])
    av = ["G1", "SEM_FOCAL"]
    # melodic (piano) onsets drive the hero; drums do NOT (drums → backbone/sparkle)
    acc = place_beat_accents(sec, _rhythm([0, 500], onsets=[120, 480], melodic=[100, 600, 1100]), av)
    hero = [a for a in acc if a.target == "SEM_FOCAL"]
    assert [a.start_ms for a in hero] == [100, 600, 1100]           # focal prop rides the melodic lead
    # no melodic stem → no hero layer (drums alone don't drive the hero)
    assert not [a for a in place_beat_accents(sec, _rhythm([0, 500], onsets=[120, 480]), av)
                if a.target == "SEM_FOCAL"]


def test_chord_driven_accent_color():
    sec = SectionPlan(start_ms=0, end_ms=8000, target_groups=["M"], effect_family="On", intensity=0.9,
                      palette=["Gold", "Deep Blue"], pulse_groups=["04_BEAT_1", "04_BEAT_2"])
    beats = [i * 500 for i in range(16)]
    chords = [(0, "Em"), (2000, "E"), (4000, "C")]
    acc = place_beat_accents(sec, _rhythm(beats, chords=chords), ["04_BEAT_1", "04_BEAT_2"])
    assert len({tuple(a.palette_colors) for a in acc}) > 1           # color steps with chords
    # no chords → single accent color (the hue-distant contrast anchor, brightened)
    one = place_beat_accents(sec, _rhythm(beats), ["04_BEAT_1", "04_BEAT_2"])
    assert len({tuple(a.palette_colors) for a in one}) == 1


def test_sparkle_rides_the_strongest_drum_hits():
    from xlights_orchestrator.pipeline.tuning import SPARKLE_TOP_N
    sec = SectionPlan(start_ms=0, end_ms=8000, target_groups=["G"], effect_family="On", intensity=0.9,
                      pulse_groups=["G"])                              # ring=[G]; sparkle=SEM_SPINNERS
    av = ["G", "SEM_SPINNERS", "SEM_SIDE_CENTER"]                     # SIDE_CENTER takes the backbeat
    drums = [100, 300, 600, 1100, 2000, 2100]
    mags = [0.9, 0.1, 0.8, 0.2, 1.0, 0.05]                            # the strong hits: 2000, 100, 600
    acc = place_beat_accents(sec, _rhythm([0, 500], onsets=drums, drum_mags=mags), av)
    sparkle = sorted(a.start_ms for a in acc if a.target == "SEM_SPINNERS")
    assert len(sparkle) <= SPARKLE_TOP_N
    assert set(sparkle) <= set(drums)                                 # sparkle only on real drum onsets
    assert {100, 600, 2000} <= set(sparkle)                           # the strongest hits are kept
    # no drums → no sparkle
    assert not [a for a in place_beat_accents(sec, _rhythm([0, 500]), av)
                if a.target == "SEM_SPINNERS"]


def test_sparkle_uses_shockwave():
    """Sparkle role emits Shockwave when a Shockwave look is available."""
    from xlights_orchestrator.pipeline.effect_meta import SHOCKWAVE_SETTINGS
    sec = SectionPlan(start_ms=0, end_ms=8000, target_groups=["G"], effect_family="On", intensity=0.9,
                      pulse_groups=["G"])
    av = ["G", "SEM_SPINNERS", "SEM_SIDE_CENTER"]
    drums = [100, 600, 2000]
    mags = [1.0, 0.9, 0.8]
    acc = place_beat_accents(sec, _rhythm([0, 500], onsets=drums, drum_mags=mags), av)
    sparkle = [a for a in acc if a.target == "SEM_SPINNERS"]
    assert sparkle, "sparkle layer must fire"
    for a in sparkle:
        assert a.effect_type == "Shockwave", f"expected Shockwave, got {a.effect_type}"
        assert a.end_ms - a.start_ms <= 600, "sparkle Shockwave must not exceed SHOCKWAVE_ACCENT_MS"
        for k in SHOCKWAVE_SETTINGS:
            assert a.extra_settings.get(k) == SHOCKWAVE_SETTINGS[k], f"missing SHOCKWAVE_SETTINGS key {k}"


def test_backbeat_uses_shockwave():
    """Backbeat role emits Shockwave on 2&4; the ring backbone stays On on the same group.

    The backbeat falls back to a ring member (no pure-backbeat group survives ring extension), so
    SEM_SNOWFLAKES appears twice per bar: On from the ring walk, Shockwave from the backbeat. The
    test checks that the Shockwave accents exist, carry SHOCKWAVE_SETTINGS, and respect the
    SHOCKWAVE_ACCENT_MS cap AND the beat interval."""
    from xlights_orchestrator.pipeline.effect_meta import SHOCKWAVE_SETTINGS
    from xlights_orchestrator.pipeline.tuning import SHOCKWAVE_ACCENT_MS, BACKBEAT_MIN_DRUM_ONSETS
    drums = list(range(0, 4000, 250))                           # enough onsets to clear BACKBEAT_MIN
    assert len(drums) >= BACKBEAT_MIN_DRUM_ONSETS
    sec = SectionPlan(start_ms=0, end_ms=4000, target_groups=["G"], effect_family="On", intensity=0.9,
                      pulse_groups=["G"])
    beats = [0, 500, 1000, 1500, 2000, 2500, 3000, 3500]       # 120 BPM, 4/4
    av = ["G", "SEM_SNOWFLAKES", "SEM_SIDE_CENTER"]
    acc = place_beat_accents(sec, _rhythm(beats, onsets=drums), av)
    sw_beats = [a for a in acc if a.target == "SEM_SNOWFLAKES" and a.effect_type == "Shockwave"]
    on_beats = [a for a in acc if a.target == "SEM_SNOWFLAKES" and a.effect_type != "Shockwave"]
    assert sw_beats, "backbeat Shockwave accents must be placed"
    assert on_beats, "backbone ring must still place On accents on the same group"
    for a in sw_beats:
        dur = a.end_ms - a.start_ms
        assert dur <= SHOCKWAVE_ACCENT_MS, "Shockwave must not exceed SHOCKWAVE_ACCENT_MS"
        assert dur <= 500 + 1, "Shockwave must not exceed the beat interval (120 BPM = 500ms)"
        for k in SHOCKWAVE_SETTINGS:
            assert a.extra_settings.get(k) == SHOCKWAVE_SETTINGS[k], f"missing key {k}"


def test_backbone_stays_on_effect():
    """The ring (backbone) role stays On/accented — it's NOT switched to Shockwave."""
    sec = SectionPlan(start_ms=0, end_ms=4000, target_groups=["G"], effect_family="On", intensity=0.9,
                      pulse_groups=["G"])
    beats = [0, 500, 1000, 1500]
    av = ["G"]
    acc = place_beat_accents(sec, _rhythm(beats), av)
    ring = [a for a in acc if a.target == "G"]
    assert ring, "backbone must produce accents"
    assert all(a.effect_type != "Shockwave" for a in ring), "backbone ring must NOT use Shockwave"


def test_legato_backbeat_skipped():
    """Legato sections suppress the backbeat layer entirely (soft energy; no 2&4 punch)."""
    from xlights_orchestrator.pipeline.tuning import BACKBEAT_MIN_DRUM_ONSETS
    drums = list(range(0, 8000, 250))
    assert len(drums) >= BACKBEAT_MIN_DRUM_ONSETS
    sec = SectionPlan(start_ms=0, end_ms=8000, target_groups=["G"], effect_family="On",
                      intensity=0.2,                            # below PHRASING_INTENSITY_THRESHOLD → legato
                      pulse_groups=["G"], phrasing="legato")
    beats = [i * 500 for i in range(16)]
    av = ["G", "SEM_SNOWFLAKES"]
    acc = place_beat_accents(sec, _rhythm(beats, onsets=drums), av)
    backbeat = [a for a in acc if a.target == "SEM_SNOWFLAKES"]
    assert not backbeat, "legato must suppress the backbeat"


# -- place_phrase_gesture -----------------------------------------------------

_PHRASE_GROUPS = ["SEM_FOCAL", "SEM_ALL", "SEM_ARCHES"]
_PHRASE_RHYTHM = {"beats_ms": [], "beats_per_bar": 4, "tempo": 120,
                  "prominent_stem": None, "melodic_stem": None,
                  "onsets_by_stem": {}, "onset_mag_by_stem": {}, "chords_ms": []}


def _phrase_sec(bars: int, intensity: float = 0.8) -> SectionPlan:
    # 120bpm 4/4 → bar = 2000ms
    end = bars * 2000
    return SectionPlan(start_ms=0, end_ms=end, target_groups=_PHRASE_GROUPS,
                       effect_family="On", intensity=intensity, palette=["Gold", "Blue"])


def test_phrase_gesture_emits_one_instruction_four_bars():
    """Full-treatment 8-bar section → exactly one phrase instruction spanning ~4 bars, starting
    at the 2nd bar boundary (bar_ms=2000ms at 120bpm)."""
    pg = place_phrase_gesture(_phrase_sec(8), _PHRASE_RHYTHM, 0.8, _PHRASE_GROUPS, seed=0)
    assert pg is not None
    assert not pg.source                 # source is tagged by the caller (realize_section)
    bar_ms = 2000.0
    assert pg.start_ms == int(bar_ms)    # enters at the 2nd bar
    span = pg.end_ms - pg.start_ms
    assert abs(span - 4 * bar_ms) < 100  # ~4 bars (within rounding)
    assert pg.effect_type in ("Morph", "Curtain", "Fill")


def test_phrase_gesture_same_label_same_effect():
    """Two sections with the same label (same seed + intensity) produce the same effect type."""
    from xlights_orchestrator.pipeline.weave import label_seed
    seed = label_seed("chorus")
    pg1 = place_phrase_gesture(_phrase_sec(8, intensity=0.8), _PHRASE_RHYTHM, 0.8, _PHRASE_GROUPS, seed=seed)
    pg2 = place_phrase_gesture(_phrase_sec(12, intensity=0.8), _PHRASE_RHYTHM, 0.8, _PHRASE_GROUPS, seed=seed)
    assert pg1 is not None and pg2 is not None
    assert pg1.effect_type == pg2.effect_type


def test_phrase_gesture_skips_quiet_section():
    """A section below PHRASE_MIN_INTENSITY (0.4) gets no gesture."""
    pg = place_phrase_gesture(_phrase_sec(8), _PHRASE_RHYTHM, 0.3, _PHRASE_GROUPS, seed=0)
    assert pg is None


def test_phrase_gesture_skips_short_section():
    """Sections shorter than PHRASE_MIN_BARS (6) get no gesture (4 bars is too short)."""
    pg = place_phrase_gesture(_phrase_sec(4), _PHRASE_RHYTHM, 0.8, _PHRASE_GROUPS, seed=0)
    assert pg is None
    pg6 = place_phrase_gesture(_phrase_sec(PHRASE_MIN_BARS), _PHRASE_RHYTHM, 0.8, _PHRASE_GROUPS, seed=0)
    assert pg6 is not None


def test_phrase_gesture_high_energy_steps_over_curtain_to_morph():
    """At peak intensity (sec_band=5), Curtain and Fill (band 2-3) are ≥2 away; Morph (2-4) passes.

    seed=1 starts the rotation at Curtain; the step-over logic must skip Curtain→Fill→Morph."""
    pg = place_phrase_gesture(_phrase_sec(8, intensity=1.0), _PHRASE_RHYTHM, 1.0,
                              _PHRASE_GROUPS, seed=1)
    assert pg is not None
    assert pg.effect_type == "Morph", f"expected Morph (step-over from Curtain), got {pg.effect_type}"
