"""F-C: place stock xLights **Text** effects on the matrix model as sparse narrative punctuation.

The matrix is the show's storyteller (scene cookbook SC-08), yet the pipeline otherwise gives it
only washes and composites — never a word. This deterministic pass (not LLM-driven — the panel
already curated the song's lyric moments) emits a title card in the intro plus up to
`MAX_TEXT_MOMENTS` featured lyric phrases, each snapped to its aligned lyric line so text never
appears at a guessed time.

Grounding by construction: only strings already present in the brief (`identity.title`/`.artist`,
`featured_lyric_moments`) can ever appear — no section labels, no invented captions, no full
captioning. Text is asset-bound (F-B), so the emitter places it from `direct_settings` built by
`build_text_settings`, bypassing the mined catalog (Text is not in the LLM menu).

Coexistence with the matrix's focal duties: Text rides `on_top=True` with a `Max` layer blend over
the section's lightest palette color, and concurrent matrix-targeted non-text effects are dimmed
during each text span so glyphs stay legible over the kaleidoscope. Peak sections are excluded (the
peak belongs to the composite payoff). Each instruction carries its owning `section_index` and an
`X_MatrixText=1` marker so refine-loop / `xlo regen` splices replace this pass's output rather than
stacking it.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from xlights_core.knowledge.direct_settings import build_text_settings
from xlights_core.knowledge.value_curves import brightness_setting

from ..show_plan import EffectInstruction
from .beats import _lightest_hex, _slider_brightness, peak_sections
from .tuning import MAX_TEXT_MOMENTS, TEXT_SPACING_MS

log = logging.getLogger(__name__)

# -- doctrine constants -------------------------------------------------------
MATRIX_TEXT_MARKER = "X_MatrixText"      # extra_settings marker → this pass owns the instruction
MIN_MATRIX_PX = 50                       # catalog rule #2: no media effects under ~50px resolution
MIN_INTRO_MS = 8_000                     # skip the title card if the intro is shorter than this
_MIN_TITLE_END_LEAD_MS = 500             # end the title card at least this long before section 1
_FUZZY_MATCH_MIN = 0.5                   # token-overlap floor to accept a featured line's aligned span
_DEFAULT_MATRIX_H = 50                   # assumed legible matrix height until F-E's manifest / a probe
                                         #   — at the readability floor; a probed sub-50 matrix refuses
_FIT_CHARS = 12                          # ~chars that fit static at the default size (else scroll)
_DIM_FACTOR = 0.4                        # dim concurrent matrix non-text effects to ~40% under text
_BG_DIM_FLOOR = 20.0                     # ...but never darker than this (a faint bed still reads)


@dataclass
class TextMoment:
    """A resolved narrative Text placement (times already snapped to the audio / intro)."""

    text: str
    start_ms: int
    end_ms: int
    section_index: int
    is_title: bool = False


def find_matrix(model_names: list[str] | None) -> str | None:
    """The layout's matrix MODEL name (first name containing "matrix", case-insensitive).

    Mirrors `layout_semantics._ORDER_TIERS`' focal test. `None` → no matrix → the whole pass no-ops.
    Text is placed on the model directly, never a group (a group canvas mangles glyphs).
    """
    for name in model_names or []:
        if "matrix" in (name or "").lower():
            return name
    return None


def _norm(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9']+", (s or "").lower()))


def _sanitizable(text: str) -> bool:
    """A phrase F-B's builder will accept (no comma/equals, non-empty after strip)."""
    t = (text or "").strip()
    return bool(t) and "," not in t and "=" not in t


def _section_at(sections, at_ms: int) -> int | None:
    for i, s in enumerate(sections):
        if s.start_ms <= at_ms < s.end_ms:
            return i
    return None


def _title_text(brief) -> str:
    idn = getattr(brief, "identity", None)
    if not idn or not (idn.title or "").strip():
        return ""
    title = idn.title.strip()
    artist = (idn.artist or "").strip()
    # append the artist only if the combined line still fits static width (title card is static)
    combined = f"{title} - {artist}" if artist else title
    return combined if _sanitizable(combined) and len(combined) <= _FIT_CHARS * 2 else title


def _aligned_lines(sa) -> list[tuple[str, int, int]]:
    """(text, start_ms, end_ms) for every aligned lyric line, from the untyped analysis lyrics."""
    from ..song_description import _timed_lines
    lyrics = getattr(sa, "lyrics", None)
    return [(t, a, b) for (t, a, b) in (_timed_lines(lyrics) if lyrics else []) if b > a]


def _snap_to_line(line_text: str, aligned: list[tuple[str, int, int]]) -> tuple[int, int] | None:
    """Fuzzy-match a featured line to an aligned line; return its (start,end) span or None.

    Grounding rule D3: a featured moment with no aligned match is DROPPED — never shown at a
    brief-supplied (guessed) time. Same token-overlap heuristic as `song_description`.
    """
    ftok = _norm(line_text)
    if not ftok or not aligned:
        return None
    best, score = None, 0.0
    for text, a, b in aligned:
        sc = len(ftok & _norm(text)) / max(1, len(ftok))
        if sc > score:
            best, score = (a, b), sc
    return best if best and score >= _FUZZY_MATCH_MIN else None


def _title_moment(brief, sections) -> TextMoment | None:
    """Title card: identity.title (+ artist if it fits), intro only, static, ending before section 1.

    Skipped when the intro is < `MIN_INTRO_MS`, the title is empty, or there are no sections.
    """
    if not sections:
        return None
    intro = sections[0]
    if (intro.end_ms - intro.start_ms) < MIN_INTRO_MS:
        return None
    text = _title_text(brief)
    if not text:
        return None
    end = max(intro.start_ms + 1, intro.end_ms - _MIN_TITLE_END_LEAD_MS)   # ≥ a lead before section 1
    return TextMoment(text=text, start_ms=intro.start_ms, end_ms=end, section_index=0, is_title=True)


def _lyric_key(km) -> str:
    """Forward-compat escape hatch (D1): a KeyMoment of kind 'lyric' with a future `text` field
    lets the Director hand-pick a caption; the pass prefers it. Absent today → empty string."""
    return (getattr(km, "text", "") or "").strip() if "lyric" in (getattr(km, "kind", "") or "").lower() else ""


def select_text_moments(brief, sa, plan) -> list[TextMoment]:
    """Deterministically choose the show's narrative Text moments (pure — no I/O, no LLM).

    Priority + doctrine (D3): a title card in the intro, then featured lyric phrases cross-checked
    against the aligned lines and snapped to the matched line span (unmatched → dropped). Caps:
    ≤ `MAX_TEXT_MOMENTS` phrases, ≥ `TEXT_SPACING_MS` apart, ≤ one per section, none in the peak
    section. Instrumental songs (no featured moments, no aligned lines) get the title card only.
    """
    sections = list(getattr(plan, "sections", None) or [])
    out: list[TextMoment] = []
    title = _title_moment(brief, sections)
    if title is not None:
        out.append(title)

    aligned = _aligned_lines(sa)
    peaks = peak_sections(plan)
    # Director-chosen lyric captions (forward-compat) take precedence, then curated featured moments.
    # Each candidate is (line, brief_start_hint) — the hint only orders the scan; the placed time is
    # always the snapped aligned-line span, never the brief's (possibly drifted) timestamp.
    candidates: list[tuple[str, int]] = []
    for km in getattr(plan, "key_moments", None) or []:
        txt = _lyric_key(km)
        if txt and _sanitizable(txt):
            candidates.append((txt, km.at_ms))
    for m in getattr(brief, "featured_lyric_moments", None) or []:
        candidates.append((m.line, m.start_ms))

    # the title card owns its (intro) section — a phrase must not double up there. Phrase spacing
    # is measured phrase-to-phrase; the title is a separate class and doesn't consume the budget.
    used_sections: set[int] = {title.section_index} if title is not None else set()
    last_start = -TEXT_SPACING_MS
    placed = 0
    for line, _hint in sorted(candidates, key=lambda c: c[1]):
        if placed >= MAX_TEXT_MOMENTS:
            break
        span = _snap_to_line(line, aligned)
        if span is None:                                  # no aligned line → drop (never guess a time)
            continue
        start, end = span
        if end <= start or not _sanitizable(line):
            continue
        if start - last_start < TEXT_SPACING_MS:          # too close to the previous moment
            continue
        si = _section_at(sections, start)
        if si is None or si in peaks or si in used_sections:   # ≤ one/section; never the peak
            continue
        out.append(TextMoment(text=line.strip(), start_ms=start, end_ms=end, section_index=si))
        used_sections.add(si)
        last_start = start
        placed += 1
    return out


def _matrix_height(st) -> int:
    """Probed matrix pixel height, or the default until F-E's layout manifest lands.

    TODO(F-E): read the real height from the layout manifest (has_matrix / node-count / pixel dims)
    instead of this heuristic; a live `client.get_model("Matrix")` probe (parm1/parm2) is the interim.
    """
    return int(getattr(st, "matrix_height", 0) or _DEFAULT_MATRIX_H)


def _font_size(matrix_h: int) -> int:
    """Bold glyphs ≥ 10-12 px tall and ≤ matrix height - 2 (catalog §8 legibility floor)."""
    return max(10, min(12, matrix_h - 2))


def _text_instruction(moment: TextMoment, matrix: str, section) -> EffectInstruction | None:
    """Build one Text `EffectInstruction` on the matrix model via F-B's `build_text_settings`.

    Static when the phrase fits the probed width, else scroll-left exactly once across its span
    (speed sized so one traverse ≈ the moment duration — text that loops reads as a glitch).
    """
    scroll = len(moment.text) > _FIT_CHARS
    movement = "left" if scroll else "none"
    dur_ms = max(1, moment.end_ms - moment.start_ms)
    # scroll-once: xLights Text speed is chars/frame-ish; scale so a full traverse ≈ the duration.
    speed = max(1, round((len(moment.text) + _FIT_CHARS) / (dur_ms / 1000.0))) if scroll else 10
    try:
        settings = build_text_settings(moment.text, movement=movement, speed=speed)
    except ValueError as exc:                         # unsanitizable phrase → drop, never mangle
        log.info("matrix text: dropping unsanitizable phrase %r: %s", moment.text, exc)
        return None
    light = _lightest_hex(getattr(section, "palette", None) or [])
    ins = EffectInstruction(
        target=matrix, effect_type="Text", look_id="",
        direct_settings=settings, palette_colors=[light] if light else [],
        start_ms=moment.start_ms, end_ms=moment.end_ms,
        section_index=moment.section_index, on_top=True,
        extra_settings={"T_CHOICE_LayerMethod": "Max", MATRIX_TEXT_MARKER: "1"},
    )
    return ins


def _dim_background(instrs: list[EffectInstruction], matrix: str,
                    moments: list[TextMoment]) -> None:
    """Dim concurrent matrix-targeted NON-text effects during each text span so glyphs read.

    Multiplies `C_SLIDER_Brightness` by `_DIM_FACTOR` (floored) — the catalog's Faces ≤30% rule
    applied to text. Only the canvas behind the letters is touched; other props are never dimmed.
    """
    for ins in instrs:
        if ins.target != matrix or ins.effect_type == "Text":
            continue
        if not any(not (ins.end_ms <= m.start_ms or ins.start_ms >= m.end_ms) for m in moments):
            continue
        cur = _slider_brightness(ins)
        base = cur if cur is not None else 100.0
        ins.extra_settings.update(brightness_setting(max(_BG_DIM_FLOOR, base * _DIM_FACTOR)))


def place_matrix_text(st, matrix: str | None) -> list[EffectInstruction]:
    """Emit narrative Text on the matrix model + dim its background under each text span.

    No-ops (returns `[]`) when there is no matrix, no plan, no selected moment, or the matrix is
    under ~`MIN_MATRIX_PX` resolution (catalog rule #2) — each with a degradation-log line.
    """
    if not matrix:
        log.info("matrix text: no matrix model in the layout → skipped")
        return []
    matrix_h = _matrix_height(st)
    if matrix_h < MIN_MATRIX_PX:
        log.info("matrix text: matrix resolution %dpx < %dpx floor → skipped (catalog rule #2)",
                 matrix_h, MIN_MATRIX_PX)
        return []
    moments = select_text_moments(st.music_brief, st.song_analysis, st.show_plan)
    if not moments:
        log.info("matrix text: no grounded text moments (instrumental / empty identity) → skipped")
        return []
    sections = list(st.show_plan.sections)
    out: list[EffectInstruction] = []
    for m in moments:
        section = sections[m.section_index] if 0 <= m.section_index < len(sections) else None
        ins = _text_instruction(m, matrix, section)
        if ins is not None:
            out.append(ins)
    if out:
        _dim_background(st.instructions, matrix, moments)
    log.info("matrix text: placed %d Text effect(s) on %s", len(out), matrix)
    return out


def strip_matrix_text(instrs: list[EffectInstruction]) -> list[EffectInstruction]:
    """Drop this pass's prior output so re-running replaces rather than stacks (idempotence, D6)."""
    return [i for i in instrs if i.extra_settings.get(MATRIX_TEXT_MARKER) != "1"]
