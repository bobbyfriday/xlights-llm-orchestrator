"""`weave_from_brief` — the brief's optional per-section `fabric` knobs (carrier, alternation,
cell_beats, blend) over the deterministic fallback weave (claude-driven-orchestration D3).

The contract: each field is honored when it names a vocabulary value; an absent/empty fabric is
BYTE-IDENTICAL to `fallback_weave`; an invalid carrier keeps the fallback; a non-rhythmic section
gets no cells at all."""

from __future__ import annotations

from xlights_orchestrator.pipeline.beats import section_is_rhythmic, section_rhythm
from xlights_orchestrator.pipeline.effect_meta import DURATION_CELLABLE
from xlights_orchestrator.pipeline.semantic_groups import RHYTHM_GROUPS, RHYTHM_POOL
from xlights_orchestrator.pipeline.weave import (
    brief_carrier,
    expand_weave,
    fallback_weave,
    rhythm_pool,
    weave_from_brief,
)
from xlights_orchestrator.show_plan import BLEND_METHODS, FABRIC_ALTERNATIONS, SectionFabric, SectionPlan

from test_golden_pipeline import GROUPS, _analysis

TARGETS = ["SEM_ARCHES", "SEM_CANES", "SEM_MINITREES", "SEM_ALL"]


def _section(fabric: SectionFabric | None = None, **kw) -> SectionPlan:
    base = dict(start_ms=0, end_ms=12000, target_groups=TARGETS, effect_family="On",
                intensity=0.8, palette=["Red", "Green"], effect_types=["Spirals", "Twinkle"],
                pulse_groups=["SEM_ARCHES", "SEM_CANES"], pulse_on="beat", fabric=fabric)
    base.update(kw)
    return SectionPlan(**base)


def _carrier(weave):
    cells = [c for c in weave.cells if c.role == "carrier"]
    assert len(cells) == 1, [c.model_dump() for c in weave.cells]
    return cells[0]


# -- directed fields ----------------------------------------------------------------------------

def test_directed_carrier_is_realized_on_the_rhythm_pool():
    sec = _section(SectionFabric(carrier="Bars"))
    assert "Bars" in DURATION_CELLABLE
    c = _carrier(weave_from_brief(sec, GROUPS))
    assert c.effect_type == "Bars"
    assert c.groups == rhythm_pool(sec, GROUPS)            # same pool as the fallback carrier
    assert c.look_id == ""                                  # the type picks its own first look


def test_directed_carrier_accepts_display_names():
    """'Single Strand' (the guides' display name) canonicalizes to the placeable 'SingleStrand'."""
    c = _carrier(weave_from_brief(_section(SectionFabric(carrier="Single Strand")), GROUPS,
                                  carrier="Bars"))
    assert c.effect_type == "SingleStrand"


def test_directed_alternation():
    for alt in FABRIC_ALTERNATIONS:
        c = _carrier(weave_from_brief(_section(SectionFabric(alternation=alt)), GROUPS))
        assert c.alternation == alt


def test_directed_cell_beats():
    c = _carrier(weave_from_brief(_section(SectionFabric(cell_beats=4)), GROUPS))
    assert c.cell_beats == 4


def test_directed_blend():
    c = _carrier(weave_from_brief(_section(SectionFabric(blend="Brightness")), GROUPS))
    assert c.blend == "Brightness"
    assert "Brightness" in BLEND_METHODS


def test_all_four_knobs_together_match_the_spec_scenario():
    """Spec: 'SingleStrand with pingpong at 2 beats' → SingleStrand carrier cells, ping-pong across
    the rhythm pool, two beats each."""
    sec = _section(SectionFabric(carrier="SingleStrand", alternation="pingpong", cell_beats=2,
                                 blend="Max"))
    w = weave_from_brief(sec, GROUPS, carrier="Bars")      # the rotation wanted Bars; the brief wins
    c = _carrier(w)
    assert (c.effect_type, c.alternation, c.cell_beats, c.blend) == \
        ("SingleStrand", "pingpong", 2, "Max")
    # the texture cell is untouched by the fabric knobs (only the carrier is directed)
    tex = [x for x in w.cells if x.role == "texture"]
    assert tex == [x for x in fallback_weave(sec, GROUPS, carrier="SingleStrand").cells
                   if x.role == "texture"]


def test_fabric_knobs_reach_the_expanded_cells():
    """The directed knobs survive expansion: ping-pong target rotation, 2-beat cells (1000 ms at
    120 BPM), and the blend on cells placed over a base."""
    sec = _section(SectionFabric(carrier="Bars", alternation="pingpong", cell_beats=2,
                                 blend="Brightness"))
    w = weave_from_brief(sec, GROUPS)
    pool = rhythm_pool(sec, GROUPS)
    rhythm = section_rhythm(_analysis(), sec, 4)
    cells = [i for i in expand_weave(sec, w, rhythm, 0.8, GROUPS, based_targets=set(pool))
             if i.effect_type == "Bars"]
    assert cells, "no carrier cells expanded"
    assert all(i.extra_settings.get("T_CHOICE_LayerMethod") == "Brightness" for i in cells)
    assert {i.end_ms - i.start_ms for i in cells} == {1000}
    # ping-pong over [A, B] is A B A B …; over the pool it bounces at the ends
    order = [i.target for i in sorted(cells, key=lambda i: i.start_ms)]
    n = len(pool)
    expected = [pool[k if k < n else (2 * n - 2) - k] for k in
                (slot % (2 * n - 2) for slot in range(len(order)))] if n > 1 else [pool[0]] * len(order)
    assert order == expected


# -- the absent / fallback paths ----------------------------------------------------------------

def test_absent_fabric_equals_fallback_weave():
    for carrier in ("SingleStrand", "Bars", "Wave"):
        sec = _section(None)
        assert weave_from_brief(sec, GROUPS, carrier=carrier) == \
            fallback_weave(sec, GROUPS, carrier=carrier)
        assert weave_from_brief(sec, GROUPS, carrier=carrier).model_dump_json() == \
            fallback_weave(sec, GROUPS, carrier=carrier).model_dump_json()


def test_empty_fabric_block_equals_fallback_weave():
    sec = _section(SectionFabric())
    assert weave_from_brief(sec, GROUPS).model_dump_json() == \
        fallback_weave(sec, GROUPS).model_dump_json()


def test_invalid_carrier_falls_back():
    # not cellable (a HIT-class effect) and not an effect at all
    for bad in ("Fireworks", "Strobe", "NotAnEffect"):
        c = _carrier(weave_from_brief(_section(SectionFabric(carrier=bad)), GROUPS, carrier="Wave"))
        assert c.effect_type == "Wave", bad
        assert brief_carrier(_section(SectionFabric(carrier=bad)), "Wave") == "Wave"


def test_unknown_alternation_and_blend_keep_the_defaults():
    c = _carrier(weave_from_brief(_section(SectionFabric(alternation="zigzag", blend="Glow")),
                                  GROUPS))
    assert c.alternation == "chase" and c.blend == ""


def test_non_rhythmic_section_gets_no_cells_even_with_a_fabric():
    quiet = next(g for g in GROUPS if g not in RHYTHM_POOL and g not in RHYTHM_GROUPS)
    sec = _section(SectionFabric(carrier="Bars", alternation="all", cell_beats=2, blend="Max"),
                   intensity=0.05, pulse_groups=[], target_groups=[quiet])
    assert not section_is_rhythmic(sec)
    assert weave_from_brief(sec, GROUPS).cells == []
    assert weave_from_brief(sec, GROUPS) == fallback_weave(sec, GROUPS)


def test_brief_loads_a_fabric_block_from_json():
    sec = SectionPlan.model_validate({
        "start_ms": 0, "end_ms": 1000, "target_groups": ["SEM_ALL"], "effect_family": "On",
        "intensity": 0.5,
        "fabric": {"carrier": "SingleStrand", "alternation": "pingpong", "cell_beats": 2,
                   "blend": "Max"}})
    assert sec.fabric == SectionFabric(carrier="SingleStrand", alternation="pingpong",
                                       cell_beats=2, blend="Max")
    assert SectionPlan.model_validate({"start_ms": 0, "end_ms": 1, "target_groups": [],
                                       "effect_family": "On", "intensity": 0.5}).fabric is None


# -- an explicit carrier re-enables the fabric under pulse / feature (wave 2, lane H) -----------

def _realized(fabric: SectionFabric | None, treatment: str, **kw):
    from xlights_orchestrator.pipeline.generate import realize_section_from_brief
    from xlights_orchestrator.pipeline.state import State
    from xlights_orchestrator.show_plan import ShowPlan
    st = State(song_path="song.mp3")
    st.song_analysis = _analysis()
    st.available_groups = list(GROUPS)
    st.show_plan = ShowPlan(sections=[_section(fabric, treatment=treatment, **kw)])
    return realize_section_from_brief(st, 0)


def _woven_types(rows) -> set[str]:
    return {r.effect_type for r in rows if r.source == "weave"}


def test_explicit_carrier_weaves_under_pulse_and_feature():
    explicit = SectionFabric(carrier="Bars", alternation="pingpong", cell_beats=2, blend="Max")
    pulse = _realized(explicit, "pulse")
    assert "Bars" in _woven_types(pulse)                                 # the carrier cells
    assert _woven_types(pulse) - {"Bars"}                                # + the texture cell
    cells = [r for r in pulse if r.source == "weave" and r.effect_type == "Bars"]
    assert {r.end_ms - r.start_ms for r in cells} == {1000}             # the knobs still apply
    feature = _realized(explicit, "feature")
    assert _woven_types(feature) == {"Bars"}                             # the carrier cell ONLY
    rest = _realized(explicit, "rest")
    assert rest and _woven_types(rest) == set()                          # rest stays still


def test_absent_or_carrierless_fabric_keeps_the_treatment_table():
    for fabric in (None, SectionFabric(), SectionFabric(alternation="pingpong", cell_beats=2)):
        assert _woven_types(_realized(fabric, "pulse")) == set()
        assert _woven_types(_realized(fabric, "feature")) == set()
    # full / gesture are unchanged by an explicit carrier: full weaves everything either way,
    # gesture keeps its single held carrier
    explicit = SectionFabric(carrier="Bars")
    full = _woven_types(_realized(explicit, "full"))
    assert "Bars" in full and full - {"Bars"}
    assert _woven_types(_realized(explicit, "gesture")) == {"Bars"}
