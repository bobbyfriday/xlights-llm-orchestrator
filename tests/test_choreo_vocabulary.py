"""F-E slice 6c — derived choreography vocabulary (design decision 11)."""

from __future__ import annotations

from pathlib import Path

from xlights_orchestrator.pipeline.semantic_groups import (
    DEFAULT_VOCAB,
    SEM_CANES,
    SEM_MINITREES,
    ChoreoVocabulary,
    derive_vocabulary,
)

FIX = Path(__file__).parent / "fixtures"


def _fake_manifest(props):
    from types import SimpleNamespace
    return SimpleNamespace(props=props)


def _p(name, role, x=0.5, band="MID", side="CENTER", nodes=50, focal=False):
    from types import SimpleNamespace
    return SimpleNamespace(id=name, role=role, nodes=nodes, focal=focal,
                           pos=SimpleNamespace(x=x, band=band, side=side))


def test_no_manifest_is_default_vocab():
    assert derive_vocabulary(None) == DEFAULT_VOCAB
    assert isinstance(DEFAULT_VOCAB, ChoreoVocabulary)


def test_empty_manifest_is_default_vocab():
    assert derive_vocabulary(_fake_manifest([])) == DEFAULT_VOCAB


def test_archless_layout_ranks_canes_and_minis_into_ring():
    # no arches; 4 canes spread wide + 3 mini trees → the ring should feature canes + minis
    props = (
        [_p(f"Cane{i}", "CANE", x=0.1 + 0.25 * i, nodes=60) for i in range(4)]
        + [_p(f"Mini{i}", "MINI_TREE", x=0.2 + 0.3 * i, nodes=80) for i in range(3)]
        + [_p("Flood", "FLOOD", nodes=3)]
    )
    vocab = derive_vocabulary(_fake_manifest(props))
    assert SEM_CANES in vocab.metric_ring
    assert SEM_MINITREES in vocab.metric_ring
    # arches are absent, so the ring is NOT the hardcoded arch-first tuple
    assert vocab.metric_ring != DEFAULT_VOCAB.metric_ring


def test_real_layout_manifest_reproduces_todays_constants():
    """SAFETY GATE: the derivation on the real layout must reproduce today's constants so the
    golden pipeline stays byte-identical when this ships as the default."""
    import json

    from xlights_core.knowledge.layout_classify import (
        apply_overrides,
        classify,
        derive_spatial,
        parse_props,
    )
    from xlights_core.knowledge.layout_manifest import build_manifest
    from xlights_core.knowledge.layout_semantics import build_sem_groups, layout_modes

    props = parse_props(FIX / "layout_real.xml")
    res = classify(props)
    apply_overrides(res, json.loads((FIX / "layout_real_overrides.json").read_text()))
    summary = derive_spatial(props)
    plan = build_sem_groups(props)
    m = build_manifest(res, summary, plan, modes=layout_modes(plan))
    vocab = derive_vocabulary(m)
    # the real layout has arches + canes + minis + snowflakes → the ring's top families match
    # today's constant METRIC_RING (arches, canes, minitrees, snowflakes), and beds/hero match.
    assert vocab.metric_ring == DEFAULT_VOCAB.metric_ring
    assert vocab.bed_preference == DEFAULT_VOCAB.bed_preference
    assert vocab.peak_broad == DEFAULT_VOCAB.peak_broad
    assert vocab.hero_group == DEFAULT_VOCAB.hero_group
    assert vocab.accent_groups == DEFAULT_VOCAB.accent_groups
