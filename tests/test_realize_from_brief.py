"""The LLM-free realization path (claude-driven-orchestration D3): a hand-written brief + the
golden fixture analysis → `generate_instructions_from_brief` with no agent, no model API, no
xLights. Asserts coverage of every section, woven cells, that a section's `fabric` block is
honored, and byte-identical output across two runs."""

from __future__ import annotations

import json

from xlights_orchestrator.pipeline.generate import (
    generate_instructions_from_brief,
    realize_section_from_brief,
)
from xlights_orchestrator.pipeline.state import State
from xlights_orchestrator.pipeline.weave import CARRIER_ROTATION, section_carrier
from xlights_orchestrator.show_plan import KeyMoment, SectionFabric, ShowPalette, ShowPlan

from test_golden_pipeline import GROUPS, SORT_KEYS, _analysis

DIRECTED = SectionFabric(carrier="Wave", alternation="pingpong", cell_beats=2, blend="Brightness")


def _plan(fabric: SectionFabric | None = DIRECTED) -> ShowPlan:
    """Two sections like the golden plan: a quiet verse (feature treatment) and a full peak whose
    base rows cover its rhythm pool, so the carrier cells land over a base and get the blend."""
    return ShowPlan(
        concept="brief fixture",
        palette=ShowPalette(name="test", colors=["Red", "Green", "Blue"]),
        sections=[
            {"start_ms": 0, "end_ms": 12000, "target_groups": ["SEM_ARCHES", "SEM_CANES"],
             "effect_family": "On", "intensity": 0.45, "palette": ["Red", "Green"],
             "effect_types": ["Twinkle"], "pulse_groups": ["SEM_ARCHES"], "pulse_on": "beat"},
            {"start_ms": 12000, "end_ms": 24000,
             "target_groups": ["SEM_ALL", "SEM_FOCAL", "SEM_CANES", "SEM_ARCHES"],
             "effect_family": "On", "intensity": 0.92, "palette": ["Blue", "Red"],
             "effect_types": ["Spirals", "Fireworks"],
             "pulse_groups": ["SEM_CANES", "SEM_ARCHES"], "pulse_on": "onset",
             "fabric": fabric},
        ],
        key_moments=[KeyMoment(at_ms=12000, kind="climax", treatment="the drop")],
    )


def _state(plan: ShowPlan) -> State:
    st = State(song_path="song.mp3")
    st.song_analysis = _analysis()
    st.available_groups = list(GROUPS)
    st.show_plan = plan
    return st


def _dump(instrs) -> list[dict]:
    return sorted((i.model_dump() for i in instrs),
                  key=lambda d: tuple(str(d.get(k)) for k in SORT_KEYS))


def test_covers_every_section_and_weaves_cells():
    instrs = generate_instructions_from_brief(_state(_plan()))
    assert {i.section_index for i in instrs if i.section_index is not None} == {0, 1}
    assert len(instrs) > 10
    woven = [i for i in instrs if i.source == "weave"]
    assert woven and all(i.section_index == 1 for i in woven)     # the full peak weaves; the
    assert any(i.source == "bed" for i in instrs)                   # feature verse withholds it
    assert any(i.source == "accents" for i in instrs)
    # base rows: one per target group, from the brief's effect vocabulary, looks from the catalog
    base = [i for i in instrs if i.source == "generator" and i.section_index == 1]
    assert base and {i.effect_type for i in base} <= {"On", "Spirals", "Fireworks"}
    assert all(i.look_id for i in base)


def test_fabric_block_is_honored_on_its_section():
    instrs = generate_instructions_from_brief(_state(_plan()))
    cells = [i for i in instrs if i.source == "weave" and i.section_index == 1
             and i.effect_type == "Wave"]
    assert cells, "the directed Wave carrier did not weave"
    assert section_carrier(1, None) != "Wave"                       # the rotation would NOT pick it
    assert {i.end_ms - i.start_ms for i in cells} == {1000}         # 2 beats at 120 BPM
    assert all(i.extra_settings.get("T_CHOICE_LayerMethod") == "Brightness" for i in cells)
    # ping-pong alternation: consecutive cells never repeat a target when the pool has >1 group
    order = [i.target for i in sorted(cells, key=lambda i: i.start_ms)]
    assert len(set(order)) > 1 and all(a != b for a, b in zip(order, order[1:]))


def test_without_a_fabric_block_the_rotation_carrier_weaves():
    instrs = generate_instructions_from_brief(_state(_plan(fabric=None)))
    carriers = {i.effect_type for i in instrs if i.source == "weave" and i.section_index == 1} \
        & set(CARRIER_ROTATION)
    assert carriers == {section_carrier(1, None)}


def test_realize_section_from_brief_tags_every_row():
    rows = realize_section_from_brief(_state(_plan()), 1)
    assert rows and all(r.section_index == 1 for r in rows)
    assert all(r.source for r in rows)                              # provenance on every row


def test_byte_identical_across_two_runs():
    a = json.dumps(_dump(generate_instructions_from_brief(_state(_plan()))), sort_keys=True)
    b = json.dumps(_dump(generate_instructions_from_brief(_state(_plan()))), sort_keys=True)
    assert a == b
