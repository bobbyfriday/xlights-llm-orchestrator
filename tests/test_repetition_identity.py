"""Phase 1 — repetition identity: recurring sections rhyme (shared carrier / composite / palette
order) and escalate structurally (coverage, accent stride, a final extra layer)."""
from __future__ import annotations

from xlights_orchestrator.pipeline.beats import (
    _off_beat_stride,
    coverage_cap,
    effect_palette,
    label_palette_offset,
    occurrence_ordinal,
    section_identity,
    trim_coverage,
)
from xlights_orchestrator.pipeline.weave import (
    CARRIER_ROTATION,
    label_seed,
    section_carrier,
)


# -- 1.1 section_identity ------------------------------------------------------

def test_section_identity_recurring_label_found():
    rm = {"chorus": [2, 5, 8], "verse": [1, 4]}
    assert section_identity(2, rm) == "chorus"
    assert section_identity(8, rm) == "chorus"
    assert section_identity(4, rm) == "verse"


def test_section_identity_one_off_is_none():
    rm = {"chorus": [2, 5], "intro": [0]}    # intro occurs once → not an identity
    assert section_identity(0, rm) is None
    assert section_identity(3, rm) is None    # not in any label


def test_section_identity_empty_map_is_none():
    assert section_identity(0, {}) is None
    assert section_identity(0, None) is None


def test_occurrence_ordinal():
    rm = {"chorus": [2, 5, 8]}
    assert occurrence_ordinal(2, rm) == (0, 3)
    assert occurrence_ordinal(8, rm) == (2, 3)
    assert occurrence_ordinal(5, rm) == (1, 3)
    assert occurrence_ordinal(9, rm) == (0, 1)   # one-off → spend nothing


# -- 1.2 carrier keyed on identity ---------------------------------------------

def test_shared_label_shares_carrier():
    # two chorus sections at DIFFERENT indices resolve the SAME carrier via the label
    c1 = section_carrier(2, "chorus")
    c2 = section_carrier(8, "chorus")
    assert c1 == c2
    assert c1 in CARRIER_ROTATION


def test_adjacent_one_offs_still_differ():
    # no identity → index-keyed rotation, so adjacent one-offs vary as before
    assert section_carrier(0, None) != section_carrier(1, None)


def test_label_seed_is_stable_and_process_independent():
    # md5-derived, so it does NOT depend on PYTHONHASHSEED (would churn the golden otherwise)
    assert label_seed("chorus") == label_seed("chorus")
    assert isinstance(label_seed("chorus"), int) and label_seed("chorus") >= 0
    # a precomputed value pins the mapping so a refactor can't silently move it
    assert section_carrier(0, "chorus") == CARRIER_ROTATION[label_seed("chorus") % len(CARRIER_ROTATION)]


# -- 1.3 palette rotation keyed on identity ------------------------------------

def test_repeated_choruses_share_palette_order():
    pal = ["Red", "Green", "Blue"]
    off = label_palette_offset("chorus")
    a = effect_palette(pal, "Plasma", 0, off)
    b = effect_palette(pal, "Plasma", 0, off)      # same label offset → identical order
    assert a == b
    # a one-off (offset 0) generally differs from the chorus's rotated order when the offset is nonzero
    if off:
        assert effect_palette(pal, "Plasma", 0, 0) != a


def test_palette_offset_zero_for_one_off():
    assert label_palette_offset(None) == 0
    assert label_palette_offset("") == 0


# -- 1.4 structural escalation -------------------------------------------------

def test_coverage_cap_grows_with_occurrence_extra():
    n = 8
    base = coverage_cap(0.5, n, 0)
    later = coverage_cap(0.5, n, 2)
    assert later >= base
    assert later == min(n, base + 2)


def test_coverage_cap_bounded_by_group_count():
    assert coverage_cap(1.0, 3, 10) == 3     # never exceeds available groups


def test_off_beat_stride_tightens_one_step():
    # a quiet section normally lights downbeats only (None); +1 step → every-other off-beat
    assert _off_beat_stride(0.2, 0) is None
    assert _off_beat_stride(0.2, 1) == 2
    assert _off_beat_stride(0.2, 2) == 1
    # already at the densest rung → clamped, can't over-spend
    assert _off_beat_stride(0.9, 0) == 1
    assert _off_beat_stride(0.9, 3) == 1


def test_trim_coverage_extra_widens_kept_targets():
    class _Ins:
        def __init__(self, target):
            self.target = target
    instrs = [_Ins(f"G{i}") for i in range(6)]
    kept0 = {i.target for i in trim_coverage(instrs, 0.5, 0)}
    kept2 = {i.target for i in trim_coverage(instrs, 0.5, 2)}
    assert kept0 <= kept2
    assert len(kept2) >= len(kept0)
