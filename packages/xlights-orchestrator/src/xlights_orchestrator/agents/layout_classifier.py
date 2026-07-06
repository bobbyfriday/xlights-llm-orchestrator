"""Optional LLM fallback for the unresolved classification tail (F-E, spec §3.5).

The deterministic steps 1–4 resolve most props; a residual tail (bare Custom props with no name or
group clue) goes here — ONE batched, enum-constrained call. The `role` field is a `Literal` over the
16 canonical roles, so an invented role is a schema failure, not a silent bad group. Any guess below
0.8 confidence, and every prop the LLM doesn't return, still goes to the review queue. Fully
optional: `--no-llm` or no key → the deterministic tail (CUSTOM_PROP + review). Keeps xlights-core
LLM-free (this lives in the orchestrator).
"""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field

from xlights_core.knowledge.layout_classify import CANONICAL_ROLES

from ..models import build_agent

# The enum-constrained role literal (built from the single source of truth in xlights-core).
Role = Literal[
    "MEGA_TREE", "MINI_TREE", "ARCH", "CANE", "ICICLES", "STAR", "SPINNER", "MATRIX",
    "WINDOW", "OUTLINE", "FLOOD", "SINGING_FACE", "SIGN", "PATH", "SNOWFLAKE", "CUSTOM_PROP",
]

# Guard: the literal must stay in lockstep with the canonical roles.
assert set(Role.__args__) == set(CANONICAL_ROLES), "Role literal drifted from CANONICAL_ROLES"


class PropRoleGuess(BaseModel):
    name: str
    role: Role
    confidence: float = 0.5
    rationale: str = ""


class PropRoleGuesses(BaseModel):
    guesses: list[PropRoleGuess] = Field(default_factory=list)


_PROMPT = (
    "You classify unlabeled Christmas-light props into ROLES. You get a compact record per prop "
    "(name, DisplayAs, node count, world position, any user-group names). Assign each the single "
    "best role from the allowed enum ONLY. Use the name and group names as the strongest clues; use "
    "node count + DisplayAs for geometry (a big dense grid is a MATRIX; a small point cluster is a "
    "CUSTOM_PROP). If you are unsure, return CUSTOM_PROP with a low confidence — do NOT guess a "
    "specific role you can't justify. Set confidence in [0,1]: >=0.8 only when the clue is strong."
)


def layout_classifier_agent():
    return build_agent("classifier", output_type=PropRoleGuesses, system_prompt=_PROMPT)


def render_input(props) -> str:
    """A compact record per unresolved prop (spec §3.5)."""
    records = [
        {
            "name": p.name,
            "display_as": p.display_as,
            "nodes": p.nodes,
            "pos": [round(p.wx, 1), round(p.wy, 1)],
            "groups": p.groups,
        }
        for p in props
    ]
    return (
        "Classify these unlabeled props (return one guess per name, role from the enum only):\n"
        + json.dumps(records, indent=1)
    )


async def classify_tail(props, *, agent=None, min_confidence: float = 0.8):
    """Resolve the unresolved tail with ONE batched call. Applies each guess to the matching Prop
    (role + confidence). Returns the list of names that STILL need review: a guess below
    `min_confidence`, and any prop the LLM did not return. Pure state mutation on `props`.

    Callers pass `--no-llm`/no-key handling upstream — this is only invoked when the LLM runs."""
    if not props:
        return []
    agent = agent or layout_classifier_agent()
    from xlights_core.knowledge.layout_classify import capability
    out = (await agent.run(render_input(props))).output
    by_name = {p.name: p for p in props}
    returned: set[str] = set()
    review: list[str] = []
    for guess in out.guesses:
        p = by_name.get(guess.name)
        if p is None:
            continue
        returned.add(guess.name)
        p.role = guess.role
        p.confidence = guess.confidence
        p.res = capability(p.role, p.nodes, p.string_type)
        if guess.confidence < min_confidence:
            review.append(guess.name)
    # every prop the LLM didn't return stays unresolved → review
    review.extend(n for n in by_name if n not in returned)
    return sorted(set(review))
