"""Golden/regression snapshot for the deterministic realize stage.

Drives `generate_instructions_from_brief` (what `xlo realize` runs) over a fixture creative brief
(`fixtures/creative_brief.json`: two labelled sections, a `fabric` block on the peak) and a rich,
fixed SongAnalysis so the deterministic layers actually fire — coverage trim, brightness/speed
settings, ensemble bed, peak fill, beat accents, the woven fabric, triggers, key-moment flashes,
feature-prop contrast, transitions. The produced instructions are snapshot to
`fixtures/golden_instructions.json` and compared exactly. (The realize stage then applies the
emitter's ≤4-layer budget and singing faces; those are covered by their own tests.)

The point is a SAFETY NET for refactors that are supposed to be behavior-preserving: if the
realized effects change, this fails. It does NOT assert the output is "correct" — only that it is
unchanged. `tests/test_fabric_stats.py` runs the fabric canary over the same snapshot.

Regenerate the snapshot intentionally after a real behavior change:

    XLO_REGEN_GOLDEN=1 pytest tests/test_golden_pipeline.py

Instructions are sorted by a canonical key before compare/write so the test is
robust to set-iteration order (PYTHONHASHSEED) and is purely about content.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from xlights_core.audio import (
    Beat,
    EnergyPoint,
    SectionInstrumentation,
    Segment,
    SongAnalysis,
    StemFeatures,
)
from xlights_orchestrator.pipeline.generate import generate_instructions_from_brief
from xlights_orchestrator.pipeline.state import State
from xlights_orchestrator.pipeline.weave import CARRIER_ROTATION
from xlights_orchestrator.show_plan import EffectInstruction, ShowPalette, ShowPlan

FIXTURES = Path(__file__).parent / "fixtures"
GOLDEN = FIXTURES / "golden_instructions.json"
BRIEF = FIXTURES / "creative_brief.json"

# Real SEM_ group vocabulary the deterministic layers key off (beds, accents, peak fill).
GROUPS = [
    "SEM_ALL", "SEM_BAND_GROUND", "SEM_FOCAL",
    "SEM_ARCHES", "SEM_CANES", "SEM_MINITREES",
    "SEM_SNOWFLAKES", "SEM_SPINNERS",
    "SEM_SIDE_LEFT", "SEM_SIDE_CENTER", "SEM_SIDE_RIGHT",
]

DURATION_S = 24.0
SORT_KEYS = ("section_index", "start_ms", "end_ms", "target", "effect_type", "look_id", "layer")


def _analysis() -> SongAnalysis:
    # 120 BPM → a beat every 0.5s; bar_position cycles 1..4 (downbeat every 4th).
    beats = [
        Beat(time=round(i * 0.5, 3), bar_position=(i % 4) + 1)
        for i in range(int(DURATION_S / 0.5))
    ]
    onsets = [round(i * 0.5, 3) for i in range(int(DURATION_S / 0.5))]
    drum_onsets = [round(i * 0.5, 3) for i in range(0, int(DURATION_S / 0.5), 2)]
    return SongAnalysis(
        path="song.mp3", duration_s=DURATION_S, sample_rate=44100,
        tempo_overall=120.0, key_overall="C major",
        beats=beats, onsets=onsets,
        segments=[Segment(start=0, end=12, segment_id="A"),
                  Segment(start=12, end=24, segment_id="B")],
        # a dense arc that BUILDS into the 12s boundary (0.25 → 0.85) so the Phase 3 transition pass
        # has real signal to read (a riser fires into the rising boundary).
        energy_arc=[EnergyPoint(time=t, rms=r) for t, r in (
            (0, 0.25), (4, 0.30), (8, 0.45), (10, 0.60), (11, 0.72),
            (12, 0.85), (16, 0.85), (20, 0.85), (24, 0.85))],
        stems=[StemFeatures(stem="drums", onsets=drum_onsets,
                            energy_arc=[EnergyPoint(time=0, rms=0.3),
                                        EnergyPoint(time=12, rms=0.9)])],
        section_instrumentation=[
            SectionInstrumentation(segment_id="A", start_ms=0, end_ms=12000,
                                   shares={"drums": 0.6, "bass": 0.4}, dominant=["drums"]),
            SectionInstrumentation(segment_id="B", start_ms=12000, end_ms=24000,
                                   shares={"drums": 0.7, "vocals": 0.3}, dominant=["drums"]),
        ],
    )


def _show_plan() -> ShowPlan:
    """The fixture creative brief (what Claude would write for this song)."""
    return ShowPlan.model_validate_json(BRIEF.read_text())


def _state(plan: ShowPlan) -> State:
    """The State `xlo realize` builds — no show folder → no manifest (DEFAULT_VOCAB), no models."""
    st = State(song_path="song.mp3")
    st.song_analysis = _analysis()
    st.show_plan = plan
    st.available_groups = list(GROUPS)
    return st


def _realize(plan: ShowPlan) -> list[EffectInstruction]:
    return generate_instructions_from_brief(_state(plan))


def _generate() -> list[dict]:
    dumped = [i.model_dump() for i in _realize(_show_plan())]
    return sorted(dumped, key=lambda d: tuple(str(d.get(k)) for k in SORT_KEYS))


def test_generate_matches_golden():
    produced = _generate()

    if os.environ.get("XLO_REGEN_GOLDEN") or not GOLDEN.exists():
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(json.dumps(produced, indent=1, sort_keys=True))
        if os.environ.get("XLO_REGEN_GOLDEN"):
            return  # explicit regen run: don't also assert against what we just wrote

    # Normalize the golden through the current schema so an additive, defaulted field doesn't
    # spuriously fail the compare. A real realization change still fails (values differ).
    expected = [EffectInstruction(**d).model_dump() for d in json.loads(GOLDEN.read_text())]
    assert produced == expected, (
        f"realize output changed ({len(produced)} effects vs {len(expected)} golden). "
        "If intentional, regenerate: XLO_REGEN_GOLDEN=1 pytest tests/test_golden_pipeline.py"
    )


def test_golden_is_deterministic():
    assert _generate() == _generate()                    # same brief + analysis → same show


def test_golden_is_non_trivial():
    """Guard the guard: the fixture must exercise the deterministic layers, not a bare pass.

    Section 0 (intensity 0.45 → `feature`) is realized SPARSER than section 1 (0.92 → `full`) — it
    withholds the weave fabric, composites, and VU. The `full` peak keeps the rich stack, and its
    `fabric` block directs the carrier."""
    produced = _generate()
    # weave + beds + accents + flashes → well more than the brief's base rows.
    assert len(produced) > 10
    assert any(i["section_index"] == 1 for i in produced)              # both sections produced effects
    assert any(i["section_index"] == 0 for i in produced)

    # (Exclude Phase-3 transition instructions — a riser is a boundary chase, not a weave carrier.)
    def _weave(s):
        return [i for i in produced
                if i["section_index"] == s and not i["extra_settings"].get("_XLO_TRANSITION")]

    def _weave_carriers(s):
        return {i["effect_type"] for i in _weave(s)} & set(CARRIER_ROTATION)
    assert _weave_carriers(1) == {"SingleStrand"}                      # the brief's fabric.carrier
    assert not _weave_carriers(0)                                      # the feature verse withholds it
    # the fabric's cell_beats=2 sets the carrier cell length (2 beats = 1000ms at 120 bpm); the
    # texture cell (Ripple: the brief names no cellable effect_types) expands beside it
    carrier_cells = [i for i in _weave(1) if i["effect_type"] == "SingleStrand"]
    assert carrier_cells and all(i["end_ms"] - i["start_ms"] == 1000 for i in carrier_cells)
    assert any(i["effect_type"] == "Ripple" for i in _weave(1))
    # Phase 3: a riser transition builds into the rising 12s boundary, tagged to the outgoing section
    risers = [i for i in produced if i["extra_settings"].get("_XLO_TRANSITION") == "riser"]
    assert risers and all(i["section_index"] == 0 for i in risers)
    # composite stack: the peak hero (SEM_FOCAL) carries a multi-effect blended stack (full only)
    focal = [i for i in produced if i["target"] == "SEM_FOCAL"]
    layers = sorted({i["layer"] for i in focal})
    assert layers[:2] == [0, 1]                                        # ≥2 stacked layers
    assert any(i["extra_settings"].get("T_CHOICE_LayerMethod") for i in focal if i["layer"] > 0)
    assert len({i["effect_type"] for i in focal}) >= 2                 # different effects combined
    # the energetic (peak) full section carries a music-reactive VU Meter; the quiet one does not
    vu = [i for i in produced if i["effect_type"] == "VU Meter"]
    assert vu and all(i["section_index"] == 1 for i in vu)
    # the climax key moment flashes at the drop (show-level, untagged)
    assert any(i["section_index"] is None and i["start_ms"] >= 12000 for i in produced)


def test_bed_does_not_occlude_a_feature_on_the_same_group():
    """A feature sharing the peak bed's group must blend Max (and the bed sits under it) so the
    opaque bed and the feature's black background don't cancel each other — the 2:15 Fireworks bug."""
    plan = ShowPlan(concept="c", palette=ShowPalette(colors=["Red", "Blue"]), sections=[
        {"start_ms": 0, "end_ms": 12000, "target_groups": ["SEM_ALL"],
         "effect_family": "Fireworks", "intensity": 0.95, "palette": ["Red", "Blue"]}])
    sem_all = [i for i in _realize(plan) if i.target == "SEM_ALL"]
    beds = [i for i in sem_all if i.effect_type in ("On", "Color Wash")]
    fw = [i for i in sem_all if i.effect_type == "Fireworks"]
    assert beds and fw, f"expected a bed + a Fireworks on SEM_ALL, got {[i.effect_type for i in sem_all]}"
    assert all(i.extra_settings.get("T_CHOICE_LayerMethod") == "Max" for i in fw)  # feature won't occlude
