"""The look picker: ranked by corpus count, rotated per seed, never a designed (blend/mask) look."""

from __future__ import annotations

from xlights_core.knowledge import get_library
from xlights_orchestrator.pipeline import catalog

lib = get_library()


def test_ranked_is_by_count_descending():
    ids = catalog.ranked_look_ids("Spirals")
    counts = [lib.get_look("Spirals", i).count for i in ids]
    assert counts == sorted(counts, reverse=True)
    assert ids[0] != "Spirals#0", "the old 'first look in corpus order' default is gone"


def test_candidate_look_ids_is_the_ranked_prefix():
    assert catalog.candidate_look_ids("Spirals", limit=3) == list(catalog.ranked_look_ids("Spirals")[:3])


def test_pick_pool_excludes_designed_looks():
    for et in ("Spirals", "Shockwave", "Bars", "Ripple"):
        for lid in catalog.pick_pool(et):
            lk = lib.get_look(et, lid)
            assert lk.frozen_base.get("T_CHOICE_LayerMethod", "Normal") == "Normal", (et, lid)
            assert "B_CUSTOM_SubBuffer" not in lk.frozen_base, (et, lid)
            for k in lk.knobs:
                if k.key == "T_CHOICE_LayerMethod":
                    assert (k.default or "Normal") == "Normal", (et, lid)
    # the most-used Spirals look bakes a Brightness blend in as its knob default → not a default pick
    assert "Spirals#99" not in catalog.pick_pool("Spirals")
    assert len(catalog.pick_pool("Spirals")) == catalog.PICK_POOL


def test_pick_look_rotates_and_is_deterministic():
    pool = catalog.pick_pool("Spirals")
    seen = {catalog.pick_look("Spirals", s) for s in range(len(pool))}
    assert seen == set(pool)
    assert catalog.pick_look("Spirals", 7) == catalog.pick_look("Spirals", 7 + len(pool))
    assert catalog.pick_look("NoSuchEffect", 3) == ""


def test_look_ids_by_type_covers_every_placeable_type():
    by = catalog.look_ids_by_type()
    assert set(by) == set(catalog.placeable_effect_types())
    assert all(v for v in by.values())


def test_on_pool_never_pulses_or_shimmers():
    # On#9 (Cycles 2) and On#27 (Shimmer) are designed looks: a default bed must hold steady.
    for lid in catalog.pick_pool("On"):
        lk = lib.get_look("On", lid)
        assert lk.frozen_base.get("E_TEXTCTRL_On_Cycles", "1") in {"1", "1.0", "1.00"}, lid
        assert lk.frozen_base.get("E_CHECKBOX_On_Shimmer", "0") == "0", lid
        for k in lk.knobs:
            if k.key == "E_TEXTCTRL_On_Cycles":
                assert (k.default or "1") in {"1", "1.0", "1.00"}, lid
            if k.key == "E_CHECKBOX_On_Shimmer":
                assert (k.default or "0") == "0", lid
    assert "On#9" not in catalog.pick_pool("On")


def test_pool_never_bakes_a_buffer_transform():
    # Danger Zone's star pops are all `Rotate CC 90` for THEIR prop; a default pick stays upright.
    for et in catalog.placeable_effect_types():
        for lid in catalog.pick_pool(et):
            assert lib.get_look(et, lid).frozen_base.get("B_CHOICE_BufferTransform", "None") == "None", lid
    assert "On#27" not in catalog.pick_pool("On")


def test_pool_skips_compositing_nodes_and_designed_exits_but_keeps_canvas_overlays():
    # Off#15 is an Off with Canvas on (a blend node in Magic's stack); Off#10 wipes out.
    assert "Off#15" not in catalog.pick_pool("Off")
    assert "Off#10" not in catalog.pick_pool("Off")
    # Every Warp / Kaleidoscope look needs Canvas on: the key is uninformative there, so the
    # overlays still have a pool, and the Brightness-blend Kaleidoscope stays out of it.
    assert len(catalog.pick_pool("Warp")) == catalog.PICK_POOL
    assert catalog.pick_pool("Kaleidoscope")
    assert "Kaleidoscope#5" not in catalog.pick_pool("Kaleidoscope")
