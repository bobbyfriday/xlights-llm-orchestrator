"""Typed pipeline state (the blackboard)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from xlights_core.audio import SongAnalysis

from ..music_brief import MusicBrief
from ..show_plan import EffectInstruction, ShowPlan


@dataclass
class State:
    song_path: str
    song_analysis: SongAnalysis | None = None
    available_groups: list[str] = field(default_factory=list)
    placeable_types: list[str] = field(default_factory=list)
    music_brief: MusicBrief | None = None
    show_plan: ShowPlan | None = None
    instructions: list[EffectInstruction] = field(default_factory=list)
    applied: dict[str, Any] | None = None
