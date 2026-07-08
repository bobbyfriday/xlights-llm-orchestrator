"""Tests for the cell weaver: recipe expansion, density bounds, blends/curves/transitions,
fallback, and the carrier/beat-accent dedup."""

from __future__ import annotations

from xlights_core.knowledge.value_curves import motion_curve_setting

from xlights_orchestrator.pipeline.beats import place_beat_accents
from xlights_orchestrator.pipeline.weave import (
    CARRIER_ROTATION,
    carrier_covers,
    cell_budget,
    counter_rotate_stacks,
    diversify_carrier,
    expand_weave,
    fallback_weave,
    section_carrier,
)
from xlights_orchestrator.qa.rules import evaluate as rules_evaluate
from xlights_orchestrator.show_plan import CellRecipe, SectionPlan, SectionWeave

GROUPS = ["SEM_ARCHES", "SEM_CANES", "SEM_MINITREES", "SEM_YARD", "SEM_BAND_GROUND",
          "SEM_SIDE_LEFT", "SEM_SIDE_CENTER", "SEM_SIDE_RIGHT", "SEM_FOCAL"]


def _sec(start=0, end=8000, intensity=0.8, **kw):
    kw.setdefault("target_groups", ["SEM_YARD", "SEM_ARCHES"])
    kw.setdefault("effect_family", "On")
    kw.setdefault("palette", ["Gold", "Deep Blue"])
    return SectionPlan(start_ms=start, end_ms=end, intensity=intensity, **kw)


def _rhythm(n_beats=16, step=500):
    return {"beats_ms": [i * step for i in range(n_beats)], "prominent_stem": "drums",
            "onsets_by_stem": {}, "chords_ms": [], "tempo": 120}


def _carrier(**kw):
    kw.setdefault("effect_type", "SingleStrand")
    kw.setdefault("role", "carrier")
    kw.setdefault("groups", ["SEM_ARCHES", "SEM_CANES"])
    kw.setdefault("cell_beats", 1)
    return CellRecipe(**kw)


# -- expansion ----------------------------------------------------------------

def test_cells_snap_to_beats_and_chase_rotates():
    w = SectionWeave(cells=[_carrier()])
    out = expand_weave(_sec(), w, _rhythm(8), 0.8, GROUPS)
    assert [c.start_ms for c in out] == [0, 500, 1000, 1500, 2000, 2500, 3000, 3500]
    assert [c.target for c in out[:4]] == ["SEM_ARCHES", "SEM_CANES", "SEM_ARCHES", "SEM_CANES"]
    assert all(c.effect_type == "SingleStrand" for c in out)
    assert out[0].end_ms == 500                       # cell = one beat
    assert out[-1].end_ms == 8000                     # trailing partial merges to section end


def test_cell_beats_lengthens_cells():
    w = SectionWeave(cells=[_carrier(cell_beats=4)])
    out = expand_weave(_sec(), w, _rhythm(16), 0.8, GROUPS)
    assert [c.start_ms for c in out] == [0, 2000, 4000, 6000]
    assert out[0].end_ms == 2000


def test_pingpong_reflects_and_sparse_breathes():
    w = SectionWeave(cells=[_carrier(groups=["A", "B", "C"], alternation="pingpong")])
    out = expand_weave(_sec(), w, _rhythm(8), 0.8, GROUPS + ["A", "B", "C"])
    assert [c.target for c in out[:6]] == ["A", "B", "C", "B", "A", "B"]
    w2 = SectionWeave(cells=[_carrier(alternation="sparse")])
    out2 = expand_weave(_sec(), w2, _rhythm(8), 0.8, GROUPS)
    assert [c.start_ms for c in out2] == [0, 1000, 2000, 3000]      # every other slot


def test_invalid_groups_and_effects_degrade():
    w = SectionWeave(cells=[
        _carrier(groups=["NOPE"]),                       # carrier falls back to the rhythm pool
        CellRecipe(effect_type="NotAnEffect", role="texture", groups=["SEM_YARD"]),  # dropped
        CellRecipe(effect_type="Spirals", role="texture", groups=["NOPE"]),          # dropped
    ])
    out = expand_weave(_sec(), w, _rhythm(8), 0.8, GROUPS)
    assert out and all(c.effect_type == "SingleStrand" for c in out)
    assert {c.target for c in out} <= {"SEM_ARCHES", "SEM_CANES", "SEM_MINITREES"}


# -- density ------------------------------------------------------------------

def test_budget_scales_with_intensity():
    assert cell_budget(1.0, 60000) > 2.5 * cell_budget(0.2, 60000)
    long_sec = _sec(end=60000)
    w = SectionWeave(cells=[_carrier(groups=["A", "B"], alternation="all"),
                            CellRecipe(effect_type="Spirals", role="texture",
                                       groups=["A", "B"], alternation="all")])
    rhythm = {"beats_ms": [i * 100 for i in range(600)], "prominent_stem": None,
              "onsets_by_stem": {}, "chords_ms": [], "tempo": 120}
    quiet = expand_weave(long_sec, w, rhythm, 0.2, ["A", "B"])
    peak = expand_weave(long_sec, w, rhythm, 1.0, ["A", "B"])
    assert len(quiet) <= cell_budget(0.2, 60000)
    assert len(peak) <= cell_budget(1.0, 60000)
    assert len(peak) > 2 * len(quiet)


# -- settings: blends / curves / transitions ----------------------------------

def test_blend_only_over_a_base():
    base_free = SectionWeave(cells=[CellRecipe(effect_type="Spirals", role="texture",
                                               groups=["SEM_YARD"], blend="Max")])
    out = expand_weave(_sec(), base_free, _rhythm(8), 0.8, GROUPS)
    assert all("T_CHOICE_LayerMethod" not in c.extra_settings for c in out)  # nothing under it

    layered = SectionWeave(cells=[
        _carrier(groups=["SEM_YARD"]),
        CellRecipe(effect_type="Spirals", role="texture", groups=["SEM_YARD"], blend="Brightness"),
    ])
    out2 = expand_weave(_sec(), layered, _rhythm(8), 0.8, GROUPS)
    spirals = [c for c in out2 if c.effect_type == "Spirals"]
    carriers = [c for c in out2 if c.effect_type == "SingleStrand"]
    assert spirals and all(c.extra_settings.get("T_CHOICE_LayerMethod") == "Brightness"
                           for c in spirals)               # explicit recipe blend honored
    assert all("T_CHOICE_LayerMethod" not in c.extra_settings for c in carriers)
    # base placed FIRST so the emitter stacks it on layer 0 under the blend
    assert out2.index(carriers[0]) < out2.index(spirals[0])


def test_cells_over_washes_default_to_max():
    """A top-layer cell's black background occludes the wash below it under Normal blend (the
    live 'mostly dark' failure) — cells over based targets default to Max."""
    w = SectionWeave(cells=[_carrier(groups=["SEM_YARD"]),
                            CellRecipe(effect_type="Spirals", role="texture", groups=["SEM_YARD"])])
    out = expand_weave(_sec(), w, _rhythm(8), 0.8, GROUPS, based_targets={"SEM_YARD"})
    assert out and all(c.extra_settings.get("T_CHOICE_LayerMethod") == "Max" for c in out)
    # ...but stay Normal where there is genuinely nothing underneath
    out2 = expand_weave(_sec(), w, _rhythm(8), 0.8, GROUPS)
    carriers = [c for c in out2 if c.effect_type == "SingleStrand"]
    assert all("T_CHOICE_LayerMethod" not in c.extra_settings for c in carriers)


def test_motion_curve_and_transition_settings():
    w = SectionWeave(cells=[_carrier(effect_type="Spirals", motion_curve="rotation",
                                     transition="Wipe", groups=["SEM_YARD"])])
    out = expand_weave(_sec(), w, _rhythm(8), 0.8, GROUPS)
    s = out[0].extra_settings
    vc = s.get("E_VALUECURVE_Spirals_Rotation", "")
    assert "Type=Ramp" in vc and "Min=-300.00|Max=300.00" in vc and "RV=TRUE" in vc
    assert s["T_CHOICE_In_Transition_Type"] == "Wipe" and s["T_CHOICE_Out_Transition_Type"] == "Wipe"


def test_unknown_motion_curve_no_ops():
    assert motion_curve_setting("On", "rotation") == {}
    assert motion_curve_setting("Spirals", "nope") == {}
    w = SectionWeave(cells=[_carrier(motion_curve="radius")])     # SingleStrand has no radius
    out = expand_weave(_sec(), w, _rhythm(8), 0.8, GROUPS)
    assert out and all(not any(k.startswith("E_VALUECURVE_") for k in c.extra_settings)
                       for c in out)


def test_cells_render_per_model_and_pop_with_energy():
    """Cells default to per-model rendering (Per Preview spreads a 0.5s cell over the whole
    yard buffer → near-invisible) and carry intensity-scaled brightness."""
    out = expand_weave(_sec(), SectionWeave(cells=[_carrier()]), _rhythm(8), 1.0, GROUPS)
    assert all(c.render_style == "Per Model Default" for c in out)
    assert all(c.extra_settings.get("C_SLIDER_Brightness") == "180" for c in out)


def test_effect_name_canonicalized_and_bed_capability():
    from xlights_orchestrator.pipeline.weave import canon_effect_type
    assert canon_effect_type("Single Strand") == "SingleStrand"
    assert canon_effect_type("SingleStrand") == "SingleStrand"
    # a non-bed-capable "bed" demotes to texture (it weaves; no 88s Pinwheel beds)
    w = SectionWeave(cells=[_carrier(),
                            CellRecipe(effect_type="Pinwheel", role="bed", groups=["SEM_YARD"])])
    out = expand_weave(_sec(), w, _rhythm(8), 0.8, GROUPS)
    pw = [c for c in out if c.effect_type == "Pinwheel"]
    assert pw and all(c.end_ms - c.start_ms <= 1000 for c in pw[:-1])   # cells, not a span
    assert pw[-1].end_ms == 8000                                # trailing partial merges to end


def test_bed_role_spans_section_dim():
    w = SectionWeave(cells=[_carrier(),
                            CellRecipe(effect_type="On", role="bed", groups=["SEM_BAND_GROUND"])])
    out = expand_weave(_sec(), w, _rhythm(8), 0.8, GROUPS)
    beds = [c for c in out if c.target == "SEM_BAND_GROUND"]
    assert len(beds) == 1 and beds[0].start_ms == 0 and beds[0].end_ms == 8000
    assert beds[0].extra_settings["C_SLIDER_Brightness"] == "60"


# -- fallback + dedup ---------------------------------------------------------

def test_fallback_weave_carries_the_pool():
    sec = _sec(effect_types=["Spirals", "On"])
    w = fallback_weave(sec, GROUPS)
    roles = [c.role for c in w.cells]
    assert roles[0] == "carrier" and w.cells[0].effect_type == "SingleStrand"
    assert set(w.cells[0].groups) & {"SEM_ARCHES", "SEM_CANES", "SEM_MINITREES"}
    assert any(c.role == "texture" and c.effect_type == "Spirals" for c in w.cells)


def test_fallback_weave_ripple_when_no_cellable_in_section():
    # "On" is not cellable — fallback should use Ripple rather than omitting the texture layer.
    sec = _sec(effect_types=["On"])
    w = fallback_weave(sec, GROUPS)
    tex = [c for c in w.cells if c.role == "texture"]
    assert len(tex) == 1 and tex[0].effect_type == "Ripple"


def test_fallback_weave_no_texture_when_no_tex_groups():
    # Only ACCENT_GROUPS in target_groups → tex_groups empty → carrier only, no texture recipe.
    sec = _sec(target_groups=["SEM_SNOWFLAKES", "SEM_SPINNERS"])
    w = fallback_weave(sec, GROUPS + ["SEM_SNOWFLAKES", "SEM_SPINNERS"])
    assert all(c.role == "carrier" for c in w.cells)


def test_carrier_covers_requires_pool_intersection():
    sec = _sec()
    on_pool = SectionWeave(cells=[_carrier()])
    off_pool = SectionWeave(cells=[_carrier(groups=["SEM_YARD"])])   # not the rhythm pool
    assert carrier_covers(on_pool, sec, GROUPS) is True
    assert carrier_covers(off_pool, sec, GROUPS) is False
    assert carrier_covers(None, sec, GROUPS) is False


def test_beat_accents_defer_to_carrier():
    sec = _sec(palette=["Gold"])
    drums = [100, 400, 700, 1100, 1500, 2000]
    rhythm = {"beats_ms": [0, 500, 1000, 1500, 2000, 2500, 3000, 3500], "beats_per_bar": 4,
              "prominent_stem": "drums", "melodic_stem": None,
              "onsets_by_stem": {"drums": drums}, "onset_mag_by_stem": {"drums": [1.0] * len(drums)},
              "chords_ms": [], "tempo": 120}
    full = place_beat_accents(sec, rhythm, GROUPS)
    deferred = place_beat_accents(sec, rhythm, GROUPS, carrier_covers=True)
    pool = {"SEM_ARCHES", "SEM_CANES", "SEM_MINITREES"}
    assert any(a.target in pool for a in full)                       # the metric backbone exists normally
    assert not any(a.target in pool for a in deferred)               # carrier owns the backbone (deferred)
    sparkle = {"SEM_SNOWFLAKES", "SEM_SPINNERS"}
    assert {a.target for a in place_beat_accents(sec, rhythm, GROUPS + list(sparkle),
                                                 carrier_covers=True)} & sparkle   # overlay still places


# -- QA advisory --------------------------------------------------------------

def test_motion_share_advisory_is_not_objective():
    from xlights_orchestrator.show_plan import EffectInstruction, ShowPlan
    plan = ShowPlan(sections=[_sec(intensity=0.9)])
    static = [EffectInstruction(target="SEM_YARD", effect_type="On", look_id="x",
                                start_ms=0, end_ms=1000, section_index=0) for _ in range(10)]
    score, findings = rules_evaluate(static, plan)
    advisories = [f for f in findings if "motion-effect share" in f.detail]
    assert advisories and advisories[0].section_index == 0 and not advisories[0].objective
    assert score == 100                                              # advisory never gates

    woven = static[:4] + [EffectInstruction(target="SEM_YARD", effect_type="SingleStrand",
                                            look_id="x", start_ms=i * 100, end_ms=i * 100 + 100,
                                            section_index=0) for i in range(8)]
    _, findings2 = rules_evaluate(woven, plan)
    assert not [f for f in findings2 if "motion-effect share" in f.detail]


def test_cellable_long_placement_chopped():
    from xlights_orchestrator.pipeline.beats import normalize_durations
    from xlights_orchestrator.show_plan import EffectInstruction
    rhythm = {"beats_ms": [], "tempo": 120.0}                        # bar = 2000ms, cell = 4000ms
    long_sp = EffectInstruction(target="SEM_ARCHES", effect_type="Spirals", look_id="x",
                                start_ms=0, end_ms=20000)
    out = normalize_durations([long_sp], rhythm)
    assert len(out) == 5 and all(o.end_ms - o.start_ms == 4000 for o in out)
    assert out[0].start_ms == 0 and out[-1].end_ms == 20000          # contiguous, full span
    bed = EffectInstruction(target="SEM_BAND_GROUND", effect_type="Spirals", look_id="x",
                            start_ms=0, end_ms=20000)
    assert normalize_durations([bed], rhythm) == [bed]               # bed rows may run long
    sub = EffectInstruction(target="SEM_ALL_LESS_FOCAL", effect_type="Bars", look_id="x",
                            start_ms=0, end_ms=20000)
    assert len(normalize_durations([sub], rhythm)) == 5              # subtractive ensembles WEAVE


# -- carrier rotation (variety) -----------------------------------------------

def test_section_carrier_rotates_across_sections():
    seen = [section_carrier(i) for i in range(len(CARRIER_ROTATION))]
    assert seen == list(CARRIER_ROTATION)            # cycles the full set
    assert section_carrier(len(CARRIER_ROTATION)) == CARRIER_ROTATION[0]   # wraps


def test_carrier_rotation_no_garlands_singlestrand_double_weighted():
    # Garlands removed from deterministic rotation (was 4× community share)
    assert "Garlands" not in CARRIER_ROTATION
    # SingleStrand appears twice (community 28.5% workhorse) out of the 4-slot tuple
    assert CARRIER_ROTATION.count("SingleStrand") == 2


def test_fallback_weave_uses_rotated_carrier():
    wv = fallback_weave(_sec(), GROUPS, carrier="Bars")
    carriers = [c for c in wv.cells if c.role == "carrier"]
    assert carriers and all(c.effect_type == "Bars" for c in carriers)


def test_diversify_carrier_swaps_plain_keeps_distinctive():
    # a plain SingleStrand/On carrier is rotated...
    plain = SectionWeave(cells=[CellRecipe(effect_type="On", role="carrier", look_id="On#0",
                                           groups=["SEM_ARCHES"])])
    diversify_carrier(plain, "Garlands")
    assert plain.cells[0].effect_type == "Garlands" and plain.cells[0].look_id == ""
    # ...but a deliberately distinctive carrier (Spirals) is left alone
    fancy = SectionWeave(cells=[CellRecipe(effect_type="Spirals", role="carrier",
                                           groups=["SEM_ARCHES"])])
    diversify_carrier(fancy, "Garlands")
    assert fancy.cells[0].effect_type == "Spirals"
    # a non-carrier texture is never touched
    tex = SectionWeave(cells=[CellRecipe(effect_type="On", role="texture", groups=["SEM_ARCHES"])])
    diversify_carrier(tex, "Bars")
    assert tex.cells[0].effect_type == "On"


# -- composite stacks (multi-effect blended layers) ---------------------------

def test_expand_composite_stacks_layers_with_blend():
    from xlights_orchestrator.pipeline.weave import curated_composite, expand_composite
    rec = curated_composite("kaleidoscope", ["SEM_FOCAL"])
    assert rec is not None
    ins = expand_composite(rec, _sec(intensity=0.9), 0.9, ["SEM_FOCAL"])
    assert [i.layer for i in ins] == [0, 1]                       # two stacked layers
    assert all(i.target == "SEM_FOCAL" for i in ins)              # same group
    assert all(i.effect_type == "Spirals" for i in ins)           # kaleidoscope = two counter-rotating Spirals
    assert ins[0].extra_settings.get("T_CHOICE_LayerMethod") is None      # base = Normal
    assert ins[1].extra_settings.get("T_CHOICE_LayerMethod") == "Max"      # upper blends Max
    # counter-rotation: opposite E_SLIDER_Spirals_Rotation signs
    rot0 = ins[0].extra_settings.get("E_SLIDER_Spirals_Rotation")
    rot1 = ins[1].extra_settings.get("E_SLIDER_Spirals_Rotation")
    assert rot0 and rot1 and int(rot0) * int(rot1) < 0   # opposite signs — real motion contrast
    # layers differ by palette rotation so they COMBINE distinctly (not one hiding the other)
    assert ins[0].palette_colors != ins[1].palette_colors
    assert ins[0].start_ms == ins[1].start_ms                     # share the section span


def test_bloom_composite_all_layers_have_direction():
    """Every bloom layer's direction resolves to a non-empty xLights setting (no silent no-ops)."""
    from xlights_orchestrator.pipeline.weave import (
        CURATED_COMPOSITES, direction_setting,
    )
    layers = CURATED_COMPOSITES["bloom"]
    for i, lyr in enumerate(layers):
        if lyr.direction:
            ds = direction_setting(lyr.effect_type, lyr.direction, i)
            assert ds, (
                f"bloom layer {i} ({lyr.effect_type}/{lyr.direction}) returned empty "
                "direction_setting — check DIRECTION_KNOBS mapping"
            )


def test_expand_composite_needs_two_layers_and_valid_groups():
    from xlights_orchestrator.pipeline.weave import expand_composite
    from xlights_orchestrator.show_plan import CompositeLayer, CompositeRecipe
    one = CompositeRecipe(groups=["SEM_FOCAL"], layers=[CompositeLayer(effect_type="Morph")])
    assert expand_composite(one, _sec(), 0.8, ["SEM_FOCAL"]) == []          # <2 layers → nothing
    two = CompositeRecipe(groups=["NOPE"], layers=[CompositeLayer(effect_type="Morph"),
                                                   CompositeLayer(effect_type="Galaxy", blend="Max")])
    assert expand_composite(two, _sec(), 0.8, ["SEM_FOCAL"]) == []          # group not available → nothing


def test_curated_composite_unknown_name():
    from xlights_orchestrator.pipeline.weave import curated_composite
    assert curated_composite("does-not-exist", ["SEM_FOCAL"]) is None


# -- transition validation (xLights drops unrecognised transition types like 'fade') ----------

def test_canon_transition_maps_known_drops_unknown():
    from xlights_orchestrator.pipeline.weave import _canon_transition
    assert _canon_transition("wipe") == "Wipe"
    assert _canon_transition("WIPE") == "Wipe"
    assert _canon_transition("From Middle") == "From Middle"
    assert _canon_transition("dissolve") == "Dissolve"
    assert _canon_transition("fade") == ""          # a fade-time, not a transition type → dropped
    assert _canon_transition("") == "" and _canon_transition(None) == ""


# -- counter-rotation ---------------------------------------------------------

def test_two_spirals_recipes_on_same_groups_get_ltr_rtl():
    """_valid_recipes assigns ltr/rtl to same-type rotational pairs with no explicit direction."""
    w = SectionWeave(cells=[
        CellRecipe(effect_type="Spirals", role="texture", groups=["SEM_YARD"], cell_beats=4),
        CellRecipe(effect_type="Spirals", role="texture", groups=["SEM_YARD"], cell_beats=4),
    ])
    out = expand_weave(_sec(), w, _rhythm(8), 0.8, GROUPS)
    spirals = [c for c in out if c.effect_type == "Spirals"]
    assert spirals
    rotations = {c.extra_settings.get("E_SLIDER_Spirals_Rotation") for c in spirals}
    assert "20" in rotations and "-20" in rotations   # both directions present


def test_counter_rotate_stacks_flips_upper_overlapping():
    """counter_rotate_stacks sets rtl on the 2nd overlapping Spirals on the same target."""
    from xlights_orchestrator.show_plan import EffectInstruction
    a = EffectInstruction(target="SEM_FOCAL", effect_type="Spirals", look_id="x",
                          start_ms=0, end_ms=8000)
    b = EffectInstruction(target="SEM_FOCAL", effect_type="Spirals", look_id="x",
                          start_ms=0, end_ms=8000, layer=1)
    counter_rotate_stacks([a, b])
    assert a.extra_settings.get("E_SLIDER_Spirals_Rotation") == "20"
    assert b.extra_settings.get("E_SLIDER_Spirals_Rotation") == "-20"


def test_counter_rotate_stacks_is_idempotent():
    """Calling counter_rotate_stacks twice leaves directions unchanged."""
    from xlights_orchestrator.show_plan import EffectInstruction
    a = EffectInstruction(target="SEM_FOCAL", effect_type="Spirals", look_id="x",
                          start_ms=0, end_ms=8000)
    b = EffectInstruction(target="SEM_FOCAL", effect_type="Spirals", look_id="x",
                          start_ms=0, end_ms=8000, layer=1)
    counter_rotate_stacks([a, b])
    rot_a = a.extra_settings["E_SLIDER_Spirals_Rotation"]
    rot_b = b.extra_settings["E_SLIDER_Spirals_Rotation"]
    counter_rotate_stacks([a, b])   # second call — should be no-op
    assert a.extra_settings["E_SLIDER_Spirals_Rotation"] == rot_a
    assert b.extra_settings["E_SLIDER_Spirals_Rotation"] == rot_b


def test_counter_rotate_stacks_explicit_direction_survives():
    """An instruction already carrying the direction key is not overwritten."""
    from xlights_orchestrator.show_plan import EffectInstruction
    a = EffectInstruction(target="SEM_FOCAL", effect_type="Spirals", look_id="x",
                          start_ms=0, end_ms=8000,
                          extra_settings={"E_SLIDER_Spirals_Rotation": "80"})
    b = EffectInstruction(target="SEM_FOCAL", effect_type="Spirals", look_id="x",
                          start_ms=0, end_ms=8000, layer=1)
    counter_rotate_stacks([a, b])
    assert a.extra_settings["E_SLIDER_Spirals_Rotation"] == "80"   # explicit wins
    assert b.extra_settings["E_SLIDER_Spirals_Rotation"] == "-20"  # other gets rtl


def test_counter_rotate_stacks_non_overlapping_untouched():
    """Non-overlapping same-type instructions (sequential) each reset to ltr."""
    from xlights_orchestrator.show_plan import EffectInstruction
    a = EffectInstruction(target="SEM_FOCAL", effect_type="Spirals", look_id="x",
                          start_ms=0, end_ms=4000)
    b = EffectInstruction(target="SEM_FOCAL", effect_type="Spirals", look_id="x",
                          start_ms=4000, end_ms=8000)
    counter_rotate_stacks([a, b])
    assert a.extra_settings.get("E_SLIDER_Spirals_Rotation") == "20"  # ltr (first)
    assert b.extra_settings.get("E_SLIDER_Spirals_Rotation") == "20"  # ltr (non-overlapping reset)


def test_cell_drops_invalid_transition_keeps_valid():
    from xlights_orchestrator.pipeline.weave import _cell
    bad = _cell(_carrier(transition="fade"), _sec(), "SEM_ARCHES", 0, 0, 1000, 0.8, False)
    assert "T_CHOICE_In_Transition_Type" not in bad.extra_settings    # 'fade' not emitted
    good = _cell(_carrier(transition="Wipe"), _sec(), "SEM_ARCHES", 0, 0, 1000, 0.8, False)
    assert good.extra_settings.get("T_CHOICE_In_Transition_Type") == "Wipe"
