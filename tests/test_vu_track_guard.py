"""VU Meter rows reach xLights bound to a timing track finalize writes, and no placed effect
carries a community sequencer's editor lock."""

from __future__ import annotations

import asyncio

from xlights_core.editing import DROP_KEYS, place_preset
from xlights_core.knowledge.preset_library import get_library
from xlights_orchestrator.effect_emitter import apply_instructions
from xlights_orchestrator.pipeline.beats import VU_TIMING_TRACK_KEY
from xlights_orchestrator.show_plan import EffectInstruction


class _Client:
    def __init__(self):
        self.calls = []
    async def get_models(self): return ["G"]
    async def close_sequence(self, **kw): pass
    async def new_sequence(self, **kw): pass
    async def render_all(self, **kw): pass
    async def save_sequence(self, *a, **kw): pass
    async def add_effect(self, target, effect_type, settings, palette="", **kw):
        self.calls.append((effect_type, settings))
        return True


def _row(effect_type, look_id, **extra):
    return EffectInstruction(target="G", effect_type=effect_type, look_id=look_id,
                             start_ms=0, end_ms=4000, extra_settings=extra)


def test_emitter_binds_vu_meter_to_beats_unless_the_row_names_one_of_ours(monkeypatch):
    seen = []
    async def fake_place(client, target, effect_type, look_id, **kw):
        seen.append(kw["extra_settings"].get(VU_TIMING_TRACK_KEY)
                    or kw["extra_settings"].get("E_CHOICE_FIRETIMINGTRACK"))
        return "ok"
    monkeypatch.setattr("xlights_orchestrator.effect_emitter.place_preset", fake_place)
    rows = [_row("VU Meter", "VU Meter#68"),                                   # frozen 'Beat Count'
            _row("VU Meter", "VU Meter#45", **{VU_TIMING_TRACK_KEY: "Onsets"}),  # a stack's choice
            _row("VU Meter", "VU Meter#45", **{VU_TIMING_TRACK_KEY: "Drums"}),   # not ours
            _row("VU Meter", "VU Meter#45", **{VU_TIMING_TRACK_KEY: "Onsets (drums)"}),  # per-stem
            _row("Fireworks", "Fireworks#1"),                                  # timed bursts
            _row("Bars", "Bars#1")]
    asyncio.run(apply_instructions(_Client(), rows, duration_secs=10, settle_secs=0))
    assert seen == ["Beats", "Onsets", "Beats", "Onsets (drums)", "Beats", None]


def test_place_preset_strips_the_sequencers_editor_lock():
    lib = get_library()
    locked = next(lk for t in lib.list_effect_types() for lk in lib.get_looks(t)
                  if "X_Effect_Locked" in lk.frozen_base)
    assert "X_Effect_Locked" in DROP_KEYS
    c = _Client()
    asyncio.run(place_preset(c, "G", locked.effect_type, locked.look_id, start_ms=0, end_ms=4000,
                             known_targets={"G"}))
    (_, settings), = c.calls
    assert "X_Effect_Locked" not in settings
