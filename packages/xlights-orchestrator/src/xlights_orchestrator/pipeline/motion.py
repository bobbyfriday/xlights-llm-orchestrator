"""Direction variety: directional effects turn with the music instead of sweeping one way all show.

Before this pass a directional effect kept whatever direction its catalog look froze (the verse
Bars on the tree "expanded" for the whole section; every Pinwheel spun one way; Meteors always
rose). `vary_directions` gives every directional instruction in a section a direction from the
section's beat grid:

- **Cadence** (`fabric.direction_change`): `hold` (one direction for the section), `phrase` (flip
  every 4 bars), `bar` (flip on every bar), `beat` (flip every beat). Blank → by energy: the peak
  flips each bar; quiet sections (gesture/rest, or intensity < 0.35) flip each phrase; the rest
  flip each bar. Each effect class has a floor: a sweep needs 2 beats to cross a prop, Meteors a
  phrase to fall. Spins (Spirals, Pinwheel, Ripple, Butterfly) reverse on the cadence itself — on
  every downbeat under `bar`. A spiral's spin is the sign of its Movement (`weave.apply_direction`).
- **Axis**: under `bar`/`beat` the KIND of motion advances each phrase (left/right → up/down →
  expand/compress, as far as the effect's knobs reach); under `phrase` it advances every 2 phrases.
  Up/down is only used on props with height (not arches, canes, outlines, paths, icicles, sides).
  The hero runs one axis ahead of the yard, so the tree and the rhythm props move differently.
- **Mirror** (`fabric.mirror`, default on): right-hand groups take the opposite horizontal
  direction (and the opposite spin), so the two sides meet and part.
- **Stacks** of the same spinning effect on one target (SC-02's counter-rotating spirals) turn
  together but stay opposed: each higher layer takes the opposite spin of the one below.
- **Spiral shape**: Spirals also change strand count, thickness and twist each phrase (ribbons ↔
  candy-cane stripes), stacked layers offset by one shape and twisted the other
  way, so a spiral never settles into fat, barely-slanted bars.

Long rows are cut on the cadence's beat boundaries so they can turn (cell-able effects only;
phrase-class effects like Fill and Fan keep their length and just pick a direction). Woven cells
are already beat-sized and are never cut. An instruction whose direction is already chosen
(`weave.has_direction`: a composite's counter-phase, an explicit chase pair) is left alone.
Deterministic: the seed is the section's label (recurring sections rhyme) else its index.
"""

from __future__ import annotations

from bisect import bisect_right

from ..show_plan import DIRECTION_CHANGES, EffectInstruction, SectionPlan
from .effect_meta import CHASE_FAMILY, DIRECTION_KNOBS, DURATION_CELLABLE
from .semantic_groups import HERO_GROUP
from .weave import ROTATIONAL_EFFECTS, apply_direction, has_direction

PHRASE_BARS = 4                 # bars per phrase: the axis-change period
_SWEEP_MIN_BEATS = 2            # a sweep needs ~2 beats to cross a prop; flipping faster jitters
_QUIET_INTENSITY = 0.35         # below this a section turns per phrase, not per bar
_SLIVER = 0.25                  # a cut closer than this fraction of a unit to an edge is skipped
# The kinds of motion, in the order a section walks them. `bounce` is a native one-value axis.
_AXES: tuple[tuple[str, ...], ...] = (("ltr", "rtl"), ("up", "down"),
                                       ("center_out", "center_in"), ("bounce",))
# Line-like groups: up/down across their canvas reads as a flash, not a motion.
_FLAT_GROUPS = ("SEM_ARCHES", "SEM_CANES", "SEM_OUTLINE", "SEM_PATH", "SEM_ICICLES", "SEM_SIDE_")
_IN_KEYS = ("T_TEXTCTRL_Fadein", "T_CHOICE_In_Transition", "T_SLIDER_In_Transition")
_OUT_KEYS = ("T_TEXTCTRL_Fadeout", "T_CHOICE_Out_Transition", "T_SLIDER_Out_Transition")
# Spiral shapes walked per phrase: (palette repeats, strand thickness %, twist). Twist is
# E_SLIDER_Spirals_Rotation, the stripes' slant over the buffer height; the looks' 20 barely slants
# on a group canvas, which with 50% thickness reads as fat vertical bars.
# At most 2 repeats: with a 4-color palette that is 8 stripes a layer, and a counter-rotating
# pair doubles it — 3 repeats (12 + 12 crossing stripes) read as noise.
SPIRAL_SHAPES: tuple[tuple[int, int, int], ...] = (
    (2, 25, 200),           # ribbons
    (1, 40, 260),           # candy cane: a few wide, steep stripes
)
_SPIRAL_KEYS = ("E_SLIDER_Spirals_Count", "E_SLIDER_Spirals_Thickness", "E_SLIDER_Spirals_Rotation")


def effect_axes(effect_type: str, target: str = "") -> list[tuple[str, ...]]:
    """The motion axes the effect's direction knobs reach, in walk order; `[]` when undirected."""
    table = DIRECTION_KNOBS.get(effect_type) or {}
    flat = target.startswith(_FLAT_GROUPS)
    out: list[tuple[str, ...]] = []
    for axis in _AXES:
        if flat and axis == ("up", "down"):
            continue
        vals = tuple(v for v in axis if v in table)
        if vals:
            out.append(vals)
    return out


def resolve_direction_change(section: SectionPlan, intensity: float, treatment: str,
                             is_peak: bool) -> str:
    """The section's cadence: the brief's `fabric.direction_change`, else by energy."""
    fabric = getattr(section, "fabric", None)
    named = getattr(fabric, "direction_change", "") if fabric is not None else ""
    if named in DIRECTION_CHANGES:
        return named
    if is_peak:
        return "bar"
    if treatment in ("gesture", "rest") or intensity < _QUIET_INTENSITY:
        return "phrase"
    return "bar"


def _unit_beats(change: str, effect_type: str, bpb: int) -> int:
    """Beats between turns for this effect at this cadence (0 = hold), after the class floor.
    Spins reverse on the cadence itself (on every downbeat under `bar`)."""
    if change == "hold":
        return 0
    phrase = PHRASE_BARS * bpb
    unit = {"phrase": phrase, "bar": bpb, "beat": 1}[change]
    if effect_type == "Meteors":                       # meteors need the phrase to travel
        return max(unit, phrase)
    if effect_type in CHASE_FAMILY:
        return max(unit, _SWEEP_MIN_BEATS)
    return unit


class _Grid:
    """The section's beat grid, counted from the section start (the brief's downbeat), so a turn
    lands on the section's own bar lines even where the tracker's bar phase is off."""

    def __init__(self, section: SectionPlan, rhythm: dict, bpb: int, bar_ms: float):
        beats = sorted(b for b in (rhythm.get("beats_ms") or [])
                       if section.start_ms <= b < section.end_ms)
        if len(beats) < 2:                             # no tracked beats: a tempo grid
            step = max(1.0, bar_ms / bpb)
            n = int((section.end_ms - section.start_ms) / step) + 1
            beats = [int(section.start_ms + k * step) for k in range(n)]
        self.beats = beats
        self.bpb = bpb

    def index(self, t: float) -> int:
        return max(0, bisect_right(self.beats, t) - 1)

    def cuts(self, unit: int, start: int, end: int) -> list[int]:
        """Turn points strictly inside (start, end), skipping slivers near either edge."""
        if unit <= 0:
            return []
        span = (self.beats[min(unit, len(self.beats) - 1)] - self.beats[0]) or 1
        margin = span * _SLIVER
        return [b for b in self.beats[unit::unit] if start + margin < b < end - margin]


def _pick(axes: list[tuple[str, ...]], change: str, unit: int, grid: _Grid, t: float,
          seed: int, offset: int, mirrored: bool) -> str:
    beat = grid.index(t)
    phrase = beat // (grid.bpb * PHRASE_BARS)
    if change == "hold" or unit <= 0:
        axis_i, pol = seed + offset, seed // max(1, len(axes))
    elif change == "phrase" or unit >= grid.bpb * PHRASE_BARS:
        slot = beat // max(1, unit)
        axis_i, pol = seed + offset + slot // 2, slot
    else:
        axis_i, pol = seed + offset + phrase, beat // unit
    axis = axes[axis_i % len(axes)]
    if mirrored and axis == ("ltr", "rtl"):
        pol += 1
    return axis[pol % len(axis)]


def _split(ins: EffectInstruction, cuts: list[int]) -> list[EffectInstruction]:
    """Cut an instruction at `cuts`; the entrance stays on the first piece, the exit on the last."""
    if not cuts:
        return [ins]
    edges = [ins.start_ms, *cuts, ins.end_ms]
    pieces: list[EffectInstruction] = []
    for k, (a, b) in enumerate(zip(edges, edges[1:])):
        p = ins.model_copy(deep=True)
        p.start_ms, p.end_ms = int(a), int(b)
        drop = (_IN_KEYS if k > 0 else ()) + (_OUT_KEYS if k < len(edges) - 2 else ())
        for key in [key for key in p.extra_settings if key.startswith(drop)] if drop else []:
            del p.extra_settings[key]
        pieces.append(p)
    return pieces


def _stack_rank(ins: EffectInstruction, instrs: list[EffectInstruction]) -> int:
    """How many same-type spinning layers sit under this one on its target (0 = the bottom or
    alone): each rank spins opposite the one below."""
    if ins.effect_type not in ROTATIONAL_EFFECTS:
        return 0
    order = {id(o): k for k, o in enumerate(instrs)}
    return sum(1 for o in instrs
               if o is not ins and o.target == ins.target and o.effect_type == ins.effect_type
               and o.start_ms < ins.end_ms and ins.start_ms < o.end_ms
               and (o.layer, order[id(o)]) < (ins.layer, order[id(ins)]))


def _spiral_shape(ins: EffectInstruction, grid: _Grid, seed: int, rank: int) -> None:
    """Set a Spirals piece's strand count, thickness and twist for its phrase (see SPIRAL_SHAPES),
    unless any of them is already set (an explicit look choice wins)."""
    ex = ins.extra_settings
    if any(k in ex or "E_VALUECURVE_" + k.split("_", 2)[2] in ex for k in _SPIRAL_KEYS):
        return
    phrase = grid.index((ins.start_ms + ins.end_ms) / 2) // (grid.bpb * PHRASE_BARS)
    count, thick, twist = SPIRAL_SHAPES[(seed + phrase + rank) % len(SPIRAL_SHAPES)]
    ex["E_SLIDER_Spirals_Count"] = str(count)
    ex["E_SLIDER_Spirals_Thickness"] = str(thick)
    ex["E_SLIDER_Spirals_Rotation"] = str(-twist if rank % 2 else twist)


def vary_directions(instrs: list[EffectInstruction], section: SectionPlan, rhythm: dict, *,
                    bar_ms: float, intensity: float, treatment: str, is_peak: bool,
                    seed: int) -> list[EffectInstruction]:
    """The section's instructions with directional effects turned on its beat grid (see module
    doc). Order is preserved (a cut row's pieces take its place); undirected rows pass through."""
    bpb = int(rhythm.get("beats_per_bar") or 4)
    grid = _Grid(section, rhythm, bpb, bar_ms)
    change = resolve_direction_change(section, intensity, treatment, is_peak)
    fabric = getattr(section, "fabric", None)
    mirror = getattr(fabric, "mirror", None) is not False
    out: list[EffectInstruction] = []
    for ins in instrs:
        axes = effect_axes(ins.effect_type, ins.target)
        if not axes or has_direction(ins):
            out.append(ins)
            continue
        rank = _stack_rank(ins, instrs)
        unit = _unit_beats(change, ins.effect_type, bpb)
        cut = ins.effect_type in DURATION_CELLABLE and ins.source != "weave"
        pieces = _split(ins, grid.cuts(unit, ins.start_ms, ins.end_ms)) if cut else [ins]
        offset = 1 if ins.target == HERO_GROUP else 0
        flip = (mirror and "RIGHT" in ins.target) != bool(rank % 2)
        for p in pieces:
            d = _pick(axes, change, unit, grid, (p.start_ms + p.end_ms) / 2, seed, offset, flip)
            p.directed = apply_direction(p.extra_settings, p.effect_type, d, 0)
            if p.effect_type == "Spirals":
                _spiral_shape(p, grid, seed, rank)
            out.append(p)
    return out
