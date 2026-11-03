"""Big-hit rings: one slow Shockwave propagating across the whole display on the strongest drum
hits of an energetic section (see `tuning.BIG_HIT_*`). A show-level gesture over the section's
stack: `on_top`, blended `Max`, rendered `Per Preview` so ONE ring crosses the whole-display
group buffer rather than a ring per prop.
"""

from __future__ import annotations

from ..show_plan import EffectInstruction, SectionPlan
from .catalog import candidate_look_ids
from .semantic_groups import FULL_DISPLAY
from .tuning import (
    BIG_HIT_BEATS, BIG_HIT_MAX_PER_SECTION, BIG_HIT_MIN_INTENSITY, BIG_HIT_MIN_MAG,
    BIG_HIT_MIN_SPACING_BARS, BIG_HIT_MS_RANGE, BIG_HIT_RING, BIG_HIT_SNAP_MS,
)

_RING_LOOK = "Shockwave#10"            # the prop-ring look: Blend Edges, Accel 0, CenterY 50 frozen


def _beat_ms(rhythm: dict) -> float:
    beats = sorted(rhythm.get("beats_ms") or [])
    if len(beats) >= 2:
        return (beats[-1] - beats[0]) / (len(beats) - 1)
    tempo = rhythm.get("tempo") or 120.0
    return 60000.0 / float(tempo)


def ring_duration_ms(rhythm: dict) -> int:
    lo, hi = BIG_HIT_MS_RANGE
    return int(min(hi, max(lo, BIG_HIT_BEATS * _beat_ms(rhythm))))


def big_hit_times(section: SectionPlan, rhythm: dict, intensity: float) -> list[int]:
    """The ring moments (ms): the strongest drum onsets at or above `BIG_HIT_MIN_MAG`, snapped to
    the nearest beat within `BIG_HIT_SNAP_MS`, at most one per `BIG_HIT_MIN_SPACING_BARS` bars,
    at most `BIG_HIT_MAX_PER_SECTION`, strongest first then sorted. Empty below the energy gate."""
    if intensity < BIG_HIT_MIN_INTENSITY:
        return []
    onsets = rhythm.get("onsets_by_stem", {}).get("drums") or []
    mags = rhythm.get("onset_mag_by_stem", {}).get("drums") or []
    if not onsets or len(mags) != len(onsets):
        return []
    beats = sorted(rhythm.get("beats_ms") or [])
    bpb = int(rhythm.get("beats_per_bar") or 4)
    spacing = BIG_HIT_MIN_SPACING_BARS * bpb * _beat_ms(rhythm)

    def snap(t: int) -> int:
        if not beats:
            return t
        b = min(beats, key=lambda x: abs(x - t))
        return b if abs(b - t) <= BIG_HIT_SNAP_MS else t

    strong = sorted(((m, t) for t, m in zip(onsets, mags) if m >= BIG_HIT_MIN_MAG),
                    key=lambda mt: (-mt[0], mt[1]))
    chosen: list[int] = []
    for _m, t in strong:
        ts = snap(int(t))
        if ts < section.start_ms or ts >= section.end_ms:
            continue
        if any(abs(ts - c) < spacing for c in chosen):
            continue
        chosen.append(ts)
        if len(chosen) >= BIG_HIT_MAX_PER_SECTION:
            break
    return sorted(chosen)


def place_big_hit_rings(section: SectionPlan, rhythm: dict, intensity: float,
                        available_groups: list[str]) -> list[EffectInstruction]:
    """One whole-display ring per big hit, white, `on_top`, blended `Max`, `Per Preview`."""
    if FULL_DISPLAY not in (available_groups or []) or not candidate_look_ids("Shockwave"):
        return []
    looks = candidate_look_ids("Shockwave", limit=10_000)
    look = _RING_LOOK if _RING_LOOK in looks else looks[0]
    dur = ring_duration_ms(rhythm)
    out: list[EffectInstruction] = []
    for t in big_hit_times(section, rhythm, intensity):
        end = min(t + dur, section.end_ms)
        if end - t < BIG_HIT_MS_RANGE[0] // 2:
            continue
        extra = dict(BIG_HIT_RING)
        extra["T_CHOICE_LayerMethod"] = "Max"
        out.append(EffectInstruction(
            target=FULL_DISPLAY, effect_type="Shockwave", look_id=look, palette_colors=["white"],
            render_style="Per Preview", extra_settings=extra, start_ms=int(t), end_ms=int(end),
            on_top=True, source="hits"))
    return out
