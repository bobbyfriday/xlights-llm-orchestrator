"""Tests for audio-backed, song-named, clean-slate sequence generation."""

from __future__ import annotations

import asyncio
import functools
from types import SimpleNamespace

import pytest

from xlights_orchestrator.effect_emitter import apply_instructions
from xlights_orchestrator.pipeline.media import prepare_media, safe_name


def run(c):
    return asyncio.run(c)


# -- safe_name ----------------------------------------------------------------

@pytest.mark.parametrize("inp,out", [
    ("mp3/mad russian christmas.mp3", "mad_russian_christmas"),
    ("/x/Wizards in Winter (Remix!).wav", "Wizards_in_Winter_Remix"),
    ("Trans-Siberian.MP3", "Trans_Siberian"),
    ("  ___.mp3", "show"),          # all-separator stem → fallback
    ("café déjà.mp3", "caf_d_j"),  # non-ascii stripped
])
def test_safe_name(inp, out):
    assert safe_name(inp) == out


def test_safe_name_stable():
    once = safe_name("a  b__c.mp3")
    assert once == "a_b_c" and safe_name(once) == once   # idempotent


# -- prepare_media ------------------------------------------------------------

def test_prepare_media_copies_with_safe_name(tmp_path):
    src = tmp_path / "mad russian christmas.mp3"
    src.write_bytes(b"audio-bytes")
    show = tmp_path / "show"; show.mkdir()
    dest = prepare_media(src, show)
    assert dest == show / "mad_russian_christmas.mp3" and dest.read_bytes() == b"audio-bytes"
    # idempotent: same-size copy is reused, not re-copied
    assert prepare_media(src, show) == dest


def test_prepare_media_missing_or_no_folder(tmp_path):
    assert prepare_media(tmp_path / "nope.mp3", tmp_path) is None   # missing source
    assert prepare_media(tmp_path / "x.mp3", None) is None          # no show folder


# -- emitter: animation-only clean-slate (no media via automation) ------------

class _FakeClient:
    """Records new_sequence kwargs; auto-closes like the real client (close-first clean slate)."""
    def __init__(self):
        self.new_seq_kwargs = None
        self.closed = False

    async def new_sequence(self, *, duration_secs, frame_ms=50, media_file=None,
                           view=None, force=False):
        self.new_seq_kwargs = {"media_file": media_file, "force": force}

    async def close_sequence(self, *, force=False, quiet=False):
        self.closed = True

    async def render_all(self):
        return None


def test_emitter_animation_only_clean_slate():
    c = _FakeClient()
    run(apply_instructions(c, [], duration_secs=10, settle_secs=0))
    # animation only (no media via automation — that crashes), force clean-slate, closed first
    assert c.new_seq_kwargs == {"media_file": None, "force": True} and c.closed


# -- offline .xsq audio patch -------------------------------------------------

def test_patch_xsq_media(tmp_path):
    from xlights_orchestrator.pipeline.media import patch_xsq_media
    xsq = tmp_path / "show.xsq"
    xsq.write_text('<xsequence><head><author></author>'
                   '<sequenceType>Animation</sequenceType></head><DisplayElements/></xsequence>')
    assert patch_xsq_media(xsq, "/Users/rob/xlights/song.mp3", 289.4) is True
    text = xsq.read_text()
    assert "<sequenceType>Media</sequenceType>" in text
    assert "<mediaFile>/Users/rob/xlights/song.mp3</mediaFile>" in text
    assert "<sequenceDuration>289.400</sequenceDuration>" in text
    # idempotent: re-patch stays Media (no duplicate tags)
    assert patch_xsq_media(xsq, "/Users/rob/xlights/song.mp3", 289.4) is True
    assert xsq.read_text().count("<sequenceType>") == 1


def test_patch_xsq_media_graceful(tmp_path):
    from xlights_orchestrator.pipeline.media import patch_xsq_media
    assert patch_xsq_media(tmp_path / "nope.xsq", "x.mp3", 1.0) is False     # missing file → no raise
    bad = tmp_path / "bad.xsq"; bad.write_text("<xsequence>no head</xsequence>")
    assert patch_xsq_media(bad, "x.mp3", 1.0) is False                       # no <head> → False
