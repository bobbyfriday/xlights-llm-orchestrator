"""F-E slice 7 — the optional LLM fallback for the unresolved tail (spec §3.5)."""

from __future__ import annotations

import asyncio

import pytest

from xlights_orchestrator.agents.layout_classifier import (
    PropRoleGuess,
    PropRoleGuesses,
    classify_tail,
    render_input,
)
from xlights_core.knowledge.layout_classify import CANONICAL_ROLES
from xlights_core.knowledge.layout_semantics import Prop


def _agent(output):
    from pydantic_ai import Agent
    from pydantic_ai.models.test import TestModel
    return Agent(TestModel(custom_output_args=output.model_dump()),
                 output_type=PropRoleGuesses, system_prompt="")


def test_role_literal_matches_canonical_roles():
    from xlights_orchestrator.agents.layout_classifier import Role
    assert set(Role.__args__) == set(CANONICAL_ROLES)


def test_enum_constrained_output_rejects_invented_role():
    # an invented role must fail schema validation
    with pytest.raises(Exception):
        PropRoleGuess(name="x", role="LASER_DRAGON", confidence=0.9)   # noqa — not in the enum


def test_render_input_compact_records():
    props = [Prop(name="Prop A", display_as="Custom", nodes=40, wx=1.2, wy=3.4, groups=["G1"])]
    txt = render_input(props)
    assert "Prop A" in txt and "Custom" in txt and "G1" in txt


def test_batched_call_resolves_several_props():
    props = [Prop(name="P1", display_as="Custom", nodes=40),
             Prop(name="P2", display_as="Custom", nodes=50)]
    guesses = PropRoleGuesses(guesses=[
        PropRoleGuess(name="P1", role="SNOWFLAKE", confidence=0.9),
        PropRoleGuess(name="P2", role="STAR", confidence=0.85),
    ])
    review = asyncio.run(classify_tail(props, agent=_agent(guesses)))
    assert props[0].role == "SNOWFLAKE" and props[1].role == "STAR"
    assert review == []                                    # both confident → no review


def test_low_confidence_and_missing_route_to_review():
    props = [Prop(name="P1", display_as="Custom", nodes=40),
             Prop(name="P2", display_as="Custom", nodes=50)]
    guesses = PropRoleGuesses(guesses=[
        PropRoleGuess(name="P1", role="SNOWFLAKE", confidence=0.4),   # low → review
        # P2 not returned → review
    ])
    review = asyncio.run(classify_tail(props, agent=_agent(guesses)))
    assert set(review) == {"P1", "P2"}


def test_empty_tail_is_noop():
    assert asyncio.run(classify_tail([], agent=_agent(PropRoleGuesses()))) == []
