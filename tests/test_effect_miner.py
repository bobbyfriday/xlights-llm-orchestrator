"""Tests for the per-effect corpus miner (hermetic: synthetic .xsq files in tmp_path)."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from xlights_core.knowledge import effect_miner as em
from xlights_core.knowledge.xsq_extractor import iter_corpus

SPIR_A = "E_SLIDER_Spirals_Count=1,E_SLIDER_Spirals_Rotation=20,E_SLIDER_Spirals_Thickness=50,E_TEXTCTRL_Spirals_Movement=1.0,E_CHECKBOX_Spirals_3D=1"
SPIR_B = "E_SLIDER_Spirals_Count=1,E_SLIDER_Spirals_Rotation=-20,E_SLIDER_Spirals_Thickness=50,E_TEXTCTRL_Spirals_Movement=-1.0,E_CHECKBOX_Spirals_3D=1,B_CHOICE_BufferTransform=Rotate 180"
SPIR_VC = ("E_SLIDER_Spirals_Count=2,E_SLIDER_Spirals_Thickness=10,E_TEXTCTRL_Spirals_Movement=0,"
           "E_VALUECURVE_Spirals_Rotation=Active=TRUE|Id=ID_VALUECURVE_Spirals_Rotation|Type=Ramp|Min=-300.00|Max=300.00|P1=-300.00|P2=300.00|RV=TRUE|")
WARP = "E_CHOICE_Warp_Type=water drops,T_CHOICE_LayerMethod=Normal"
RIPPLE = "E_CHOICE_Ripple_Object_To_Draw=Circle"
PAL = "C_BUTTON_Palette1=#FF0000,C_CHECKBOX_Palette1=1,C_BUTTON_Palette2=#000000,C_CHECKBOX_Palette2=1,C_SLIDER_SparkleFrequency=40"


def make_xsq(effects, *, author="", jukebox=True, song="Test Song", version="2023.20"):
    """effects: list of (model, layer, type, start_ms, end_ms, settings_ref) — refs index `db`."""
    db = [SPIR_A, SPIR_B, SPIR_VC, WARP, RIPPLE]
    models: dict[str, dict[int, list[str]]] = {}
    for model, layer, typ, s, e, ref in effects:
        models.setdefault(model, {}).setdefault(layer, []).append(
            f'<Effect ref="{ref}" name="{typ}" protected="0" selected="0" startTime="{s}" endTime="{e}" palette="0"/>')
    model_xml = []
    for model, layers in models.items():
        lay = "".join(f"<EffectLayer>{''.join(layers.get(i, []))}</EffectLayer>" for i in range(max(layers) + 1))
        model_xml.append(f'<Element type="model" name="{model}">{lay}</Element>')
    beats = "".join(f'<Effect label="" startTime="{t}" endTime="{t + 500}"/>' for t in range(0, 8000, 500))
    secs = '<Effect label="Verse" startTime="0" endTime="4000"/><Effect label="Chorus" startTime="4000" endTime="8000"/>'
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<xsequence BaseChannel="0" ChanCtrlBasic="0" ChanCtrlColor="0" FixedPointTiming="1" ModelBlending="true">
  <head><version>{version}</version><author>{author}</author><song>{song}</song><sequenceDuration>8.0</sequenceDuration></head>
  <nextid value="1"/>{'<Jukebox/>' if jukebox else ''}
  <ColorPalettes><ColorPalette>{PAL}</ColorPalette></ColorPalettes>
  <EffectDB>{''.join(f'<Effect id="{i}">{s}</Effect>' for i, s in enumerate(db))}</EffectDB>
  <ElementEffects>
    <Element type="timing" name="Beats"><EffectLayer>{beats}</EffectLayer></Element>
    <Element type="timing" name="Structure"><EffectLayer>{secs}</EffectLayer></Element>
    {''.join(model_xml)}
  </ElementEffects>
</xsequence>"""


@pytest.fixture
def corpus(tmp_path: Path):
    # seq1: a mirror twin on the tree (layer 0 + 1), Warp on top at layer 0 over a chorus twin; ripple bed
    seq1 = make_xsq([
        ("Mega Tree", 1, "Spirals", 0, 2000, 0), ("Mega Tree", 2, "Spirals", 0, 2000, 1),
        ("Mega Tree", 0, "Warp", 4000, 8000, 3), ("Mega Tree", 1, "Spirals", 4000, 8000, 0),
        ("Mega Tree", 2, "Spirals", 4000, 8000, 1), ("Mega Tree", 3, "Ripple", 4000, 8000, 4),
        ("Candy Cane 1", 0, "Spirals", 1000, 1500, 0),
    ], song="Song One")
    # seq2: a curved single on a matrix; also a byte-identical copy packaged as .xsqz (must be dropped)
    seq2 = make_xsq([("Matrix1", 0, "Spirals", 0, 4000, 2)], song="Song Two")
    (tmp_path / "one.xsq").write_text(seq1)
    (tmp_path / "two.xsq").write_text(seq2)
    pkg = tmp_path / "pkg" / "two copy.xsqz"
    pkg.parent.mkdir()
    with zipfile.ZipFile(pkg, "w") as zf:
        zf.writestr("__MACOSX/Sequences/._two.xsq", "junk")
        zf.writestr("Sequences/two.xsq", seq2)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"root": str(tmp_path), "sequences": [
        {"path": "one.xsq", "song": "Song One", "sequencer": "A"},
        {"path": "two.xsq", "song": "Song Two", "sequencer": "B"},
        {"path": "pkg/two copy.xsqz", "song": "Song Two", "sequencer": "C"},
        {"path": "missing.xsq", "song": "Nope"},
    ]}))
    return manifest


def test_manifest_loads_and_reports_missing(corpus):
    m = em.load_manifest(corpus)
    assert [e.name for e in m.entries] == ["one.xsq", "two.xsq", "pkg/two copy.xsqz"]
    assert m.missing == ["missing.xsq"]


def test_package_member_is_read_and_identical_file_dropped(corpus):
    m = em.load_manifest(corpus)
    seqs = list(em.iter_sequences(m))
    assert [e.name for e, _, _ in seqs] == ["one.xsq", "two.xsq"]       # the .xsqz copy is a duplicate
    facts = em.mine_effect("Spirals", m)
    assert facts.n_sequences == 2 and facts.n_songs == 2 and facts.duplicates_dropped == 1
    assert facts.missing == ["missing.xsq"]


def test_placements_context_and_breadth(corpus):
    facts = em.mine_effect("Spirals", em.load_manifest(corpus))
    assert len(facts.placements) == 6
    tree = [p for p in facts.placements if p.model == "Mega Tree"]
    assert {p.cls for p in tree} == {"megatree"}
    cane = next(p for p in facts.placements if p.model.startswith("Candy"))
    assert cane.cls == "cane" and cane.beats == 1 and cane.section == "Verse" and cane.dur_s == 0.5
    chorus = [p for p in tree if p.start_ms == 4000]
    assert all(p.section == "Chorus" and p.beats == 8 for p in chorus)
    assert all(p.colors == ["#FF0000", "#000000"] and p.sparkles for p in facts.placements)
    # breadth: the curved placement is one sequence / one song
    curved = [p for p in facts.placements if "E_VALUECURVE_Spirals_Rotation" in p.settings]
    assert em._breadth(curved) == "1 seq / 1 song"


def test_stack_orientation_layer0_is_top(corpus):
    facts = em.mine_effect("Spirals", em.load_manifest(corpus))
    me_layer = {p.key: p.layer for p in facts.placements}
    above = {s.other_type for s in facts.pairs if s.other_layer < me_layer[s.me]}
    below = {s.other_type for s in facts.pairs if s.other_layer > me_layer[s.me]}
    assert "Warp" in above and "Warp" not in below
    assert "Ripple" in below and "Ripple" not in above
    twins = [s for s in facts.pairs if s.other_type == "Spirals"]
    assert len(twins) == 4                                   # two twins, each counted from both sides


def test_render_block_has_every_section_and_breadth(corpus):
    facts = em.mine_effect("Spirals", em.load_manifest(corpus), mined_on="2026-01-01")
    md = em.render_facts(facts)
    for h in ("### Where it is placed", "### Dials observed", "### Value curves", "### Palette habits",
              "### Duration", "### Stacking"):
        assert h in md
    assert "**6 placements" in md and "2 community sequences, 2 distinct songs" in md
    assert "Song One (A) 5" in md                             # sources are labelled by song and sequencer
    assert "`Rotation` (slider)" in md and "curved 17% · 1 seq / 1 song" in md
    assert "Warp 2 Normal" in md                              # above both chorus layers, with its blend
    assert "buffer transform differs 100%" in md and "`Rotation` (slider) opposite sign 100%" in md
    assert "Type=Ramp|Min=-300.00|Max=300.00|P1=-300.00|P2=300.00" in md


def test_splice_replaces_facts_and_keeps_craft(tmp_path, corpus):
    facts = em.mine_effect("Spirals", em.load_manifest(corpus))
    f = tmp_path / "Spirals.md"
    f.write_text("# Spirals\n\nintro line\n\n---\n\n## Corpus facts\n\nOLD FACTS\n\n---\n\n## Craft\n\n### Identity and role\n\nkeep me\n")
    em.write_effect_file(f, facts)
    md = f.read_text()
    assert "OLD FACTS" not in md and "keep me" in md and "intro line" in md
    assert md.count("## Corpus facts") == 1 and md.count("## Craft") == 1
    assert md.index("## Corpus facts") < md.index("---\n\n## Craft") < md.index("keep me")
    # a fresh file gets the craft skeleton
    g = tmp_path / "Warp.md"
    em.write_effect_file(g, em.mine_effect("Warp", em.load_manifest(corpus)))
    assert "### Anchors (starting points, not a menu)" in g.read_text() and "No placements" not in g.read_text()


def test_no_placements_renders_a_note(corpus):
    md = em.render_facts(em.mine_effect("Fireworks", em.load_manifest(corpus)))
    assert "No placements of Fireworks" in md


def test_iter_corpus_skips_our_own_authorless_files(tmp_path):
    (tmp_path / "community.xsq").write_text(make_xsq([], author="", jukebox=True))
    (tmp_path / "storms.xsq").write_text(make_xsq([], author="John Storms", jukebox=False))
    (tmp_path / "ours.xsq").write_text(make_xsq([], author="", jukebox=False, version="2026.19"))
    (tmp_path / "tool.xsq").write_text(make_xsq([], author="xlight-autosequencer", jukebox=False))
    assert [p.name for p in iter_corpus(tmp_path)] == ["community.xsq", "storms.xsq"]


REAL = Path("/Users/rob/xlights")


@pytest.mark.skipif(not REAL.exists(), reason="show folder not present")
def test_real_corpus_manifest_resolves():
    m = em.load_manifest()
    assert not m.missing, m.missing
    assert len(m.entries) == 22


# -- the preset catalog from the manifest, with stable look ids ----------------------------------

def test_build_catalog_from_manifest_keeps_ids_stable_and_appends(tmp_path):
    from xlights_core.knowledge.xsq_extractor import build_catalog
    # first mine: two files (one.xsq twice as a package copy is deduped) → Spirals signatures A, B
    first = tmp_path / "m1.json"
    (tmp_path / "a.xsq").write_text(make_xsq([("Mega Tree", 0, "Spirals", 0, 2000, 0)], song="A"))
    (tmp_path / "b.xsq").write_text(make_xsq([("Mega Tree", 0, "Spirals", 0, 2000, 1)], song="B"))
    first.write_text(json.dumps({"root": str(tmp_path), "sequences": [
        {"path": "a.xsq", "song": "A"}, {"path": "b.xsq", "song": "B"}]}))
    cat1, _ = build_catalog(manifest=first)
    ids1 = {tuple(lk.key_signature): lk.look_id for lk in cat1.looks_by_type["Spirals"]}
    assert cat1.meta["files"] == 2 and cat1.meta["corpus"] == str(first)
    # second mine adds a file with a NEW signature (the value-curved spiral) and more of signature A
    (tmp_path / "c.xsq").write_text(make_xsq([("Matrix1", 0, "Spirals", 0, 4000, 2),
                                              ("Matrix1", 1, "Spirals", 0, 4000, 0)], song="C"))
    second = tmp_path / "m2.json"
    second.write_text(json.dumps({"root": str(tmp_path), "sequences": [
        {"path": "a.xsq", "song": "A"}, {"path": "b.xsq", "song": "B"}, {"path": "c.xsq", "song": "C"}]}))
    cat2, _ = build_catalog(manifest=second, previous=cat1)
    ids2 = {tuple(lk.key_signature): lk.look_id for lk in cat2.looks_by_type["Spirals"]}
    for sig, lid in ids1.items():
        assert ids2[sig] == lid                                   # old signatures keep their ids
    new_sigs = set(ids2) - set(ids1)
    assert len(new_sigs) == 1
    top = max(int(l.rsplit("#", 1)[1]) for l in ids1.values())
    assert ids2[next(iter(new_sigs))] == f"Spirals#{top + 1}"   # appended, not renumbered
    counts = {lk.look_id: lk.count for lk in cat2.looks_by_type["Spirals"]}
    assert counts[ids1[next(s for s in ids1 if s in {tuple(sorted(k for k, _ in __import__('xlights_core.knowledge.settings', fromlist=['parse_settings']).parse_settings(SPIR_A)))})]] == 2
    assert cat2.meta["dropped_looks"] == 0
    # without `previous`, ids come in signature order (the old behaviour)
    cat3, _ = build_catalog(manifest=second)
    assert [lk.look_id for lk in cat3.looks_by_type["Spirals"]] == ["Spirals#0", "Spirals#1", "Spirals#2"]
