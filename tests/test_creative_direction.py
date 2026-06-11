"""Tests for Stage 2 — the creative brief (rich grounded ShowPlan + plain-language render)."""

from __future__ import annotations

from xlights_orchestrator.agents import director as director_mod
from xlights_orchestrator.agents import generator as generator_mod
from xlights_orchestrator.creative_brief import render_creative_brief
from xlights_orchestrator.music_brief import FeaturedLyricMoment, MusicBrief, LabeledSection
from xlights_orchestrator.show_plan import (
    GroupMotif,
    KeyMoment,
    SectionPlan,
    ShowPalette,
    ShowPlan,
)


# -- schema is additive / back-compat -----------------------------------------

def test_showplan_back_compat():
    # an old-shape plan (only original fields) still validates; new fields default
    p = ShowPlan(sections=[SectionPlan(start_ms=0, end_ms=1000, target_groups=["G"],
                                       effect_family="On", intensity=0.5)])
    assert p.experience == "" and p.group_motifs == {} and p.sections[0].look == ""
    assert p.sections[0].scene_id == "" and p.sections[0].scene_adaptation == ""


# -- render leads with the plain-language experience --------------------------

def test_render_creative_brief_leads_with_experience():
    p = ShowPlan(
        experience="Opens like a single candle, grows to a warm glow, erupts into a celebration.",
        concept="A winter night to triumphant dawn.",
        palette=ShowPalette(name="Winter Fire", colors=["ice blue", "gold", "red"],
                            mapping="cool for the hush, warm/hot for the peaks"),
        group_motifs={"Megatree": GroupMotif(role="the hero/melody", style="sweeps", color="gold")},
        key_moments=[KeyMoment(at_ms=178000, kind="climax", treatment="full-yard burst")],
        sections=[SectionPlan(start_ms=0, end_ms=20000, target_groups=["Megatree"],
                              effect_family="On", intensity=0.1, look="a single warm tree, like a candle",
                              palette=["gold"], effect_types=["Glow"], motion="slow breathe",
                              rationale="piano 44% intro → soft megatree wash", transition="bloom outward")])
    md = render_creative_brief(p)
    assert md.index("Opens like a single candle") < md.index("## Sections")     # experience leads
    assert "a single warm tree, like a candle" in md                            # plain per-section look
    assert "Winter Fire" in md and "Megatree" in md and "the hero/melody" in md
    assert "full-yard burst" in md and "piano 44% intro" in md                  # key moment + grounded why


# -- Director grounding signal ------------------------------------------------

def test_director_input_has_instrumental_grounding():
    brief = MusicBrief(sections=[LabeledSection(start_ms=0, end_ms=1000, label="intro")],
                       featured_lyric_moments=[], narrative_summary=None)        # instrumental
    s = director_mod.render_input(brief, ["G1"], ["On"])
    assert '"INSTRUMENTAL": true' in s.replace("INSTRUMENTAL: true", '"INSTRUMENTAL": true') or \
           "INSTRUMENTAL: true" in s
    assert "title/filename is NOT evidence" in s and "experience" in s          # grounding + plain-language ask


def test_director_input_marks_vocal():
    brief = MusicBrief(sections=[LabeledSection(start_ms=0, end_ms=1000, label="verse")],
                       featured_lyric_moments=[FeaturedLyricMoment(line="x", start_ms=0, end_ms=1)])
    assert "INSTRUMENTAL: false" in director_mod.render_input(brief, ["G1"], ["On"])


# -- Generator follows the brief (concept + motifs) ---------------------------

def test_generator_input_includes_concept_and_motifs():
    sec = SectionPlan(start_ms=0, end_ms=1000, target_groups=["Megatree"], effect_family="On",
                      intensity=0.8, palette=["gold"], effect_types=["Pulse"], motion="drive")
    motifs = {"Megatree": GroupMotif(role="the hero", style="sweeps", color="gold")}
    s = generator_mod.render_input(sec, concept="winter to dawn", motifs=motifs)
    assert "winter to dawn" in s and "the hero" in s and "Pulse" in s
    # back-compat: old call shapes still work
    assert "SECTION PLAN" in generator_mod.render_input(sec)
    assert "SECTION PLAN" in generator_mod.render_input(sec, revision=None)


# -- Scene cookbook plumbing (director picks scenes, generator realizes stacks) --

def test_director_input_asks_for_scenes():
    brief = MusicBrief(sections=[LabeledSection(start_ms=0, end_ms=1000, label="verse")])
    s = director_mod.render_input(brief, ["G1"], ["On"])
    assert "scene_id" in s and "scene_adaptation" in s
    assert "ARCHETYPES" in s                                  # cookbook rows must be cast, not copied


def test_generator_input_realizes_scene():
    sec = SectionPlan(start_ms=0, end_ms=1000, target_groups=["Megatree"], effect_family="On",
                      intensity=0.8, scene_id="SC-02",
                      scene_adaptation="hero=Megatree, bed=SEM_ALL")
    s = generator_mod.render_input(sec)
    assert "SC-02" in s and "hero=Megatree" in s
    assert "T_CHOICE_LayerMethod" in s and "`layer` 0" in s   # blend + layer-order mechanics
    # no scene → no scene note
    plain = SectionPlan(start_ms=0, end_ms=1000, target_groups=["G"], effect_family="On",
                        intensity=0.5)
    assert "cookbook scene" not in generator_mod.render_input(plain)


def test_generator_input_offers_looks_per_effect_type():
    sec = SectionPlan(start_ms=0, end_ms=1000, target_groups=["G"], effect_family="Spirals",
                      intensity=0.6, effect_types=["Spirals", "Twinkle"])
    s = generator_mod.render_input(sec)
    assert "CANDIDATE LOOK IDS by effect type" in s
    assert "Spirals#" in s and "Twinkle#" in s                # looks for every section type


def test_render_creative_brief_shows_scene():
    p = ShowPlan(sections=[SectionPlan(start_ms=0, end_ms=1000, target_groups=["G"],
                                       effect_family="On", intensity=0.5, scene_id="SC-01",
                                       scene_adaptation="hero=Megatree")])
    md = render_creative_brief(p)
    assert "SC-01" in md and "hero=Megatree" in md
