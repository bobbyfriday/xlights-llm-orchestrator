"""Big-hit whole-display rings, and the emitter's logical → xLights layer flip."""

from __future__ import annotations

import asyncio

from xlights_orchestrator.effect_emitter import _logical_layers, _xlights_layers, apply_instructions
from xlights_orchestrator.pipeline.hits import big_hit_times, place_big_hit_rings, ring_duration_ms
from xlights_orchestrator.pipeline.semantic_groups import FULL_DISPLAY
from xlights_orchestrator.pipeline.tuning import BIG_HIT_MIN_SPACING_BARS, BIG_HIT_RING
from xlights_orchestrator.show_plan import EffectInstruction, SectionPlan

BEAT = 500                                             # 120 BPM
BEATS = [t * BEAT for t in range(0, 64)]               # 32 s
SEC = SectionPlan(start_ms=0, end_ms=32000, label="chorus", target_groups=["SEM_FOCAL"],
                  effect_family="Spirals", intensity=0.9, palette=["red", "white"])


def _rhythm(onsets: list[tuple[int, float]]) -> dict:
    return {"beats_ms": BEATS, "beats_per_bar": 4, "tempo": 120.0,
            "onsets_by_stem": {"drums": [t for t, _ in onsets]},
            "onset_mag_by_stem": {"drums": [m for _, m in onsets]}}


def test_big_hits_pick_the_strongest_onsets_spaced_two_bars_apart_and_snap_to_beats():
    # strong hits at 1.0s (snaps to 1.0), 1.5s (too close), 9.06s (snaps to 9.0), 17.3s (no snap)
    r = _rhythm([(1000, 0.95), (1500, 0.9), (9060, 0.8), (17300, 0.75), (25000, 0.5)])
    times = big_hit_times(SEC, r, 0.9)
    assert times == [1000, 9000, 17300]
    spacing = BIG_HIT_MIN_SPACING_BARS * 4 * BEAT
    assert all(b - a >= spacing for a, b in zip(times, times[1:]))
    assert big_hit_times(SEC, r, 0.4) == []                       # the energy gate
    assert big_hit_times(SEC, {"beats_ms": BEATS, "beats_per_bar": 4}, 0.9) == []   # no drum onsets


def test_ring_rows_cross_the_whole_display_slowly_and_punch_through():
    r = _rhythm([(1000, 0.95), (9000, 0.9)])
    rows = place_big_hit_rings(SEC, r, 0.9, [FULL_DISPLAY, "SEM_FOCAL"])
    assert len(rows) == 2 and all(x.target == FULL_DISPLAY and x.on_top and x.source == "hits" for x in rows)
    assert rows[0].start_ms == 1000 and rows[0].end_ms == 1000 + ring_duration_ms(r) == 2000   # 2 beats
    assert all(x.render_style == "Per Preview" and x.effect_type == "Shockwave" for x in rows)
    assert all(x.extra_settings["T_CHOICE_LayerMethod"] == "Max" for x in rows)
    for k, v in BIG_HIT_RING.items():
        assert rows[0].extra_settings[k] == v
    assert int(rows[0].extra_settings["E_SLIDER_Shockwave_End_Radius"]) <= 130      # stays in frame
    assert place_big_hit_rings(SEC, r, 0.9, ["SEM_FOCAL"]) == []                     # no whole display


def test_ring_duration_is_bounded_for_slow_and_fast_songs():
    assert ring_duration_ms({"beats_ms": [0, 2000, 4000]}) == 2000        # 30 BPM → capped
    assert ring_duration_ms({"beats_ms": [0, 200, 400]}) == 900           # 300 BPM → floored


# -- the emitter's layer flip -----------------------------------------------------------------

def _row(target, start, end, *, layer=0, on_top=False, look="x"):
    return EffectInstruction(target=target, effect_type="On", look_id=look, layer=layer,
                             start_ms=start, end_ms=end, on_top=on_top)


def test_logical_layers_then_xlights_indices_from_the_top():
    rows = [_row("G", 0, 4000),                  # bed → logical 0
            _row("G", 0, 4000),                  # feature → logical 1
            _row("G", 1000, 1500, on_top=True),  # accent above everything → logical 2
            _row("G", 5000, 6000),               # alone later → logical 0
            _row("H", 0, 1000)]                  # another target → logical 0
    logical = _logical_layers(rows)
    assert logical == [0, 1, 2, 0, 0]
    xl = _xlights_layers(rows, logical)
    assert xl == [2, 1, 0, 2, 0]     # G is three deep: bed at index 2 (bottom), accent at 0 (top)


def test_apply_places_the_punch_through_accent_on_index_zero(monkeypatch):
    calls = []
    async def fake_place(client, target, effect_type, look_id, **kw):
        calls.append((look_id, kw.get("layer")))
        return "ok"
    monkeypatch.setattr("xlights_orchestrator.effect_emitter.place_preset", fake_place)

    class Client:
        rendered = False
        async def get_models(self): return ["G"]
        async def close_sequence(self, **kw): pass
        async def new_sequence(self, **kw): pass
        async def render_all(self, **kw): self.rendered = True
        async def save_sequence(self, *a, **kw): pass
    rows = [_row("G", 0, 4000, look="bed"), _row("G", 0, 4000, look="feature"),
            _row("G", 1000, 1500, on_top=True, look="accent")]
    rep = asyncio.run(apply_instructions(Client(), rows, duration_secs=10, settle_secs=0))
    assert dict(calls) == {"bed": 2, "feature": 1, "accent": 0}
    assert [p["layer"] for p in rep["placed"]] == [2, 1, 0]
