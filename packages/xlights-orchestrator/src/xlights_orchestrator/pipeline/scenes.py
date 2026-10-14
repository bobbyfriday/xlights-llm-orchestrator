"""Scene casting on the brief-only path (claude-driven-orchestration, "Sections compose from
cookbook scenes"): parse a cookbook scene's stack table into archetype rows, cast those
archetypes onto the layout's real groups, and emit the layered, blended base rows the generic
one-row-per-group base layer would otherwise synthesize.

The cookbook (`xlights-scene-cookbook.md`) writes every scene against display ARCHETYPES
(`G2-HERO`, `G2-RHYTHM`, `G0-ALL-LESS-HERO`, …), never real groups. The brief casts them through
`SectionPlan.scene_cast` (`{archetype: group}`); when it leaves that empty, `default_cast` maps
each archetype by role through the SEM_ vocabulary (`semantic_groups`). Both are deterministic.

Conventions (see the cookbook §1 Scene Schema): cookbook `L1` is the TOP layer → `layer 0`; a
blank Layer cell means a single layer; a blank Row cell carries the archetype (and render style)
of the row above; Blend is an xLights `T_CHOICE_LayerMethod` (`Normal` → unset); a brightness in
the Effect cell ("30–40%", "25%") becomes a constant `C_SLIDER_Brightness` (range → midpoint);
"*Feature effect*" / "Any …" placeholders take the section's own `effect_family`.

Best-effort throughout: a scene without a stack table (prose-only scenes such as SC-09) or an
unknown id parses to `[]`, and the caller falls back to the generic base rows.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from xlights_core.knowledge.value_curves import brightness_setting

from .catalog import candidate_look_ids, placeable_effect_types
from .cookbook import scene_recipe
from ..show_plan import BLEND_METHODS, EffectInstruction
from .beats import effect_palette
from .semantic_groups import (
    ACCENT_GROUPS,
    BED_PREFERENCE,
    HERO_GROUP,
    RHYTHM_GROUPS,
    RHYTHM_POOL,
    SEM_ALL,
    SEM_CANVAS,
    SEM_HOUSE,
    SEM_SIDE_LEFT,
    SEM_SIDE_RIGHT,
)
from .weave import canon_effect_type, rhythm_pool

# The subtractive / frame groups the layout-semantics builder emits (xlights_core.knowledge.
# layout_semantics) that `semantic_groups` does not name because no deterministic layer targets
# them — the cookbook's archetypes do.
SEM_ALL_LESS_FOCAL = "SEM_ALL_LESS_FOCAL"
SEM_ALL_LESS_FOCAL_RHYTHM = "SEM_ALL_LESS_FOCAL_RHYTHM"
SEM_OUTLINE = "SEM_OUTLINE"

_ARCHETYPE = re.compile(r"\bG\d-[A-Z][A-Z-]*[A-Z]\b")      # G0-ALL, G2-HERO, G0-ALL-LESS-HERO-RHYTHM
_LAYER = re.compile(r"\bL(\d+)\b")
_PERCENT = re.compile(r"(\d+)\s*(?:[–-]\s*(\d+))?\s*%")  # "30–40%", "25%", "100%"
_MARKUP = re.compile(r"[*_`]+")
_CAMEL = re.compile(r"(?<=[a-z])(?=[A-Z])")                # SingleStrand → Single Strand
_FEATURE_PLACEHOLDER = re.compile(r"\bfeature effect\b|^\s*any\b", re.IGNORECASE)
_NO_CAST = ("G9-STROBE-OVERLAY",)   # not a group: code's climax flashes / on_top triggers play it


@dataclass(frozen=True)
class StackRow:
    """One cookbook stack row, resolved to the orchestrator's vocabulary."""

    archetype: str                 # the cookbook archetype (G2-HERO, …)
    layer: int = 0                 # 0 = top (cookbook L1)
    effect_type: str = ""          # canonical placeable type ("" when the cell names none)
    blend: str = ""                # T_CHOICE_LayerMethod ("" = Normal)
    brightness: float | None = None   # 0..1 fraction parsed from the Effect cell
    render_style: str = ""         # an xLights buffer style ("" → per-effect fallback)
    feature: bool = False          # a "*Feature effect*" placeholder → the section's effect_family
    phase: str = ""                # a timeline table's Phase cell ("" for a plain stack table)
    notes: str = ""
    raw_effect: str = ""


@dataclass
class _Table:
    columns: list[str]
    rows: list[list[str]] = field(default_factory=list)


def _cells(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    return [c.strip() for c in body.split("|")]


def _tables(block: str) -> list[_Table]:
    """Every markdown table in the block whose header has a `Row` column."""
    out: list[_Table] = []
    cur: _Table | None = None
    for line in block.splitlines():
        if not line.strip().startswith("|"):
            cur = None
            continue
        cells = _cells(line)
        if cur is None:
            cols = [c.lower() for c in cells]
            cur = _Table(columns=cols) if "row" in cols else _Table(columns=[])
            if cur.columns:
                out.append(cur)
            continue
        if all(set(c) <= set("-: ") for c in cells):       # the |---|---| separator
            continue
        if cur.columns:
            cur.rows.append(cells)
    return out


def _col(table: _Table, row: list[str], name: str) -> str:
    try:
        i = table.columns.index(name)
    except ValueError:
        return ""
    return row[i] if i < len(row) else ""


def _render_style(text: str) -> str:
    """The cookbook's render-style shorthand → a `render_style.KNOWN_STYLES` value, or ""."""
    t = _MARKUP.sub("", text or "").lower()
    if "per model" in t:
        return "Per Model Default"
    if "per preview" in t:
        return "Per Preview"
    if "single line" in t:
        return "Single Line"
    if "default" in t or "canvas" in t:
        return "Default"
    return ""


def _blend(text: str) -> str:
    t = _MARKUP.sub("", text or "").split("(")[0].strip()
    if not t or t.lower() == "normal":
        return ""
    return next((b for b in BLEND_METHODS if b.lower() == t.lower()), "")


def _brightness(text: str) -> float | None:
    m = _PERCENT.search(text or "")
    if not m:
        return None
    lo = float(m.group(1))
    hi = float(m.group(2)) if m.group(2) else lo
    return max(0.0, min(1.0, (lo + hi) / 200.0))


def _type_patterns() -> list[tuple[re.Pattern, str]]:
    """(whole-word pattern, placeable type) for every placeable type, in both its internal and
    its display spelling ("SingleStrand" / "Single Strand"); longest names first."""
    pats: list[tuple[re.Pattern, str]] = []
    for t in sorted(placeable_effect_types(), key=len, reverse=True):
        for spelling in {t, _CAMEL.sub(" ", t)}:
            pats.append((re.compile(r"(?<![A-Za-z])" + re.escape(spelling) + r"(?![A-Za-z])",
                                    re.IGNORECASE), t))
    return pats


def _effect_type(text: str) -> str:
    """The FIRST placeable effect named in an Effect cell ("Fast Spirals or Pinwheel" → Spirals,
    "Fire (or Plasma), color A" → Fire); "" when it names none."""
    t = _MARKUP.sub("", text or "")
    best: tuple[int, int, str] | None = None            # (position, -len, type)
    for pat, typ in _type_patterns():
        m = pat.search(t)
        if m is None:
            continue
        key = (m.start(), -len(m.group(0)), typ)
        if best is None or key < best:
            best = key
    return canon_effect_type(best[2]) if best else ""


def parse_scene_stack(scene_id: str) -> list[StackRow]:
    """The named scene's stack table as `StackRow`s (cookbook order). `[]` for an empty/unknown
    id or a scene whose stack is prose only. A timeline table (SC-04's `Phase` column) parses
    too, each row carrying its phase; `cast_scene` keeps only the final phase's rows."""
    block = scene_recipe(scene_id)
    if not block:
        return []
    rows: list[StackRow] = []
    for table in _tables(block):
        archetype, style = "", ""
        for raw in table.rows:
            row_cell = _MARKUP.sub("", _col(table, raw, "row"))
            m = _ARCHETYPE.search(row_cell)
            if m:
                archetype = m.group(0)
                style = _render_style(_col(table, raw, "render style")) or \
                    _render_style(row_cell[m.end():])          # "G2-RHYTHM (Per Model)"
            elif row_cell.strip():
                continue                                    # "(at release)" / "→ SC-04": not a row
            elif not archetype:
                continue
            else:                                           # blank Row: carries down
                style = _render_style(_col(table, raw, "render style")) or style
            effect_cell = _col(table, raw, "effect")
            layer_m = _LAYER.search(_col(table, raw, "layer"))
            rows.append(StackRow(
                archetype=archetype,
                layer=max(0, int(layer_m.group(1)) - 1) if layer_m else 0,
                effect_type=_effect_type(effect_cell),
                blend=_blend(_col(table, raw, "blend")),
                brightness=_brightness(effect_cell),
                render_style=style,
                feature=bool(_FEATURE_PLACEHOLDER.search(_MARKUP.sub("", effect_cell))),
                phase=_MARKUP.sub("", _col(table, raw, "phase")).strip(),
                notes=_col(table, raw, "notes"),
                raw_effect=effect_cell,
            ))
    return rows


def scene_archetypes(scene_id: str) -> list[str]:
    """The castable archetype row ids a scene's stack names (first-seen order)."""
    out: list[str] = []
    for r in parse_scene_stack(scene_id):
        if r.archetype not in out:
            out.append(r.archetype)
    return out


def default_cast(archetypes, section, available_groups: list[str]) -> dict[str, str]:
    """Cast archetypes onto real groups by ROLE (the `xlo-scenes` default casting table):
    hero → `HERO_GROUP`; rhythm → the section's rhythm pool, else the first rhythm family; accent
    → the first `ACCENT_GROUPS`; all-less-hero → the subtractive group when the layout built one,
    else the first `BED_PREFERENCE` group that is not the hero; frame → outline, else house; canvas
    → `SEM_CANVAS`, else the group named like a matrix; sides → `SEM_SIDE_*`. Archetypes the layout cannot cast are
    left out (their rows are skipped)."""
    avail = list(available_groups or [])

    def first(*names) -> str:
        return next((g for g in names if g in avail), "")

    pool = rhythm_pool(section, avail) if section is not None else []
    rhythm = (pool[0] if pool else "") or first(*RHYTHM_POOL, *RHYTHM_GROUPS)
    less_hero = first(SEM_ALL_LESS_FOCAL) or first(*(g for g in BED_PREFERENCE if g != HERO_GROUP))
    canvas = first(SEM_CANVAS) or next((g for g in avail if "matrix" in g.lower()), "")
    table = {
        "G0-ALL": first(SEM_ALL),
        "G0-ALL-LESS-HERO": less_hero,
        "G0-ALL-LESS-HERO-RHYTHM": first(SEM_ALL_LESS_FOCAL_RHYTHM) or less_hero,
        "G1-LEFT": first(SEM_SIDE_LEFT),
        "G1-RIGHT": first(SEM_SIDE_RIGHT),
        "G2-HERO": first(HERO_GROUP),
        "G2-RHYTHM": rhythm,
        "G2-FRAME": first(SEM_OUTLINE, SEM_HOUSE),
        "G2-ACCENT": first(*ACCENT_GROUPS),
        "G2-CANVAS": canvas,
    }
    return {a: table[a] for a in archetypes if table.get(a)}


def _castable_rows(stack: list[StackRow]) -> list[StackRow]:
    """A plain stack table casts every row; a timeline table casts only its FINAL phase (the
    sustained body of the section — SC-04's blackout/flash are code's transitions and climax
    flash). An explicit `Off` is never cast section-spanning."""
    rows = [r for r in stack if r.effect_type != "Off"]
    phased = [r for r in rows if r.phase]
    if phased:
        last = phased[-1].phase.split("(")[0].strip().lower()
        rows = [r for r in rows if not r.phase or r.phase.split("(")[0].strip().lower() == last]
    return rows


def cast_scene(section, stack: list[StackRow], available_groups: list[str], *,
               cast: dict[str, str] | None = None, pal_offset: int = 0) -> list[EffectInstruction]:
    """Cast a parsed scene stack onto real groups: one section-spanning `EffectInstruction` per
    castable row whose archetype maps to an available group — `layer` from the cookbook L-number,
    the blend as `T_CHOICE_LayerMethod` (Normal → unset), the cookbook brightness as a constant
    level, the row's render style, the section palette rotated per row (`pal_offset` rhymes
    recurring labels), and `source="scene"`. `cast` defaults to the section's `scene_cast`, then
    to `default_cast`. Rows naming no catalog-backed type are skipped; a feature placeholder takes
    the section's `effect_family`."""
    avail = set(available_groups or [])
    archetypes = [r.archetype for r in stack]
    cast = dict(cast if cast is not None else (getattr(section, "scene_cast", None) or {}))
    if not cast:
        cast = default_cast(archetypes, section, list(available_groups or []))
    family = canon_effect_type(getattr(section, "effect_family", "") or "")
    palette = list(getattr(section, "palette", None) or [])
    out: list[EffectInstruction] = []
    for row in _castable_rows(stack):
        target = cast.get(row.archetype, "")
        if row.archetype in _NO_CAST or not target or (avail and target not in avail):
            continue
        et = family if row.feature else row.effect_type
        looks = candidate_look_ids(et) if et else []
        if not looks:
            continue
        ins = EffectInstruction(
            target=target, effect_type=et, look_id=looks[0], layer=row.layer,
            render_style=row.render_style,
            palette_colors=effect_palette(palette, et, len(out), pal_offset) if palette else [],
            start_ms=section.start_ms, end_ms=section.end_ms, source="scene")
        if row.blend:
            ins.extra_settings["T_CHOICE_LayerMethod"] = row.blend
        if row.brightness is not None:
            ins.extra_settings.update(brightness_setting(row.brightness * 100.0))
        out.append(ins)
    echo = _canvas_echo(section, out, cast.get("G2-HERO", ""), family, avail)
    return out + ([echo] if echo is not None else [])


def _canvas_echo(section, rows: list[EffectInstruction], hero: str, family: str,
                 avail: set[str]) -> EffectInstruction | None:
    """The screens' share of a hero scene: when the section names `SEM_CANVAS` in its
    `target_groups` and the cast stack put nothing on it (most scenes have no G2-CANVAS row), the
    canvas gets ONE layer of the hero's feature effect, drawn per matrix — a calmer echo of the
    hero rather than a copy of its whole stack, and never left dark under a hero-only scene."""
    if SEM_CANVAS not in (getattr(section, "target_groups", None) or []) or \
            (avail and SEM_CANVAS not in avail) or any(r.target == SEM_CANVAS for r in rows):
        return None
    hero_rows = [r for r in rows if r.target == hero and hero]
    if not hero_rows:
        return None
    src = next((r for r in hero_rows if r.effect_type == family), hero_rows[0])
    echo = src.model_copy(deep=True, update={"target": SEM_CANVAS, "layer": 0,
                                              "render_style": "Per Model Default"})
    echo.extra_settings.pop("T_CHOICE_LayerMethod", None)
    return echo
