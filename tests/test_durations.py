"""Tests for effect duration classes (catalog §2.1)."""
from xlights_orchestrator.pipeline.beats import normalize_durations
from xlights_orchestrator.show_plan import EffectInstruction


def _ins(effect, start=0, end=88000):
    return EffectInstruction(target="SEM_ALL", effect_type=effect, look_id="x",
                             palette_colors=["#FFD700"], start_ms=start, end_ms=end,
                             extra_settings={"k": "v"})


def _rhythm(bpm=120):
    return {"beats_ms": [], "prominent_stem": None, "onsets_by_stem": {}, "chords_ms": [], "tempo": bpm}


def test_hit_becomes_per_bar_cells():
    out = normalize_durations([_ins("Shockwave")], _rhythm(120))   # bar = 2000ms → 44 bars
    assert len(out) == 44
    assert all(o.end_ms - o.start_ms <= 1200 for o in out)         # short cells
    assert out[1].start_ms - out[0].start_ms == 2000               # one per bar
    assert out[0].palette_colors == ["#FFD700"] and out[0].extra_settings == {"k": "v"}   # preserved


def test_phrase_clamped_to_eight_bars():
    out = normalize_durations([_ins("Curtain")], _rhythm(120))
    assert len(out) == 1 and out[0].end_ms == 16000                # 8 bars × 2s


def test_sustained_and_short_hits_untouched():
    spirals = _ins("Spirals")
    short = _ins("Shockwave", 0, 1000)                              # already ≤1 bar
    out = normalize_durations([spirals, short], _rhythm(120))
    assert out == [spirals, short]


def test_cells_and_pulses_land_on_the_tracked_bar_lines():
    # beats drift off the 120 BPM clock (510 ms apart, first at 300): cells follow the beats
    beats = [300 + i * 510 for i in range(40)]
    rhythm = {"beats_ms": beats, "beats_per_bar": 4, "tempo": 120}
    spirals = _ins("Spirals", 0, 20000)
    spirals.target = "SEM_ARCHES"                                   # not a bed row: it cells
    cells = normalize_durations([spirals], rhythm)
    assert [(c.start_ms, c.end_ms) for c in cells] == [
        (0, 4380), (4380, 8460), (8460, 12540), (12540, 16620), (16620, 20000)]  # 300 = sliver
    pulses = normalize_durations([_ins("Shockwave", 0, 20000)], rhythm)
    assert [p.start_ms for p in pulses] == [0, 2340, 4380, 6420, 8460, 10500, 12540, 14580,
                                            16620, 18660]
