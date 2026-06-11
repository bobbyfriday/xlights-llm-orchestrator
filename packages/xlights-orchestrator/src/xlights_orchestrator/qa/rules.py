"""Placement-rules QA (objective) — the effects catalog §11 rules that are 'normative for
automated sequencing', detected deterministically. The Generator stays the author: violations
become section-scoped findings the refine loop regenerates (plus two hard duration caps the
catalog states verbatim).

Enforced here: #2 texture-on-linear affinity, #3 energy bands (±1), #4 one-feature-per-moment,
#7 Strobe/Shimmer hard caps (via `clamp_hard_caps`).
"""

from __future__ import annotations

from ..refine import Finding

# Catalog §2 energy bands (min, max) — only effects we can place; absent = unconstrained.
ENERGY_BAND: dict[str, tuple[int, int]] = {
    "On": (1, 5), "Fill": (2, 3), "SingleStrand": (2, 4), "Bars": (2, 4), "Curtain": (2, 3),
    "Wave": (2, 3), "Marquee": (2, 3), "Meteors": (2, 4), "Morph": (2, 4), "Garlands": (2, 2),
    "Pinwheel": (2, 5), "Fan": (2, 4), "Galaxy": (2, 4), "Shockwave": (3, 5), "Spirals": (2, 5),
    "Circles": (2, 3), "Kaleidoscope": (3, 4), "Butterfly": (2, 3), "Plasma": (1, 3),
    "Fire": (2, 4), "Liquid": (2, 3), "Snowflakes": (1, 2), "Snowstorm": (2, 3),
    "Twinkle": (1, 3), "Shimmer": (2, 4), "Strobe": (4, 5), "Lightning": (3, 5),
    "Fireworks": (3, 5), "Ripple": (2, 3), "Shape": (1, 4), "Tendril": (2, 3), "Tree": (2, 2),
    "VU Meter": (2, 5),
}
# Duration classes (catalog §2.1 v0.3): a HIT is ≤1-bar punctuation (smearing it over a section
# reads as one slow weird gesture); a PHRASE is a bounded gesture (reveal/build); CELL-ABLE motion
# effects default to 1–2 bar cells (community medians are 0.3–0.9s even for Spirals/Wave —
# sustained-CAPABLE ≠ sustained-USED); explicit long beds (ColorWash/Plasma on bed groups) exempt.
DURATION_HIT = {"Shockwave", "Strobe", "Lightning"}
DURATION_PHRASE = {"Curtain", "Fill", "Morph", "Fan", "Fireworks", "Shimmer"}
DURATION_CELLABLE = {"SingleStrand", "Spirals", "Pinwheel", "Ripple", "Wave", "Bars", "Butterfly",
                     "Meteors", "Garlands"}
PHRASE_BARS = 8
CELL_BARS = 2
_BED_TARGET_PREFIXES = ("SEM_BAND_",)                  # band rows MAY hold long beds
_BED_TARGETS = {"SEM_ALL", "SEM_YARD"}                 # exact — NOT SEM_ALL_LESS_* (those weave)

# The community fabric is woven from continuous-motion effects (~58% there vs ~16% ours) —
# surfaced per energetic section as an ADVISORY so the Judge sees fabric regressions.
MOTION_EFFECTS = DURATION_CELLABLE | {"Meteors", "Garlands", "Fire", "Galaxy", "Pinwheel"}
MOTION_SHARE_MIN = 0.30
MOTION_SHARE_INTENSITY = 0.5

TEXTURE = {"Plasma", "Fire", "Liquid", "Life"}                   # rule #2: never on linear props
FEATURES = {"Kaleidoscope", "Shader", "Shockwave", "Fireworks"}  # rule #4: one at a time
_LINEAR_PREFIXES = ("SEM_ARCHES", "SEM_OUTLINE", "SEM_CANES", "SEM_ICICLES", "SEM_PATH")

STROBE_CAP_MS = 1000          # rule #7, verbatim: "Strobe ≤ ~1s per instance"
SHIMMER_BARS = 2              # rule #7: "Shimmer ≤ 2 bars"
_PENALTY = 8                  # objective points per violation


def _is_linear(target: str) -> bool:
    return target.startswith(_LINEAR_PREFIXES)


def _section_band(intensity: float) -> int:
    return 1 + round(4 * max(0.0, min(1.0, intensity or 0.0)))


def evaluate(instructions, plan) -> tuple[int, list[Finding]]:
    sections = list(getattr(plan, "sections", None) or []) if plan else []
    findings: list[Finding] = []

    features: list = []
    for ins in instructions or []:
        si = getattr(ins, "section_index", None)
        # #2 — texture on linear props
        if ins.effect_type in TEXTURE and _is_linear(ins.target):
            findings.append(Finding(
                scope=f"section {si} / {ins.target}", severity="error", metric="rules",
                objective=True, section_index=si,
                detail=f"{ins.effect_type} (texture) on a linear prop group — reads as flicker, "
                       f"not texture (catalog rule #2)"))
        # #3 — energy band vs the section's energy (±1 allowed)
        band = ENERGY_BAND.get(ins.effect_type)
        if band and si is not None and 0 <= si < len(sections):
            sec_band = _section_band(getattr(sections[si], "intensity", 0.5))
            gap = max(band[0] - sec_band, sec_band - band[1], 0)
            if gap >= 2:
                findings.append(Finding(
                    scope=f"section {si} / {ins.target}", severity="error", metric="rules",
                    objective=True, section_index=si,
                    detail=f"{ins.effect_type} (energy {band[0]}–{band[1]}) in an energy-"
                           f"{sec_band} section — a defect, not a choice (catalog rule #3)"))
        if ins.effect_type in FEATURES:
            features.append(ins)
    # #4 — one high-attention feature MOMENT at a time. The same effect on many groups in the
    # same window is ONE gesture, so merge same-type overlapping spans into events first.
    events = []                                       # (start, end, effect_type, representative ins)
    for etype in {x.effect_type for x in features}:
        spans = sorted(((x.start_ms, x.end_ms, x) for x in features if x.effect_type == etype),
                       key=lambda t: (t[0], t[1]))
        for st_, en_, x in spans:
            if events and events[-1][2] == etype and st_ < events[-1][1]:
                events[-1] = (events[-1][0], max(events[-1][1], en_), etype, events[-1][3])
            else:
                events.append((st_, en_, etype, x))
    events.sort(key=lambda e: (e[0], e[1]))
    for a, b in zip(events, events[1:]):
        if b[0] < a[1]:
            x = b[3]
            findings.append(Finding(
                scope=f"section {getattr(x, 'section_index', None)} / {x.target}",
                severity="error", metric="rules", objective=True,
                section_index=getattr(x, "section_index", None),
                detail=f"{b[2]} overlaps {a[2]} — at most one high-attention "
                       f"feature at a time (catalog rule #4)"))
    score = max(0, 100 - _PENALTY * len(findings))      # advisories below do NOT gate the score
    # motion-share advisory: an energetic section that is mostly static/punctuation reads as
    # "pulses over a wash", not the community's woven-motion fabric.
    by_section: dict[int, list] = {}
    for ins in instructions or []:
        si = getattr(ins, "section_index", None)
        if si is not None:
            by_section.setdefault(si, []).append(ins)
    for si, group in sorted(by_section.items()):
        if not (0 <= si < len(sections)):
            continue
        if (getattr(sections[si], "intensity", 0.5) or 0.5) < MOTION_SHARE_INTENSITY:
            continue
        share = sum(1 for x in group if x.effect_type in MOTION_EFFECTS) / len(group)
        if share < MOTION_SHARE_MIN:
            findings.append(Finding(
                scope=f"section {si}", severity="warn", metric="rules",
                objective=False, section_index=si,
                detail=f"motion-effect share {share:.0%} (< {MOTION_SHARE_MIN:.0%}) in an "
                       f"energetic section — mostly static/punctuation effects; weave motion "
                       f"cells (chases/spirals/ripples) instead (community fabric ~58% motion)"))
    return score, findings


def clamp_hard_caps(instructions, tempo_bpm: float | None) -> int:
    """Catalog rule #7 hard caps, enforced in place. Returns the number clamped."""
    bar_ms = (4 * 60000 / tempo_bpm) if tempo_bpm else 2000.0
    shimmer_cap = int(SHIMMER_BARS * bar_ms)
    n = 0
    for ins in instructions or []:
        cap = STROBE_CAP_MS if ins.effect_type == "Strobe" else \
              shimmer_cap if ins.effect_type == "Shimmer" else None
        if cap and ins.end_ms - ins.start_ms > cap:
            ins.end_ms = ins.start_ms + cap
            n += 1
    return n
