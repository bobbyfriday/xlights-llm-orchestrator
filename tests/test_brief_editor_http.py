"""HTTP-level tests for the brief editor over a REAL loopback ThreadingHTTPServer (I6).

Hermetic: binds 127.0.0.1 on an ephemeral port, drives with urllib (2s timeouts), no browser.
This exercises the do_GET / do_POST handlers and the on-disk atomic save that the unit-level
`test_brief_editor.py` (render_page/save_brief in isolation) does not.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from xlights_orchestrator.brief_editor import _color_hex_map, _handler, render_page


SCHEMA = {"$defs": {"SectionPlan": {"properties": {
    "target_groups": {"type": "array", "items": {"enum": ["SEM_ALL", "SEM_SNOWFLAKES"]}},
    "palette": {"type": "array", "items": {"enum": ["red", "white"]}},
    "intensity": {"type": "number", "minimum": 0, "maximum": 1},
    "look": {"type": "string"},
}}}}


def _brief():
    return {
        "$schema": "./creative_brief.schema.json",
        "experience": "opens calm",
        "sections": [{"start_ms": 0, "end_ms": 1000, "target_groups": ["SEM_ALL"],
                      "effect_family": "On", "intensity": 0.5, "palette": ["red"], "look": "calm"}],
        "group_motifs": {"SEM_ALL": {"role": "bed"}},   # NOT rendered by the form — must survive
    }


@pytest.fixture
def server(tmp_path):
    """Yield (base_url, brief_path) for a running editor server; closed on teardown."""
    brief_path = tmp_path / "creative_brief.json"
    brief_path.write_text(json.dumps(_brief()))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _handler(brief_path, SCHEMA, _color_hex_map()))
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        yield base, brief_path
    finally:
        httpd.shutdown()
        httpd.server_close()


def _get(url):
    with urllib.request.urlopen(url, timeout=2) as r:
        return r.status, r.headers.get("Content-Type", ""), r.read().decode()


def _post(url, body: bytes, headers=None):
    req = urllib.request.Request(url, data=body, method="POST", headers=headers or {})
    with urllib.request.urlopen(req, timeout=2) as r:
        return r.status, r.read().decode()


# -- GET ----------------------------------------------------------------------

def test_get_root_serves_html_with_embedded_brief(server):
    base, brief_path = server
    status, ctype, body = _get(base + "/")
    assert status == 200
    assert "text/html" in ctype
    assert "opens calm" in body                       # the brief JSON is embedded (__BRIEF__)
    assert "SectionPlan" in body                      # the schema is embedded (__SCHEMA__)
    assert "__BRIEF__" not in body and "__SCHEMA__" not in body   # placeholders replaced


def test_get_unknown_path_404_json(server):
    base, _ = server
    with pytest.raises(urllib.error.HTTPError) as ei:
        _get(base + "/nope")
    assert ei.value.code == 404
    assert json.loads(ei.value.read().decode()) == {}


# -- POST /save ---------------------------------------------------------------

def test_post_save_valid_writes_file(server):
    base, brief_path = server
    edited = _brief()
    edited["sections"][0]["palette"] = ["red", "white"]
    status, body = _post(base + "/save", json.dumps(edited).encode())
    assert status == 200
    assert json.loads(body) == {"ok": True}
    out = json.loads(brief_path.read_text())
    assert list(out)[0] == "$schema"                  # $schema written first
    assert out["sections"][0]["palette"] == ["red", "white"]      # the edit landed
    assert out["group_motifs"] == {"SEM_ALL": {"role": "bed"}}    # unrendered field preserved


def test_post_save_structurally_invalid_400_and_file_untouched(server):
    base, brief_path = server
    before = brief_path.read_text()
    bad = {"sections": "not-a-list"}                  # sections must be a list
    with pytest.raises(urllib.error.HTTPError) as ei:
        _post(base + "/save", json.dumps(bad).encode())
    assert ei.value.code == 400
    err = json.loads(ei.value.read().decode())
    assert "error" in err and len(err["error"]) <= 300
    assert brief_path.read_text() == before           # atomic .tmp-replace never ran


def test_post_save_missing_content_length_400_not_hang(server):
    base, brief_path = server
    before = brief_path.read_text()
    # Content-Length 0 → empty body → json.loads(b"{}") → save_brief({}) → ShowPlan needs sections.
    status_code = None
    try:
        _post(base + "/save", b"", headers={"Content-Length": "0"})
    except urllib.error.HTTPError as exc:
        status_code = exc.code
    assert status_code == 400                          # rejected, did not hang
    assert brief_path.read_text() == before


def test_post_unknown_path_404(server):
    base, _ = server
    with pytest.raises(urllib.error.HTTPError) as ei:
        _post(base + "/elsewhere", b"{}")
    assert ei.value.code == 404


# -- serve()-level schema-missing fallback ------------------------------------

def test_schema_missing_renders_empty_schema():
    """When no sibling schema exists, the page renders with SCHEMA={} (no enums) — proven at the
    render_page composition level the serve() fallback uses (brief_editor.py:209-210)."""
    html = render_page(_brief(), {}, _color_hex_map())
    assert "const BRIEF=" in html
    assert "SCHEMA={}" in html                         # empty-object schema embedded verbatim
