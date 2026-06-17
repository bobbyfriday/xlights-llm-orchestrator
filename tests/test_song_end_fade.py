"""Song-end envelope fade: lights stop and fade WITH the music, not past it to the file end."""

from __future__ import annotations

from xlights_core.audio import song_tail_envelope
from xlights_core.audio.envelope import MAX_TAIL_FADE_S, MIN_TAIL_FADE_S
from xlights_core.audio.schema import EnergyPoint

from xlights_orchestrator.pipeline.generate import apply_song_end_fade
from xlights_orchestrator.pipeline.phrasing import tail_fade_settings
from xlights_orchestrator.show_plan import EffectInstruction


def _arc(pairs):
    return [EnergyPoint(time=t, rms=r) for t, r in pairs]


def _eff(start_ms, end_ms, effect_type="SingleStrand", **extra):
    return EffectInstruction(target="G1", effect_type=effect_type, look_id="x",
                             start_ms=start_ms, end_ms=end_ms, extra_settings=dict(extra))


# -- song_tail_envelope ------------------------------------------------------

def _fine(value_at, end_s, step=0.1):
    return _arc([(round(i * step, 3), value_at(round(i * step, 3)))
                 for i in range(int(end_s / step) + 1)])


def test_flat_to_end_no_trim():
    arc = _fine(lambda t: 1.0, 30.0)                    # constant energy through the file end
    fade_start, music_end = song_tail_envelope(arc, 30.0)
    assert music_end == 30.0                            # never goes quiet → no trim
    assert abs((music_end - fade_start) - MIN_TAIL_FADE_S) < 0.15   # short ease-off at the very end


def test_silent_tail_trims_to_music_end():
    # loud to 25s, then effectively silent out to a 35s file
    arc = _arc([(float(t), 1.0) for t in range(0, 26)] + [(float(t), 0.0) for t in range(26, 36)])
    fade_start, music_end = song_tail_envelope(arc, 35.0)
    assert 25.0 <= music_end <= 27.0                    # lights stop where the music goes silent
    assert music_end < 35.0
    assert fade_start < music_end


def test_gradual_fadeout_long_fade():
    # loud until 20s, then a smooth linear decline to silence by 28s (file ends 28s)
    loud = [(float(t), 1.0) for t in range(0, 21)]
    decline = [(20.0 + i * 0.5, max(0.0, 1.0 - i * 0.0625)) for i in range(1, 17)]  # ->0 by 28s
    fade_start, music_end = song_tail_envelope(_arc(loud + decline), 28.0)
    assert music_end <= 28.0
    fade_len = music_end - fade_start
    assert fade_len > MIN_TAIL_FADE_S                   # a real, longer fade tracks the decline
    assert fade_len <= MAX_TAIL_FADE_S + 1e-6           # bounded


def test_abrupt_ending_short_fade():
    arc = _fine(lambda t: 1.0, 20.0)                      # loud right up to the 20s file end
    fade_start, music_end = song_tail_envelope(arc, 20.0)
    assert music_end == 20.0
    assert abs((music_end - fade_start) - MIN_TAIL_FADE_S) < 0.15   # floored to the MIN fade


def test_empty_arc_degrades_to_short_tail_fade():
    fade_start, music_end = song_tail_envelope([], 12.0)
    assert music_end == 12.0
    assert abs((music_end - fade_start) - MIN_TAIL_FADE_S) < 1e-6


# -- tail_fade_settings ------------------------------------------------------

def test_tail_fade_line_effect_is_opacity_fade_only():
    keys = tail_fade_settings("SingleStrand", 2.0)
    assert keys == {"T_TEXTCTRL_Fadeout": "2"}
    assert "T_TEXTCTRL_Fadein" not in keys              # song is ending — nothing fades IN


def test_tail_fade_wash_adds_dissolve_out():
    keys = tail_fade_settings("Color Wash", 1.5)
    assert keys["T_TEXTCTRL_Fadeout"] == "1.5"
    assert keys["T_CHOICE_Out_Transition_Type"] == "Dissolve"


# -- apply_song_end_fade -----------------------------------------------------

def test_trims_effect_past_music_end():
    effs = apply_song_end_fade([_eff(0, 30000)], fade_start_ms=24000, music_end_ms=25000)
    assert len(effs) == 1
    assert effs[0].end_ms == 25000                      # clamped to the music's end


def test_drops_effect_entirely_in_silent_tail():
    effs = apply_song_end_fade([_eff(26000, 30000)], fade_start_ms=24000, music_end_ms=25000)
    assert effs == []


def test_effect_before_fade_region_untouched():
    effs = apply_song_end_fade([_eff(0, 10000)], fade_start_ms=24000, music_end_ms=25000)
    assert "T_TEXTCTRL_Fadeout" not in effs[0].extra_settings


def test_effect_in_region_gets_scaled_fadeout():
    # a section-spanning effect to the file end; region is the last 1s before music_end
    effs = apply_song_end_fade([_eff(0, 30000)], fade_start_ms=24000, music_end_ms=25000)
    assert effs[0].extra_settings["T_TEXTCTRL_Fadeout"] == "1"   # 24000..25000 = 1.0s


def test_keeps_longer_existing_fadeout():
    effs = apply_song_end_fade([_eff(0, 30000, **{"T_TEXTCTRL_Fadeout": "3"})],
                               fade_start_ms=24000, music_end_ms=25000)
    assert effs[0].extra_settings["T_TEXTCTRL_Fadeout"] == "3"   # existing longer fade wins


def test_final_section_floor_prevents_collapse():
    # music_end below the final section start is lifted so the section isn't wiped out
    effs = apply_song_end_fade([_eff(28000, 30000)], fade_start_ms=20000, music_end_ms=10000,
                               final_section_start_ms=28000)
    assert len(effs) == 1
    assert effs[0].end_ms > effs[0].start_ms


def test_idempotent():
    once = apply_song_end_fade([_eff(0, 30000)], fade_start_ms=24000, music_end_ms=25000)
    twice = apply_song_end_fade(once, fade_start_ms=24000, music_end_ms=25000)
    assert [e.model_dump() for e in once] == [e.model_dump() for e in twice]
