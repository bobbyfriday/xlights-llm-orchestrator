"""The deterministic rhythm layers respect each section's brief intent."""

from __future__ import annotations

from xlights_orchestrator.pipeline.beats import RHYTHM_FLOOR, section_is_rhythmic
from xlights_orchestrator.pipeline.weave import fallback_weave, rhythm_pool
from xlights_orchestrator.show_plan import CellRecipe, SectionPlan, SectionWeave
from xlights_orchestrator.pipeline.weave import expand_weave

AVAIL = ["SEM_ALL", "SEM_SNOWFLAKES", "SEM_ARCHES", "SEM_CANES", "SEM_MINITREES",
         "SEM_SIDE_LEFT", "SEM_FOCAL"]


def _sec(intensity=0.2, targets=("SEM_ALL", "SEM_SNOWFLAKES"), pulse=()):
    return SectionPlan(start_ms=0, end_ms=100000, target_groups=list(targets),
                       effect_family="On", intensity=intensity, palette=["deep blue"],
                       pulse_groups=list(pulse))


# -- the gate ------------------------------------------------------------------

def test_section_is_rhythmic_truth_table():
    # quiet, no pulse groups, no rhythm targets → NOT rhythmic (the Christmas Canon §0 case)
    assert section_is_rhythmic(_sec(0.2, ("SEM_ALL", "SEM_SNOWFLAKES"), ())) is False
    # explicit pulse groups → rhythmic
    assert section_is_rhythmic(_sec(0.2, ("SEM_ALL",), ("SEM_ARCHES",))) is True
    # rhythm prop in targets → rhythmic
    assert section_is_rhythmic(_sec(0.2, ("SEM_ARCHES", "SEM_ALL"), ())) is True
    # energetic → rhythmic even with no rhythm groups named
    assert section_is_rhythmic(_sec(RHYTHM_FLOOR, ("SEM_ALL",), ())) is True
    assert section_is_rhythmic(_sec(0.9, ("SEM_ALL",), ())) is True


# -- rhythm_pool respects the brief --------------------------------------------

def test_rhythm_pool_no_injection_when_quiet():
    # quiet section that chose no rhythm groups → empty (won't light arches/canes)
    assert rhythm_pool(_sec(0.2, ("SEM_ALL", "SEM_SNOWFLAKES"), ()), AVAIL) == []


def test_rhythm_pool_uses_chosen_groups():
    assert rhythm_pool(_sec(0.2, ("SEM_ALL",), ("SEM_ARCHES",)), AVAIL) == ["SEM_ARCHES"]
    # rhythm prop chosen in targets is used (and being rhythmic, the pool fills to >=3)
    pool = rhythm_pool(_sec(0.2, ("SEM_CANES", "SEM_ALL"), ()), AVAIL)
    assert "SEM_CANES" in pool


def test_rhythm_pool_injects_when_energetic():
    pool = rhythm_pool(_sec(0.9, ("SEM_ALL",), ()), AVAIL)   # energetic → default pool injected
    assert set(pool) & set(("SEM_ARCHES", "SEM_CANES", "SEM_MINITREES"))


# -- fallback weave ------------------------------------------------------------

def test_fallback_weave_empty_when_quiet():
    assert fallback_weave(_sec(0.2, ("SEM_ALL", "SEM_SNOWFLAKES"), ()), AVAIL).cells == []


def test_fallback_weave_present_when_energetic():
    w = fallback_weave(_sec(0.9, ("SEM_ALL",), ()), AVAIL)
    assert any(c.role == "carrier" for c in w.cells)


def test_llm_weave_still_expands_when_quiet():
    # a quiet section's fallback is empty, but an explicit LLM weave is still honored
    sec = _sec(0.2, ("SEM_ARCHES",), ())
    w = SectionWeave(cells=[CellRecipe(effect_type="SingleStrand", role="carrier",
                                       cell_beats=1, groups=["SEM_ARCHES"])])
    rhythm = {"beats_ms": [i * 500 for i in range(8)], "prominent_stem": None,
              "onsets_by_stem": {}, "chords_ms": [], "tempo": 120}
    out = expand_weave(sec, w, rhythm, 0.2, AVAIL)
    assert out                                              # LLM weave expands regardless of the gate
