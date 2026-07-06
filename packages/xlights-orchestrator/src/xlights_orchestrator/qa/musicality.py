"""Musicality QA (ADVISORY): compositional metrics the objective score can't see.

These measure *musical shape*, not correctness — repeated music that fails to rhyme, a show with
no dynamic range, a quiet section drowning in concurrent motion. Every finding is `objective=False`
(it informs the Judge and the revision log, never gates the refine loop's convergence) and the
metric names are `musicality:*` so `source_of` groups them apart from sync/placement/variety.

Pure functions over the placed `EffectInstruction[]` + the plan + the repetition map — no xLights,
no render, no LLM. Each metric emits a BOUNDED number of findings (mirroring qa/variety's style).
"""

from __future__ import annotations

from collections import defaultdict

from ..refine import Finding
from ..pipeline.effect_meta import MOTION_EFFECTS

# -- repetition-rhyme ---------------------------------------------------------
RHYME_LOW = 0.5             # mean label similarity below this → an advisory "repeat doesn't rhyme"
_MAX_RHYME_FINDINGS = 4     # at most one per label, hard-capped

# -- dynamic-range ------------------------------------------------------------
DYNAMIC_LOW = 0.25          # normalized spread below this → "wall-to-wall brightness"

# -- focus-budget -------------------------------------------------------------
# concurrent distinct moving-effect SYSTEMS a section may run, by energy band
_FOCUS_BUDGET = ((0.66, 4), (0.4, 3), (0.0, 2))   # (min intensity, max concurrent systems)
_MAX_FOCUS_FINDINGS = 4


def _by_section(instructions) -> dict[int, list]:
    out: dict[int, list] = defaultdict(list)
    for ins in instructions:
        si = getattr(ins, "section_index", None)
        if si is not None:
            out[si].append(ins)
    return out


def _section_signature(instrs) -> set[tuple[str, str]]:
    """The (target, effect_type) set a section lights — its visual fingerprint for rhyme."""
    return {(i.target, i.effect_type) for i in instrs}


def _carrier_types(instrs) -> frozenset[str]:
    """The chase/carrier effect types present (used for carrier-equality in the rhyme score)."""
    from ..pipeline.weave import CARRIER_ROTATION
    return frozenset({i.effect_type for i in instrs} & set(CARRIER_ROTATION))


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b) if (a | b) else 1.0


def repetition_rhyme(instructions, repetition_map) -> tuple[float | None, list[Finding]]:
    """Mean visual similarity across the occurrences of each recurring label.

    Per label: Jaccard of the `(target, effect_type)` sets between occurrence pairs, plus a
    carrier-equality bonus (all occurrences sharing a carrier is the strongest rhyme signal). The
    score is the mean over labels; None when the show has no recurring labels (neutral)."""
    if not repetition_map:
        return None, []
    by = _by_section(instructions)
    findings: list[Finding] = []
    label_scores: list[float] = []
    for label, indices in repetition_map.items():
        occ = [sorted(indices)[k] for k in range(len(indices)) if sorted(indices)[k] in by]
        if len(occ) < 2:
            continue
        sigs = [_section_signature(by[si]) for si in occ]
        carriers = [_carrier_types(by[si]) for si in occ]
        pairs = [(i, j) for i in range(len(occ)) for j in range(i + 1, len(occ))]
        sims = [_jaccard(sigs[i], sigs[j]) for i, j in pairs]
        # carrier equality: fraction of pairs whose carriers match (empty==empty counts as match)
        carrier_eq = sum(1 for i, j in pairs if carriers[i] == carriers[j]) / len(pairs)
        score = 0.7 * (sum(sims) / len(sims)) + 0.3 * carrier_eq
        label_scores.append(score)
        if score < RHYME_LOW and len(findings) < _MAX_RHYME_FINDINGS:
            findings.append(Finding(
                scope=f"label {label}", severity="warn", metric="musicality:rhyme", objective=False,
                detail=(f"repeated section '{label}' does not rhyme (visual similarity "
                        f"{score:.0%}) — occurrences use different carriers or effect/target sets")))
    if not label_scores:
        return None, []
    return sum(label_scores) / len(label_scores), findings


# -- dynamic-range ------------------------------------------------------------

def _mean_brightness(instrs) -> float:
    vals: list[float] = []
    for i in instrs:
        raw = i.extra_settings.get("C_SLIDER_Brightness")
        try:
            vals.append(float(raw))
        except (TypeError, ValueError):
            vals.append(100.0)               # xLights default (100 = normal) when unset
    return sum(vals) / len(vals) if vals else 0.0


def dynamic_range(instructions, plan) -> tuple[float | None, list[Finding]]:
    """Normalized spread between the quietest and loudest section by mean(brightness × lit
    fraction). Low spread → the whole show sits at one level ('wall-to-wall brightness')."""
    sections = list(getattr(plan, "sections", None) or [])
    if len(sections) < 2:
        return None, []
    by = _by_section(instructions)
    n_groups = len({t for instrs in by.values() for i in instrs for t in [i.target]}) or 1
    weights: list[float] = []
    for si in range(len(sections)):
        instrs = by.get(si, [])
        lit_frac = len({i.target for i in instrs}) / n_groups
        weights.append(_mean_brightness(instrs) * lit_frac)
    active = [w for w in weights if w > 0]
    if len(active) < 2:
        return None, []
    lo, hi = min(active), max(active)
    spread = (hi - lo) / hi if hi > 0 else 0.0
    findings: list[Finding] = []
    if spread < DYNAMIC_LOW:
        findings.append(Finding(
            scope="global", severity="warn", metric="musicality:dynamic-range", objective=False,
            detail=(f"low dynamic range ({spread:.0%}) — sections light nearly the same coverage at "
                    "similar brightness; give quiet sections real restraint so the peak lands")))
    return spread, findings


# -- focus-budget -------------------------------------------------------------

def _budget_for(intensity: float) -> int:
    for lo, cap in _FOCUS_BUDGET:
        if intensity >= lo:
            return cap
    return _FOCUS_BUDGET[-1][1]


def focus_budget(instructions, plan) -> list[Finding]:
    """Flag a section running more concurrent distinct moving-effect systems than its energy earns.

    A 'system' = one distinct moving effect_type (MOTION_EFFECTS) placed in the section; a quiet
    section stacking four different motion effects reads as busy noise, not restraint."""
    sections = list(getattr(plan, "sections", None) or [])
    if not sections:
        return []
    by = _by_section(instructions)
    findings: list[Finding] = []
    for si, sec in enumerate(sections):
        if len(findings) >= _MAX_FOCUS_FINDINGS:
            break
        systems = {i.effect_type for i in by.get(si, []) if i.effect_type in MOTION_EFFECTS}
        intensity = getattr(sec, "intensity", 0.0) or 0.0
        budget = _budget_for(intensity)
        if len(systems) > budget:
            findings.append(Finding(
                scope=f"section {si}", severity="info", metric="musicality:focus", objective=False,
                section_index=si,
                detail=(f"section {si} (intensity {intensity:.2f}) runs {len(systems)} concurrent "
                        f"moving systems (budget {budget}) — thin the motion so the eye has a focus")))
    return findings


def evaluate(instructions, plan, repetition_map=None) -> tuple[int, list[Finding]]:
    """All advisory musicality metrics → (advisory score 0-100, findings). Never gates."""
    findings: list[Finding] = []
    parts: list[float] = []

    rhyme, f_rhyme = repetition_rhyme(instructions, repetition_map)
    findings += f_rhyme
    if rhyme is not None:
        parts.append(rhyme)

    spread, f_dyn = dynamic_range(instructions, plan)
    findings += f_dyn
    if spread is not None:
        parts.append(min(1.0, spread / DYNAMIC_LOW))    # reaching the floor = full marks

    findings += focus_budget(instructions, plan)

    score = round(100 * sum(parts) / len(parts)) if parts else 100
    return score, findings
