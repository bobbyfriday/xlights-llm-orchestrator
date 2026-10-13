"""The realization path (claude-driven-orchestration D3): a hand-written brief + the golden
fixture analysis → `generate_instructions_from_brief` with no model API and no xLights. Asserts coverage of every section, woven cells, that a section's `fabric` block is
honored, byte-identical output across two runs, and that recurring section labels rhyme through
the label-derived repetition map."""

from __future__ import annotations

import json

from xlights_orchestrator.brief_schema import build_brief_schema
from xlights_orchestrator.pipeline.generate import (
    generate_instructions_from_brief,
    realize_section_from_brief,
    repetition_map,
)
from xlights_orchestrator.pipeline.state import State
from xlights_orchestrator.pipeline.weave import CARRIER_ROTATION, section_carrier
from xlights_orchestrator.show_plan import (
    KeyMoment,
    SectionFabric,
    SectionPlan,
    ShowPalette,
    ShowPlan,
    normalize_label,
    repetition_map_from_labels,
)

from test_golden_pipeline import GROUPS, SORT_KEYS, _analysis

DIRECTED = SectionFabric(carrier="Wave", alternation="pingpong", cell_beats=2, blend="Brightness")


def _plan(fabric: SectionFabric | None = DIRECTED) -> ShowPlan:
    """Two sections like the golden plan: a quiet verse (feature treatment) and a full peak whose
    base rows cover its rhythm pool, so the carrier cells land over a base and get the blend."""
    return ShowPlan(
        concept="brief fixture",
        palette=ShowPalette(name="test", colors=["Red", "Green", "Blue"]),
        sections=[
            {"start_ms": 0, "end_ms": 12000, "label": "verse 1",
             "target_groups": ["SEM_ARCHES", "SEM_CANES"],
             "effect_family": "On", "intensity": 0.45, "palette": ["Red", "Green"],
             "effect_types": ["Twinkle"], "pulse_groups": ["SEM_ARCHES"], "pulse_on": "beat"},
            {"start_ms": 12000, "end_ms": 24000, "label": "chorus",
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


# -- section labels → the repetition map ---------------------------------------------------------

def _sec(i: int, label: str, intensity: float = 0.9) -> SectionPlan:
    return SectionPlan(start_ms=i * 8000, end_ms=(i + 1) * 8000, label=label,
                       target_groups=["SEM_ALL", "SEM_ARCHES", "SEM_CANES"], effect_family="On",
                       intensity=intensity, palette=["Red", "Blue"], pulse_groups=["SEM_ARCHES"])


def test_label_field_is_a_plain_string_in_the_schema():
    p = build_brief_schema(groups=["SEM_ALL"], effect_types=["On"], scene_ids=[], stems=[],
                           colors=[])["$defs"]["SectionPlan"]["properties"]["label"]
    assert p["type"] == "string" and p["default"] == "" and "enum" not in p
    assert SectionPlan(start_ms=0, end_ms=1, target_groups=[], effect_family="On",
                       intensity=0.5).label == ""


def test_normalize_label_drops_trailing_numbering():
    assert normalize_label("Chorus 1") == normalize_label("chorus 2") == "chorus"
    assert normalize_label("verse-1") == normalize_label("Verse #2") == "verse"
    assert normalize_label("  bridge ") == "bridge"
    assert normalize_label("") == normalize_label("   ") == ""


def test_repetition_map_from_labels_two_choruses_rhyme():
    secs = [_sec(0, "intro"), _sec(1, "verse 1"), _sec(2, "Chorus 1"),
            _sec(3, "verse 2"), _sec(4, "chorus 2"), _sec(5, "bridge"), _sec(6, "chorus")]
    assert repetition_map_from_labels(secs) == {"verse": [1, 3], "chorus": [2, 4, 6]}


def test_repetition_map_from_labels_excludes_one_offs_and_blanks():
    assert repetition_map_from_labels([_sec(0, "intro"), _sec(1, "chorus"), _sec(2, "outro")]) == {}
    assert repetition_map_from_labels([_sec(0, ""), _sec(1, ""), _sec(2, "  ")]) == {}
    assert repetition_map_from_labels([]) == {}


def test_repetition_map_comes_from_the_brief_labels():
    st = _state(ShowPlan(sections=[_sec(0, "chorus"), _sec(1, "chorus"), _sec(2, "verse")]))
    assert repetition_map(st) == {"chorus": [0, 1]}
    st.show_plan = ShowPlan(sections=[_sec(0, "a"), _sec(1, "b")])
    assert repetition_map(st) is None                                # nothing recurs → one-offs


def test_recurring_labels_rhyme_in_the_brief_path():
    """Two 'chorus' sections pick the SAME carrier (keyed on the label) and the last one gains
    the final-occurrence escalation; relabeling the second breaks the rhyme."""
    def carriers(plan):
        instrs = generate_instructions_from_brief(_state(plan))
        return {si: ({i.effect_type for i in instrs if i.source == "weave" and i.section_index == si}
                     & set(CARRIER_ROTATION))
                for si in range(len(plan.sections))}
    rhymed = carriers(ShowPlan(sections=[_sec(0, "verse"), _sec(1, "chorus 1"), _sec(2, "chorus 2")]))
    assert rhymed[1] == rhymed[2] and rhymed[1]
    plain = carriers(ShowPlan(sections=[_sec(0, "verse"), _sec(1, "chorus 1"), _sec(2, "bridge")]))
    assert plain[1] == {section_carrier(1, None)} and plain[2] == {section_carrier(2, None)}
