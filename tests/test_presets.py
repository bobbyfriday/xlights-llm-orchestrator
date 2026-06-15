"""Tests for the effect-preset library.

Library/catalog tests run against the committed catalog (hermetic). Mining tests run
against the real show folder and skip if it's absent.
"""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from xlights_core.knowledge import (
    ASSET_BOUND_TYPES,
    KnobValueError,
    get_library,
)
from xlights_core.knowledge.settings import (
    classify_value_curve,
    parse_settings,
    serialize_settings,
)
from xlights_core.knowledge.validators import validate_knob_value
from xlights_core.knowledge.models import Knob

CORPUS = Path("/Users/rob/xlights")
needs_corpus = pytest.mark.skipif(not CORPUS.exists(), reason="show folder not present")

lib = get_library()  # committed catalog (hermetic)


# -- committed-catalog / API tests --------------------------------------------

def test_asset_bound_types_excluded():
    types = set(lib.list_effect_types())
    assert types.isdisjoint(ASSET_BOUND_TYPES)
    assert "SingleStrand" in types and "Spirals" in types


def test_get_looks_have_knobs_and_provenance():
    looks = lib.get_looks("Shockwave")
    assert looks, "expected Shockwave looks"
    for lk in looks:
        assert lk.source_versions, "every look records source versions"
        assert lk.key_order, "every look has a canonical key order"


def test_assemble_defaults_is_well_formed():
    look = lib.get_looks("Shockwave")[0]
    s = lib.assemble(look)
    keys = {k for k, _ in parse_settings(s)}
    assert keys == set(look.key_order)
    assert "#" not in s and "C_BUTTON" not in s  # color stays in palettes


def test_assemble_with_chosen_knob():
    # find a numeric slider knob and set an in-range value
    for look in lib.get_looks("Shockwave"):
        for knob in look.knobs:
            if knob.numeric and knob.min is not None and knob.min != knob.max:
                mid = str(int((knob.min + knob.max) / 2))
                out = lib.assemble(look, {knob.key: mid})
                assert f"{knob.key}={mid}" in out
                return
    pytest.skip("no numeric slider knob found")


def test_decoupling_no_color_in_looks():
    for looks in (lib.get_looks(t) for t in lib.list_effect_types()):
        for lk in looks:
            blob = "".join(lk.frozen_base.values()) + "".join(
                "".join(k.options or []) for k in lk.knobs
            )
            assert "#" not in blob and "C_BUTTON" not in blob


def test_palettes_filter_and_tags():
    warm = lib.get_palettes(tag="warm", limit=5)
    assert all("warm" in p.tags for p in warm)
    assert all(p.colors for p in lib.get_palettes(limit=3))


# -- validator (per-knob constraint) tests ------------------------------------

def test_slider_range_enforced():
    knob = Knob(key="E_SLIDER_X", kind="slider", numeric=True, min=0, max=100, default="50")
    validate_knob_value(knob, "50")            # in range OK
    with pytest.raises(KnobValueError):
        validate_knob_value(knob, "150")       # out of range


def test_categorical_membership_enforced():
    knob = Knob(key="E_CHOICE_X", kind="choice", options=["A", "B"], default="A")
    validate_knob_value(knob, "B")
    with pytest.raises(KnobValueError):
        validate_knob_value(knob, "C")         # never observed


def test_value_curve_is_categorical_only():
    obs = "Active=TRUE|Type=Ramp|Min=0|Max=100|P1=0|P2=100|RV=FALSE|"
    knob = Knob(key="E_VALUECURVE_X", kind="valuecurve", options=[obs],
                vc_class="parametric", default=obs)
    validate_knob_value(knob, obs)             # observed OK
    with pytest.raises(KnobValueError):        # synthesis rejected
        validate_knob_value(knob, "Active=TRUE|Type=Sine|Min=0|Max=50|")


def test_value_curve_classification():
    assert classify_value_curve("Active=TRUE|Type=Ramp|Min=0|Max=1|") == "parametric"
    assert classify_value_curve("Active=TRUE|Type=Custom|Values=0:0;1:1|") == "custom"
    assert classify_value_curve("Active=TRUE|Type=Timing Track Fade Fixed|") == "timing-track"


def test_no_timing_track_curves_in_catalog():
    for t in lib.list_effect_types():
        for lk in lib.get_looks(t):
            for knob in lk.knobs:
                if knob.kind == "valuecurve":
                    for opt in knob.options or []:
                        assert classify_value_curve(opt) != "timing-track"


# -- mining tests (need the real corpus) --------------------------------------

@needs_corpus
def test_mining_excludes_tool_and_backup_and_assets():
    from xlights_core.knowledge.xsq_extractor import build_catalog, iter_corpus

    files = list(iter_corpus(CORPUS))
    assert files, "expected community files"
    assert all("Backup" not in f.parts for f in files)

    catalog, skipped = build_catalog(CORPUS)
    # community sequences predate the 2026 auto-sequencer output
    assert all(not v.startswith("2026") for v in catalog.meta["xlights_versions"])
    assert set(catalog.looks_by_type).isdisjoint(ASSET_BOUND_TYPES)
    assert skipped.get("asset_type", 0) > 0
    assert skipped.get("timing_track_vc", 0) > 0


@needs_corpus
def test_settings_roundtrip_lossless():
    # every EffectDB settings string round-trips through parse/serialize (key/value equiv)
    from xlights_core.knowledge.xsq_extractor import iter_corpus

    checked = 0
    for path in iter_corpus(CORPUS):
        root = ET.parse(path).getroot()
        edb = root.find("EffectDB")
        if edb is None:
            continue
        for e in edb.findall("Effect"):
            s = (e.text or "").strip()
            pairs = parse_settings(s)
            assert parse_settings(serialize_settings(pairs)) == pairs
            checked += 1
    assert checked > 1000
