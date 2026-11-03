"""The authored stack: model, vocab/schema, validation, expansion, and its place in realization."""

from __future__ import annotations

import json

from xlights_core.knowledge import get_library
from xlights_orchestrator.brief_schema import build_brief_schema
from xlights_orchestrator.pipeline import catalog
from xlights_orchestrator.pipeline.generate import generate_instructions_from_brief
from xlights_orchestrator.pipeline.stack import expand_stack, stack_has_role
from xlights_orchestrator.pipeline.validate_brief import validate_brief
from xlights_orchestrator.pipeline.vocab import build_vocab, load_vocab, write_vocab
from xlights_orchestrator.show_plan import SectionPlan, ShowPlan, StackLayer
from test_golden_pipeline import DURATION_S, GROUPS, _state

lib = get_library()
BEATS = [int(t * 500) for t in range(0, 48)]            # 120 BPM over 24 s
RHYTHM = {"beats_ms": BEATS, "beats_per_bar": 4, "tempo": 120.0}


def _section(stack: list[StackLayer], **kw) -> SectionPlan:
    base = dict(start_ms=0, end_ms=8000, label="chorus", target_groups=["SEM_FOCAL", "SEM_ARCHES"],
                effect_family="Spirals", intensity=0.8, palette=["red", "green", "white"])
    base.update(kw)
    return SectionPlan(stack=stack, **base)


def test_hold_layers_one_row_per_group_bottom_to_top():
    sec = _section([
        StackLayer(effect_type="Ripple", role="bed", look_id="Ripple#47", knobs={"Ripple_Thickness": "3"}),
        StackLayer(effect_type="Spirals", role="feature", blend="Max", transform="Rotate CW 90",
                   settings={"C_SLIDER_SparkleFrequency": "40"}, fade_in=0.25, fade_out=0.25,
                   brightness=0.8, direction="ltr"),
    ])
    rows = expand_stack(sec, RHYTHM, GROUPS, seed=3)
    # logical layers: the brief lists bottom → top, the bed is 0 and the feature 1 (the emitter
    # flips to xLights indices, where 0 is the top)
    assert [(r.effect_type, r.layer, r.target) for r in rows] == [
        ("Ripple", 0, "SEM_FOCAL"), ("Ripple", 0, "SEM_ARCHES"),
        ("Spirals", 1, "SEM_FOCAL"), ("Spirals", 1, "SEM_ARCHES")]
    assert all(r.start_ms == 0 and r.end_ms == 8000 and r.source == "stack" for r in rows)
    assert rows[0].look_id == "Ripple#47" and rows[0].knob_values == {"Ripple_Thickness": "3"}
    sp = rows[2]
    assert sp.look_id == catalog.pick_look("Spirals", 3 + 1)      # the picker, seeded per layer
    assert sp.extra_settings["T_CHOICE_LayerMethod"] == "Max"
    assert sp.extra_settings["B_CHOICE_BufferTransform"] == "Rotate CW 90"
    assert sp.extra_settings["C_SLIDER_SparkleFrequency"] == "40"
    assert sp.extra_settings["T_TEXTCTRL_Fadein"] == "0.25" and sp.extra_settings["T_TEXTCTRL_Fadeout"] == "0.25"
    assert sp.extra_settings["C_SLIDER_Brightness"] == "80"
    assert sp.directed and sp.extra_settings.get("E_TEXTCTRL_Spirals_Movement")   # ltr → a signed spin
    assert rows[2].palette_colors != rows[0].palette_colors            # layers rotate the palette


def test_cells_follow_the_beat_grid_and_alternation():
    sec = _section([StackLayer(effect_type="Shockwave", role="carrier", cell_beats=1,
                               alternation="chase", groups=["SEM_FOCAL", "SEM_ARCHES"])])
    rows = expand_stack(sec, RHYTHM, GROUPS)
    assert len(rows) == 16                                   # 8 s at 120 BPM, one cell per beat
    assert [r.target for r in rows[:4]] == ["SEM_FOCAL", "SEM_ARCHES", "SEM_FOCAL", "SEM_ARCHES"]
    assert [(r.start_ms, r.end_ms) for r in rows[:2]] == [(0, 500), (500, 1000)]
    assert rows[-1].end_ms == 8000
    both = expand_stack(_section([StackLayer(effect_type="Bars", cell_beats=2)]), RHYTHM, GROUPS)
    assert len(both) == 16 and {r.target for r in both} == {"SEM_FOCAL", "SEM_ARCHES"}   # "all" default
    assert both[0].end_ms == 1000


def test_twins_sit_one_layer_above_and_differ_as_named():
    def rows_for(twin, **kw):
        sec = _section([StackLayer(effect_type="Spirals", groups=["SEM_FOCAL"], twin=twin, **kw)])
        return expand_stack(sec, RHYTHM, GROUPS)
    mirror = rows_for("mirror")
    assert [r.layer for r in mirror] == [0, 1]              # the twin one logical layer above its base
    assert "B_CHOICE_BufferTransform" not in mirror[0].extra_settings
    assert mirror[1].extra_settings["B_CHOICE_BufferTransform"] == "Rotate 180"
    mirror2 = rows_for("mirror", transform="Rotate CW 90")
    assert mirror2[1].extra_settings["B_CHOICE_BufferTransform"] == "Flip Horizontal"
    flip = rows_for("flip")
    assert flip[1].extra_settings["B_CHOICE_BufferTransform"] == "Flip Horizontal"
    counter = rows_for("counter", direction="ltr", look_id="Spirals#57",
                       knobs={"E_SLIDER_Spirals_Rotation": "20", "E_TEXTCTRL_Spirals_Movement": "2"})
    a, b = counter
    assert float(a.extra_settings["E_TEXTCTRL_Spirals_Movement"]) == 2.0        # the knob's magnitude
    assert float(b.extra_settings["E_TEXTCTRL_Spirals_Movement"]) == -2.0       # reversed, same pace
    assert a.knob_values["E_SLIDER_Spirals_Rotation"] == "20" and b.knob_values["E_SLIDER_Spirals_Rotation"] == "-20"
    # an undirected counter pair is still opposed (the base takes ltr), and a direction CHECKBOX
    # (Pinwheel's Rotation) is flipped, never "negated"
    sec = _section([StackLayer(effect_type="Pinwheel", groups=["SEM_FOCAL"], look_id="Pinwheel#86",
                               knobs={"E_SLIDER_Pinwheel_Arms": "3"}, twin="counter")])
    p, q = expand_stack(sec, RHYTHM, GROUPS)
    assert {p.extra_settings["E_CHECKBOX_Pinwheel_Rotation"], q.extra_settings["E_CHECKBOX_Pinwheel_Rotation"]} == {"0", "1"}
    assert "E_CHECKBOX_Pinwheel_Rotation" not in q.knob_values
    color = rows_for("color")
    assert color[0].palette_colors != color[1].palette_colors
    # a twin consumes the layer above: the next stack layer lands on 2
    sec = _section([StackLayer(effect_type="Spirals", groups=["SEM_FOCAL"], twin="mirror"),
                    StackLayer(effect_type="Warp", groups=["SEM_FOCAL"], role="overlay")])
    assert [r.layer for r in expand_stack(sec, RHYTHM, GROUPS)] == [0, 1, 2]   # Warp (listed last) is the top
    assert stack_has_role(sec, "overlay") and not stack_has_role(sec, "accent")


def test_unknown_groups_and_types_are_dropped_not_fatal():
    sec = _section([StackLayer(effect_type="NoSuchEffect"), StackLayer(effect_type="Bars", groups=["SEM_NOPE"])])
    assert expand_stack(sec, RHYTHM, GROUPS) == []


# -- vocab / schema / validation ---------------------------------------------------------------

def _vocab() -> dict:
    return build_vocab(groups=GROUPS, effect_types=catalog.placeable_effect_types(),
                       cellable=["Spirals", "Bars"], scene_ids=[], stems=["drums"],
                       colors=["red", "green", "white"], looks=catalog.look_ids_by_type())


def test_vocab_carries_looks_transforms_roles_and_round_trips(tmp_path):
    v = _vocab()
    assert v["looks"]["Spirals"][0] == catalog.ranked_look_ids("Spirals")[0]
    assert "Rotate 180" in v["transforms"] and "overlay" in v["stack_roles"]
    write_vocab(tmp_path, v)
    back = load_vocab(tmp_path)
    assert back["looks"] == v["looks"] and back["transforms"] == v["transforms"]
    schema = build_brief_schema(groups=GROUPS, effect_types=v["effect_types"], scene_ids=[], stems=[],
                                colors=v["colors"], cellable=v["cellable"])
    stk = schema["$defs"]["StackLayer"]["properties"]
    assert "mirror" in stk["twin"]["enum"] and "Rotate 180" in stk["transform"]["enum"]
    assert stk["groups"]["items"]["enum"] == GROUPS and "bed" in stk["role"]["enum"]


def _brief(stack: list[dict]) -> dict:
    return {"sections": [{"start_ms": 0, "end_ms": int(DURATION_S * 1000), "label": "chorus",
                          "target_groups": ["SEM_FOCAL"], "effect_family": "Spirals",
                          "intensity": 0.8, "palette": ["red", "green"], "stack": stack}]}


def test_validate_brief_accepts_a_good_stack_and_names_every_bad_field():
    good = _brief([{"effect_type": "Spirals", "role": "feature", "look_id": "Spirals#57",
                    "knobs": {"E_SLIDER_Spirals_Rotation": "20"}, "twin": "mirror",
                    "settings": {"C_SLIDER_SparkleFrequency": "40"}, "cell_beats": 2}])
    res = validate_brief(good, _vocab(), duration_ms=int(DURATION_S * 1000))
    assert res.ok, [e.model_dump() for e in res.errors]
    bad = _brief([{"effect_type": "Spirals", "role": "hero", "look_id": "Spirals#9999",
                   "knobs": {"E_SLIDER_Spirals_Rotation": "20"}, "blend": "Bogus",
                   "transform": "Spin", "direction": "sideways", "twin": "evil",
                   "groups": ["SEM_NOPE"], "settings": {"T_CHOICE_LayerMethod": "Max", "lowercase": "1"},
                   "cell_beats": 99}])
    res = validate_brief(bad, _vocab(), duration_ms=int(DURATION_S * 1000))
    paths = {e.path for e in res.errors}
    for tail in ("role", "look_id", "blend", "transform", "direction", "twin", "groups[0]",
                 "settings.T_CHOICE_LayerMethod", "settings.lowercase", "cell_beats"):
        assert f"sections[0].stack[0].{tail}" in paths, (tail, sorted(paths))
    # a knob outside its look's observed range, and a knob the look froze
    rng = _brief([{"effect_type": "Spirals", "look_id": "Spirals#57",
                   "knobs": {"E_SLIDER_Spirals_Rotation": "250", "E_CHECKBOX_Spirals_Grow": "1"}}])
    res = validate_brief(rng, _vocab(), duration_ms=int(DURATION_S * 1000))
    paths = {e.path for e in res.errors}
    assert "sections[0].stack[0].knobs.E_SLIDER_Spirals_Rotation" in paths
    assert "sections[0].stack[0].knobs.E_CHECKBOX_Spirals_Grow" in paths
    look = lib.get_look("Spirals", "Spirals#57")
    assert any(e.allowed and "…" in e.allowed[0] for e in res.errors if e.path.endswith("Spirals_Rotation"))
    assert "E_CHECKBOX_Spirals_Grow" in look.frozen_base


# -- realization --------------------------------------------------------------------------------

def test_a_stack_section_realizes_only_its_stack_plus_accents():
    plan = ShowPlan(sections=[SectionPlan(
        start_ms=0, end_ms=int(DURATION_S * 1000), label="chorus",
        target_groups=["SEM_FOCAL", "SEM_ARCHES"], effect_family="Spirals", intensity=0.9,
        palette=["red", "green", "white"],
        stack=[StackLayer(effect_type="Ripple", role="bed", groups=["SEM_FOCAL"]),
               StackLayer(effect_type="Spirals", role="feature", groups=["SEM_FOCAL"], twin="mirror",
                          look_id="Spirals#57", knobs={"E_SLIDER_Spirals_Thickness": "50"}),
               StackLayer(effect_type="Shockwave", role="carrier", groups=["SEM_ARCHES"], cell_beats=1)])])
    rows = generate_instructions_from_brief(_state(plan))
    sources = {r.source for r in rows}
    assert "stack" in sources
    assert not sources & {"weave", "composite", "bed", "phrase", "vu", "feature", "generator"}
    stack_rows = [r for r in rows if r.source == "stack"]
    assert {r.effect_type for r in stack_rows} == {"Ripple", "Spirals", "Shockwave"}
    assert sum(1 for r in stack_rows if r.effect_type == "Spirals") == 2       # the twin
    assert all(r.knob_values == {"E_SLIDER_Spirals_Thickness": "50"} for r in stack_rows if r.effect_type == "Spirals")
    assert sum(1 for r in stack_rows if r.effect_type == "Shockwave") > 20   # one per beat
    # the same brief twice is byte-identical (the stack is deterministic)
    again = generate_instructions_from_brief(_state(plan))
    assert [r.model_dump() for r in rows] == [r.model_dump() for r in again]
    # the stack survives a JSON round trip of the brief
    assert ShowPlan.model_validate(json.loads(plan.model_dump_json())).sections[0].stack[1].twin == "mirror"


def test_a_stack_accent_layer_silences_code_accents():
    def rows(stack):
        plan = ShowPlan(sections=[SectionPlan(start_ms=0, end_ms=int(DURATION_S * 1000), label="chorus",
                                              target_groups=["SEM_FOCAL"], effect_family="Spirals",
                                              intensity=0.9, palette=["red", "green"], stack=stack)])
        return generate_instructions_from_brief(_state(plan))
    with_code_accents = rows([StackLayer(effect_type="Spirals", groups=["SEM_FOCAL"])])
    own = rows([StackLayer(effect_type="Spirals", groups=["SEM_FOCAL"]),
                StackLayer(effect_type="Shockwave", role="accent", groups=["SEM_FOCAL"], cell_beats=1)])
    assert any(r.source == "accents" for r in with_code_accents)
    assert not any(r.source == "accents" for r in own)


def test_layers_count_per_group_not_across_groups():
    sec = _section([StackLayer(effect_type="SingleStrand", groups=["SEM_FOCAL"], cell_beats=1),
                    StackLayer(effect_type="SingleStrand", groups=["SEM_FOCAL"], cell_beats=1),
                    StackLayer(effect_type="Warp", role="overlay", groups=["SEM_FOCAL"]),
                    StackLayer(effect_type="Pinwheel", groups=["SEM_ARCHES"], twin="counter")])
    rows = expand_stack(sec, RHYTHM, GROUPS)
    assert {r.layer for r in rows if r.target == "SEM_FOCAL"} == {0, 1, 2}
    assert [r.layer for r in rows if r.target == "SEM_ARCHES"] == [0, 1]      # the pair owns 0 and 1 on its own group
    warp = next(r for r in rows if r.effect_type == "Warp")
    assert warp.layer == 2                                                    # the overlay is the top logical layer


def test_counter_twin_negation_stays_inside_the_looks_range():
    sec = _section([StackLayer(effect_type="Spirals", groups=["SEM_FOCAL"], look_id="Spirals#80",
                               knobs={"E_SLIDER_Spirals_Rotation": "-80"}, twin="counter")])
    a, b = expand_stack(sec, RHYTHM, GROUPS)
    assert a.knob_values["E_SLIDER_Spirals_Rotation"] == "-80"
    assert b.knob_values["E_SLIDER_Spirals_Rotation"] == "40"               # +80 is outside [-80, 40]
    look = lib.get_look("Spirals", "Spirals#80")
    knob = next(k for k in look.knobs if k.key == "E_SLIDER_Spirals_Rotation")
    assert knob.min <= float(b.knob_values["E_SLIDER_Spirals_Rotation"]) <= knob.max


def test_layer_budget_clamp_keeps_stack_rows_over_synthesized_ones():
    from xlights_orchestrator.effect_emitter import clamp_layer_budget
    from xlights_orchestrator.show_plan import EffectInstruction
    def row(et, layer, source):
        return EffectInstruction(target="SEM_FOCAL", effect_type=et, look_id="x", layer=layer,
                                 start_ms=0, end_ms=1000, source=source)
    rows = [row("On", 0, "accents"), row("On", 0, "accents"), row("On", 0, "accents"),
            row("Spirals", 0, "stack"), row("Spirals", 1, "stack"), row("Warp", 2, "stack")]
    kept, dropped = clamp_layer_budget(rows, max_layers=4)
    assert dropped == 2
    assert [r.effect_type for r in kept] == ["On", "Spirals", "Spirals", "Warp"]   # order preserved, stack intact
