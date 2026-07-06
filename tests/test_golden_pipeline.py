"""Golden/regression snapshot for the deterministic generate stage.

Drives `run_pipeline` end-to-end with fake (TestModel) agents and a rich, fixed
SongAnalysis so the deterministic layers actually fire — coverage trim, brightness/
speed settings, ensemble bed, peak fill, beat accents, weave expansion, triggers,
key-moment flashes, feature-prop contrast. The produced `st.instructions` are snapshot
to `fixtures/golden_instructions.json` and compared exactly.

The point is a SAFETY NET for refactors that are supposed to be behavior-preserving
(e.g. splitting run.py): if the generated effects change, this fails. It does NOT
assert the output is "correct" — only that it is unchanged.

Regenerate the snapshot intentionally after a real behavior change:

    XLO_REGEN_GOLDEN=1 pytest tests/test_golden_pipeline.py

Instructions are sorted by a canonical key before compare/write so the test is
robust to set-iteration order (PYTHONHASHSEED) and is purely about content.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from xlights_orchestrator.pipeline import run_pipeline
from xlights_orchestrator.pipeline.weave import CARRIER_ROTATION
from xlights_orchestrator.show_plan import (
    CellRecipe,
    EffectInstruction,
    KeyMoment,
    SectionEffects,
    SectionWeave,
    ShowPalette,
    ShowPlan,
)
from xlights_core.audio import (
    Beat,
    EnergyPoint,
    SectionInstrumentation,
    Segment,
    SongAnalysis,
    StemFeatures,
)

GOLDEN = Path(__file__).parent / "fixtures" / "golden_instructions.json"

# Real SEM_ group vocabulary the deterministic layers key off (beds, accents, peak fill).
GROUPS = [
    "SEM_ALL", "SEM_BAND_GROUND", "SEM_FOCAL",
    "SEM_ARCHES", "SEM_CANES", "SEM_MINITREES",
    "SEM_SNOWFLAKES", "SEM_SPINNERS",
    "SEM_SIDE_LEFT", "SEM_SIDE_CENTER", "SEM_SIDE_RIGHT",
]

DURATION_S = 24.0
SORT_KEYS = ("section_index", "start_ms", "end_ms", "target", "effect_type", "look_id", "layer")


def _run(coro):
    return asyncio.run(coro)


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
        energy_arc=[EnergyPoint(time=0, rms=0.25), EnergyPoint(time=12, rms=0.85)],
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
    return ShowPlan(
        concept="golden fixture",
        palette=ShowPalette(name="test", colors=["Red", "Green", "Blue"]),
        sections=[
            {"start_ms": 0, "end_ms": 12000, "target_groups": ["SEM_ARCHES", "SEM_CANES"],
             "effect_family": "On", "intensity": 0.45, "palette": ["Red", "Green"],
             "pulse_groups": ["SEM_ARCHES"], "pulse_on": "beat"},
            {"start_ms": 12000, "end_ms": 24000, "target_groups": ["SEM_ALL", "SEM_FOCAL"],
             "effect_family": "On", "intensity": 0.92, "palette": ["Blue", "Red"],
             "pulse_groups": ["SEM_CANES"], "pulse_on": "onset"},
        ],
        key_moments=[KeyMoment(at_ms=12000, kind="climax", treatment="the drop")],
    )


def _section_effects() -> SectionEffects:
    return SectionEffects(
        instructions=[EffectInstruction(
            target="SEM_ARCHES", effect_type="On", look_id="On#0", start_ms=0, end_ms=12000)],
        weave=SectionWeave(cells=[
            CellRecipe(effect_type="On", role="carrier", groups=["SEM_ARCHES", "SEM_CANES"],
                       cell_beats=1, alternation="chase", direction="ltr"),
            CellRecipe(effect_type="Twinkle", role="texture", groups=["SEM_MINITREES"],
                       cell_beats=2, alternation="all"),
        ]),
    )


def _test_agent(output):
    from pydantic_ai import Agent
    from pydantic_ai.models.test import TestModel
    return Agent(TestModel(custom_output_args=output.model_dump()),
                 output_type=type(output), system_prompt="")


class _FakeClient:
    """Only get_group_names; targetable_groups falls back to the full list when probing fails."""

    def __init__(self, groups):
        self._groups = groups

    async def get_group_names(self):
        return list(self._groups)

    async def get_show_folder(self):
        raise RuntimeError("no show folder in the hermetic fixture")


def _generate(tmp_path) -> list[dict]:
    song = tmp_path / "song.mp3"
    song.write_bytes(b"fake-audio-bytes")

    async def fake_emitter(client, instructions, *, duration_secs, **kw):
        return {"placed": [i.model_dump() for i in instructions], "skipped": [], "rendered": True}

    st = _run(run_pipeline(
        str(song), client=_FakeClient(GROUPS),
        director=_test_agent(_show_plan()), generator=_test_agent(_section_effects()),
        analyze=lambda p: _analysis(), interpret=lambda p, sa: _noop_brief(),
        emitter=fake_emitter, use_cache=False, stems=False, timing_tracks=False,
    ))
    dumped = [i.model_dump() for i in st.instructions]
    return sorted(dumped, key=lambda d: tuple(str(d.get(k)) for k in SORT_KEYS))


async def _noop_brief():
    from xlights_orchestrator.music_brief import LabeledSection, MusicBrief
    return MusicBrief(sections=[
        LabeledSection(start_ms=0, end_ms=12000, label="build", intensity=0.45),
        LabeledSection(start_ms=12000, end_ms=24000, label="drop", intensity=0.92)])


def test_generate_matches_golden(tmp_path, monkeypatch):
    monkeypatch.setenv("XLO_CACHE_DIR", str(tmp_path / "cache"))
    produced = _generate(tmp_path)

    if os.environ.get("XLO_REGEN_GOLDEN") or not GOLDEN.exists():
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(json.dumps(produced, indent=1, sort_keys=True))
        if os.environ.get("XLO_REGEN_GOLDEN"):
            return  # explicit regen run: don't also assert against what we just wrote

    # Normalize the golden through the current schema so an additive, defaulted field (e.g. F-B's
    # direct_settings="") doesn't spuriously fail the compare: the fixture stays byte-identical, and
    # nothing here emits direct instructions. A real generation change still fails (values differ).
    expected = [EffectInstruction(**d).model_dump() for d in json.loads(GOLDEN.read_text())]
    assert produced == expected, (
        f"generate output changed ({len(produced)} effects vs {len(expected)} golden). "
        "If intentional, regenerate: XLO_REGEN_GOLDEN=1 pytest tests/test_golden_pipeline.py"
    )


def test_golden_is_non_trivial(tmp_path, monkeypatch):
    """Guard the guard: the fixture must exercise the deterministic layers, not a bare pass."""
    monkeypatch.setenv("XLO_CACHE_DIR", str(tmp_path / "cache"))
    produced = _generate(tmp_path)
    # weave + beds + accents + flashes → well more than the lone generator instruction.
    assert len(produced) > 10
    assert any(i["effect_type"] == "Twinkle" for i in produced)        # weave texture cell expanded
    assert any(i["section_index"] == 1 for i in produced)              # both sections produced effects
    # carrier rotation: the two sections use DIFFERENT carrier effects (variety, not all SingleStrand)
    carrier_by_section = {
        s: {i["effect_type"] for i in produced if i["section_index"] == s} & set(CARRIER_ROTATION)
        for s in (0, 1)
    }
    assert carrier_by_section[0] != carrier_by_section[1]              # rotated, not identical
    assert len({t for ts in carrier_by_section.values() for t in ts}) >= 2
    # composite stack: the peak hero (SEM_FOCAL) carries a multi-effect blended stack
    focal = [i for i in produced if i["target"] == "SEM_FOCAL"]
    layers = sorted({i["layer"] for i in focal})
    assert layers[:2] == [0, 1]                                        # ≥2 stacked layers
    assert any(i["extra_settings"].get("T_CHOICE_LayerMethod") for i in focal if i["layer"] > 0)
    assert len({i["effect_type"] for i in focal}) >= 2                 # different effects combined
    # the energetic (peak) section carries a music-reactive VU Meter; the quiet one does not
    vu = [i for i in produced if i["effect_type"] == "VU Meter"]
    assert vu and all(i["section_index"] == 1 for i in vu)


def test_bed_does_not_occlude_a_feature_on_the_same_group(tmp_path, monkeypatch):
    """A feature sharing the peak bed's group must blend Max (and the bed sits under it) so the
    opaque bed and the feature's black background don't cancel each other — the 2:15 Fireworks bug."""
    monkeypatch.setenv("XLO_CACHE_DIR", str(tmp_path / "cache"))
    song = tmp_path / "s.mp3"; song.write_bytes(b"x")
    plan = ShowPlan(concept="c", palette=ShowPalette(colors=["Red", "Blue"]), sections=[
        {"start_ms": 0, "end_ms": 12000, "target_groups": ["SEM_ALL"],
         "effect_family": "Fireworks", "intensity": 0.95, "palette": ["Red", "Blue"]}])
    se = SectionEffects(instructions=[EffectInstruction(
        target="SEM_ALL", effect_type="Fireworks", look_id="Fireworks#0", start_ms=0, end_ms=12000)])

    async def emit(client, instructions, *, duration_secs, **kw):
        return {"placed": [], "skipped": [], "rendered": True}
    st = _run(run_pipeline(str(song), client=_FakeClient(GROUPS),
        director=_test_agent(plan), generator=_test_agent(se),
        analyze=lambda p: _analysis(), interpret=lambda p, sa: _noop_brief(),
        emitter=emit, use_cache=False, stems=False, timing_tracks=False))
    sem_all = [i for i in st.instructions if i.target == "SEM_ALL"]
    beds = [i for i in sem_all if i.effect_type in ("On", "Color Wash")]
    fw = [i for i in sem_all if i.effect_type == "Fireworks"]
    assert beds and fw, f"expected a bed + a Fireworks on SEM_ALL, got {[i.effect_type for i in sem_all]}"
    assert all(i.extra_settings.get("T_CHOICE_LayerMethod") == "Max" for i in fw)  # feature won't occlude
