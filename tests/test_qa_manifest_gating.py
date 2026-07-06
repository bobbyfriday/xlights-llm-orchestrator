"""F-E slice 6b — manifest-derived QA capability gating (design decision 10b)."""

from __future__ import annotations

from types import SimpleNamespace

from xlights_orchestrator.qa.rules import _is_linear, _target_res, evaluate
from xlights_orchestrator.show_plan import EffectInstruction


def _ins(effect, target, si=0):
    return EffectInstruction(target=target, effect_type=effect, look_id="x",
                             start_ms=0, end_ms=2000, section_index=si)


def _plan(intensities):
    return SimpleNamespace(sections=[SimpleNamespace(intensity=x) for x in intensities])


def _manifest(props, groups):
    def _p(name, res):
        return SimpleNamespace(id=name, res=res)
    def _g(members):
        return SimpleNamespace(members=members)
    return SimpleNamespace(
        props=[_p(n, r) for n, r in props.items()],
        groups={n: _g(ms) for n, ms in groups.items()},
    )


# -- _target_res --------------------------------------------------------------------------------
def test_target_res_prop_and_group_union():
    m = _manifest({"A": "LINEAR_LOW", "B": "LINEAR_HIGH", "C": "2D_SURFACE"},
                  {"Grp": ["A", "B"], "Mixed": ["A", "C"]})
    assert _target_res("A", m) == {"LINEAR_LOW"}
    assert _target_res("Grp", m) == {"LINEAR_LOW", "LINEAR_HIGH"}
    assert _target_res("Mixed", m) == {"LINEAR_LOW", "2D_SURFACE"}
    assert _target_res("Unknown", m) is None
    assert _target_res("A", None) is None


# -- manifest-gated _is_linear ------------------------------------------------------------------
def test_linear_membered_group_with_non_sem_name_is_flagged():
    # a user-named group whose members are all linear props — the prefix rule can't see it, the
    # manifest can.
    m = _manifest({"Arch1": "LINEAR_LOW", "Arch2": "LINEAR_LOW"}, {"My Arch Row": ["Arch1", "Arch2"]})
    assert _is_linear("My Arch Row", m) is True
    score, findings = evaluate([_ins("Plasma", "My Arch Row")], _plan([0.5]), m)
    assert score < 100 and any("linear" in f.detail for f in findings)


def test_matrix_dominated_group_is_not_flagged_even_with_linear_name():
    # a group named SEM_ARCHES-ish the PREFIX rule would wrongly flag, but whose members are a
    # matrix surface — the manifest un-flags it.
    m = _manifest({"BigM": "2D_SURFACE"}, {"SEM_ARCHES_FAKE": ["BigM"]})
    assert _is_linear("SEM_ARCHES_FAKE", m) is False
    assert evaluate([_ins("Plasma", "SEM_ARCHES_FAKE")], _plan([0.5]), m)[0] == 100


def test_falls_back_to_prefix_without_manifest():
    # no manifest → the legacy prefix table gates exactly as before
    assert _is_linear("SEM_ARCHES") is True
    assert _is_linear("SEM_FOCAL") is False
    score, findings = evaluate([_ins("Plasma", "SEM_ARCHES")], _plan([0.5]))
    assert score < 100 and any("linear" in f.detail for f in findings)
