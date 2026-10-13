"""`xlo validate-brief`: machine-readable, actionable checks on a creative brief (D5).

This is the loop that replaces structured-output enforcement: Claude writes `creative_brief.json`,
runs the validator, reads `validation.json`, fixes the named paths, and re-validates until clean.
So every finding carries a JSON-pointer-ish `path` (`sections[3].target_groups[1]`), a plain
`message`, and — for membership errors — the bounded `allowed` list to pick from.

Errors (block realization):
  - the file does not parse as `ShowPlan` (pydantic errors mapped to path/message)
  - sections out of order, overlapping, or leaving a gap > tolerance (incl. before the first /
    after the last against the song duration)
  - group / effect / scene / stem / pulse_on / palette names outside the vocabulary
  - `fabric.carrier` not cellable, `fabric.alternation` unknown, `fabric.cell_beats` outside 1–8,
    `fabric.blend` not a known layer method (`vocab.blends`)
Warnings (reported, never block):
  - a section boundary not within tolerance of a downbeat (when downbeats are given)
  - a section longer than ~32 s
  - the same `effect_family` on two adjacent sections

All checks run over the RAW dict (not only the parsed model) so one pass reports everything —
including the optional `fabric` block whether or not `SectionPlan` declares it yet.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import BaseModel, ValidationError

from ..show_plan import ShowPlan

VALIDATION_NAME = "validation.json"

ALTERNATIONS = ("chase", "pingpong", "all", "sparse")
PULSE_ON = ("", "beat", "onset")
CELL_BEATS_RANGE = (1, 8)
LONG_SECTION_MS = 32_000                  # ~32 s: past this a section reads as two
ALLOWED_CAP = 40                           # bounded `allowed` lists; the rest is "+N more"

_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")    # the palette resolver accepts raw hex too
_NORM = re.compile(r"[\s_-]+")             # ...and names case/space/hyphen-insensitively


class Issue(BaseModel):
    path: str
    message: str
    allowed: list[str] = []


class ValidationResult(BaseModel):
    ok: bool
    errors: list[Issue] = []
    warnings: list[Issue] = []


# ---------------------------------------------------------------- helpers

def _cap(values) -> list[str]:
    vals = [str(v) for v in values]
    if len(vals) <= ALLOWED_CAP:
        return vals
    return vals[:ALLOWED_CAP] + [f"+{len(vals) - ALLOWED_CAP} more"]


def _norm_color(c: str) -> str:
    return _NORM.sub(" ", str(c).lower()).strip()


def _squeeze(s: str) -> str:
    return str(s).replace(" ", "")


class _Membership:
    """One vocabulary list with its matching rule; produces `allowed`-bearing errors."""

    def __init__(self, label: str, values, *, match: str = "exact", blank_ok: bool = False):
        self.label, self.values, self.match, self.blank_ok = label, [str(v) for v in values], match, blank_ok
        if match == "effect":
            self._keys = {_squeeze(v) for v in self.values}
        elif match == "color":
            self._keys = {_norm_color(v) for v in self.values}
        else:
            self._keys = set(self.values)

    def ok(self, v) -> bool:
        if not isinstance(v, str):
            return False
        if v == "" and self.blank_ok:
            return True
        if self.match == "effect":
            return v in self._keys or _squeeze(v) in self._keys
        if self.match == "color":
            return bool(_HEX.match(v.strip())) or _norm_color(v) in self._keys
        return v in self._keys

    def check(self, v, path: str, errors: list[Issue]) -> None:
        if self.ok(v):
            return
        shown = repr(v) if isinstance(v, str) else type(v).__name__
        msg = f"{shown} is not a known {self.label}"
        if self.match == "color":
            msg += " (a named color or #RRGGBB)"
        if self.blank_ok:
            msg += '; "" leaves it to code'
        errors.append(Issue(path=path, message=msg, allowed=_cap(self.values)))

    def check_list(self, vals, path: str, errors: list[Issue]) -> None:
        if vals is None:
            return
        if not isinstance(vals, list):
            errors.append(Issue(path=path, message=f"expected a list of {self.label}s"))
            return
        for j, v in enumerate(vals):
            self.check(v, f"{path}[{j}]", errors)


def _ms(section: dict, key: str):
    v = section.get(key)
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def _fmt(ms: int) -> str:
    return f"{ms / 1000:.2f}s"


# ---------------------------------------------------------------- checks

def _pydantic_errors(brief: dict) -> list[Issue]:
    try:
        ShowPlan.model_validate(brief)
    except ValidationError as exc:
        out = []
        for err in exc.errors():
            path = ""
            for part in err.get("loc", ()):
                path += f"[{part}]" if isinstance(part, int) else (f".{part}" if path else str(part))
            out.append(Issue(path=path or "$", message=err.get("msg", "invalid")))
        return out
    return []


def _coverage(sections: list, duration_ms: int, tol: int, errors: list[Issue]) -> None:
    spans = []
    for i, s in enumerate(sections):
        if not isinstance(s, dict):
            continue
        a, b = _ms(s, "start_ms"), _ms(s, "end_ms")
        if a is None or b is None:
            continue                                   # pydantic already named it
        if b <= a:
            errors.append(Issue(path=f"sections[{i}].end_ms",
                                message=f"end_ms {b} must be after start_ms {a}"))
            continue
        spans.append((i, a, b))
    if not spans:
        if not sections:
            errors.append(Issue(path="sections", message="the brief has no sections"))
        return
    for (i, a, _), (j, c, _) in zip(spans, spans[1:]):
        if c < a:
            errors.append(Issue(path=f"sections[{j}].start_ms",
                                message=f"sections[{j}] starts at {_fmt(c)}, before sections[{i}] "
                                        f"({_fmt(a)}); sections must be ordered by start_ms"))
    ordered = sorted(spans, key=lambda t: (t[1], t[2]))
    first_i, first_a, _ = ordered[0]
    if first_a > tol:
        errors.append(Issue(path=f"sections[{first_i}].start_ms",
                            message=f"gap of {_fmt(first_a)} before sections[{first_i}]: the show "
                                    f"must start within {tol} ms of 0"))
    for (i, _, b), (j, c, d) in zip(ordered, ordered[1:]):
        if c - b > tol:
            errors.append(Issue(path=f"sections[{j}].start_ms",
                                message=f"gap of {_fmt(c - b)} between sections[{i}] (ends {_fmt(b)}) "
                                        f"and sections[{j}] (starts {_fmt(c)}); max {tol} ms"))
        elif b - c > tol:
            errors.append(Issue(path=f"sections[{j}].start_ms",
                                message=f"sections[{i}] (ends {_fmt(b)}) overlaps sections[{j}] "
                                        f"(starts {_fmt(c)}) by {_fmt(b - c)}; max {tol} ms"))
    last_i, _, last_b = ordered[-1]
    if duration_ms - last_b > tol:
        errors.append(Issue(path=f"sections[{last_i}].end_ms",
                            message=f"gap of {_fmt(duration_ms - last_b)} after sections[{last_i}] "
                                    f"(ends {_fmt(last_b)}): the song runs to {_fmt(duration_ms)}"))
    elif last_b - duration_ms > tol:
        errors.append(Issue(path=f"sections[{last_i}].end_ms",
                            message=f"sections[{last_i}] ends at {_fmt(last_b)}, past the song's "
                                    f"{_fmt(duration_ms)} by {_fmt(last_b - duration_ms)}"))


def _fabric_of(section: dict, model_section) -> dict | None:
    """The section's fabric block: the raw dict wins (it works before `SectionPlan` grows the
    field); otherwise a parsed model attribute, via `getattr` so either shape is fine."""
    raw = section.get("fabric")
    if isinstance(raw, dict):
        return raw
    if raw is not None:
        return {"__bad__": raw}
    fab = getattr(model_section, "fabric", None)
    if fab is None:
        return None
    return fab.model_dump() if hasattr(fab, "model_dump") else dict(fab)


def _membership(sections: list, model_sections: list, vocab: dict, errors: list[Issue]) -> None:
    groups = _Membership("targetable group", vocab.get("groups", []))
    effects = _Membership("placeable effect type", vocab.get("effect_types", []), match="effect")
    effects_opt = _Membership("placeable effect type", vocab.get("effect_types", []),
                              match="effect", blank_ok=True)
    scenes = _Membership("scene id", vocab.get("scene_ids", []), blank_ok=True)
    stems = _Membership("stem", vocab.get("stems", []), blank_ok=True)
    pulse = _Membership("pulse_on value", PULSE_ON)
    cellable = _Membership("cellable effect type", vocab.get("cellable", []), match="effect", blank_ok=True)
    alternation = _Membership("alternation", ALTERNATIONS, blank_ok=True)
    blends = (_Membership("layer blend method", vocab.get("blends", []), blank_ok=True)
              if vocab.get("blends") else None)
    colors = _Membership("named color", vocab.get("colors", []), match="color") if vocab.get("colors") else None

    for i, s in enumerate(sections):
        if not isinstance(s, dict):
            continue
        p = f"sections[{i}]"
        ms = model_sections[i] if i < len(model_sections) else None
        groups.check_list(s.get("target_groups"), f"{p}.target_groups", errors)
        groups.check_list(s.get("pulse_groups"), f"{p}.pulse_groups", errors)
        if "effect_family" in s:
            effects.check(s.get("effect_family"), f"{p}.effect_family", errors)
        effects.check_list(s.get("effect_types"), f"{p}.effect_types", errors)
        if "accent_effect" in s:
            effects_opt.check(s.get("accent_effect"), f"{p}.accent_effect", errors)
        if "scene_id" in s:
            scenes.check(s.get("scene_id"), f"{p}.scene_id", errors)
        if "follow_stem" in s:
            stems.check(s.get("follow_stem"), f"{p}.follow_stem", errors)
        if "pulse_on" in s:
            pulse.check(s.get("pulse_on"), f"{p}.pulse_on", errors)
        if colors is not None:
            colors.check_list(s.get("palette"), f"{p}.palette", errors)
        fab = _fabric_of(s, ms)
        if fab is None:
            continue
        if "__bad__" in fab:
            errors.append(Issue(path=f"{p}.fabric", message="fabric must be an object"))
            continue
        if "carrier" in fab and fab["carrier"] is not None:
            cellable.check(fab["carrier"], f"{p}.fabric.carrier", errors)
        if "alternation" in fab and fab["alternation"] is not None:
            alternation.check(fab["alternation"], f"{p}.fabric.alternation", errors)
        if blends is not None and "blend" in fab and fab["blend"] is not None:
            blends.check(fab["blend"], f"{p}.fabric.blend", errors)
        cb = fab.get("cell_beats")
        if cb is not None:
            lo, hi = CELL_BEATS_RANGE
            if isinstance(cb, bool) or not isinstance(cb, int) or not lo <= cb <= hi:
                errors.append(Issue(path=f"{p}.fabric.cell_beats",
                                    message=f"cell_beats must be an integer {lo}–{hi} or null, got {cb!r}",
                                    allowed=[str(n) for n in range(lo, hi + 1)]))


def _show_palette(brief: dict, vocab: dict, errors: list[Issue]) -> None:
    if not vocab.get("colors"):
        return
    pal = brief.get("palette")
    if isinstance(pal, dict):
        _Membership("named color", vocab["colors"], match="color").check_list(
            pal.get("colors"), "palette.colors", errors)


def _warnings(sections: list, downbeats_ms: list[int] | None, tol: int) -> list[Issue]:
    out: list[Issue] = []
    beats = sorted(int(b) for b in (downbeats_ms or []))
    prev_family: str | None = None
    for i, s in enumerate(sections):
        if not isinstance(s, dict):
            continue
        p = f"sections[{i}]"
        a, b = _ms(s, "start_ms"), _ms(s, "end_ms")
        if a is not None and beats and a > 0:
            nearest = min(beats, key=lambda d: abs(d - a))
            if abs(nearest - a) > tol:
                out.append(Issue(path=f"{p}.start_ms",
                                 message=f"starts at {_fmt(a)}, {_fmt(abs(nearest - a))} from the nearest "
                                         f"downbeat ({_fmt(nearest)}); consider snapping to it"))
        if a is not None and b is not None and b - a > LONG_SECTION_MS:
            out.append(Issue(path=f"{p}.end_ms",
                             message=f"section runs {_fmt(b - a)} (> {LONG_SECTION_MS // 1000} s); "
                                     f"consider splitting it so the look can evolve"))
        fam = s.get("effect_family")
        if isinstance(fam, str) and fam and prev_family is not None and _squeeze(fam) == _squeeze(prev_family):
            out.append(Issue(path=f"{p}.effect_family",
                             message=f"{fam!r} repeats the previous section's effect_family; "
                                     f"vary it unless the repetition is deliberate"))
        prev_family = fam if isinstance(fam, str) else None
    return out


# ---------------------------------------------------------------- entry points

def validate_brief(brief_json: dict | str, vocab: dict, *, duration_ms: int,
                   downbeats_ms: list[int] | None = None, tolerance_ms: int = 500) -> ValidationResult:
    """Validate a brief (a dict or JSON text) against the song dir's vocab. Never raises on a
    bad brief — malformed JSON and schema failures become errors in the result."""
    errors: list[Issue] = []
    if isinstance(brief_json, str):
        try:
            brief = json.loads(brief_json)
        except json.JSONDecodeError as exc:
            return ValidationResult(ok=False, errors=[Issue(path="$", message=f"not valid JSON: {exc}")])
    else:
        brief = brief_json
    if not isinstance(brief, dict):
        return ValidationResult(ok=False, errors=[Issue(path="$", message="the brief must be a JSON object")])

    errors.extend(_pydantic_errors(brief))
    sections = brief.get("sections")
    if not isinstance(sections, list):
        if not any(e.path.startswith("sections") for e in errors):
            errors.append(Issue(path="sections", message="sections must be a list"))
        return ValidationResult(ok=False, errors=errors)

    model_sections: list = []
    if not errors:
        model_sections = list(ShowPlan.model_validate(brief).sections)

    _coverage(sections, duration_ms, tolerance_ms, errors)
    _membership(sections, model_sections, vocab, errors)
    _show_palette(brief, vocab, errors)
    warnings = _warnings(sections, downbeats_ms, tolerance_ms)
    return ValidationResult(ok=not errors, errors=errors, warnings=warnings)


def write_validation(song_dir, result: ValidationResult) -> Path:
    """Write `validation.json` under the song dir; returns its path."""
    out = Path(song_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / VALIDATION_NAME
    path.write_text(json.dumps(result.model_dump(), indent=1))
    return path


def summary_line(result: ValidationResult) -> str:
    """The one-line stdout summary the CLI prints."""
    if result.ok:
        tail = f" ({len(result.warnings)} warning{'s' if len(result.warnings) != 1 else ''})" if result.warnings else ""
        return f"brief ok{tail}"
    first = result.errors[0]
    more = f" (+{len(result.errors) - 1} more)" if len(result.errors) > 1 else ""
    return f"brief has {len(result.errors)} error{'s' if len(result.errors) != 1 else ''}: {first.path}: {first.message}{more}"
