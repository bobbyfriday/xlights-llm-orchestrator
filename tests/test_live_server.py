"""Tests for the live SSE server + page (F-I), over loopback on an ephemeral port."""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request

import pytest

from xlights_orchestrator.live_server import LiveProgressServer, render_page
from xlights_orchestrator.progress import CheckpointGate, ProgressBus


@pytest.fixture
def server():
    bus = ProgressBus()
    gate = CheckpointGate(bus)
    srv = LiveProgressServer(bus, gate, title="unit")
    srv.start(open_browser=False)
    try:
        yield srv, bus, gate
    finally:
        srv.stop()


def _get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status, r.read().decode()


def test_page_has_no_placeholders_and_no_external_resources():
    page = render_page("MyShow")
    assert "__TITLE__" not in page and "MyShow" in page
    # zero external resources: no http(s):// or protocol-relative // URLs in the page
    lowered = page.replace("http-equiv", "")
    assert "http://" not in lowered and "https://" not in lowered
    assert "//" not in lowered.replace("<!--", "").replace("-->", "")  # no protocol-relative refs


def test_get_root_serves_substituted_page(server):
    srv, _, _ = server
    status, body = _get(srv.url)
    assert status == 200 and "<title>xLights run unit</title>" in body
    assert "__TITLE__" not in body


def _read_sse_frames(url, n_data, headers=None, timeout=5.0):
    """Open the SSE stream on a raw socket and read line-by-line (returns as data arrives,
    unlike a buffered .read(N) that blocks until N bytes or the 15s heartbeat)."""
    import socket
    from urllib.parse import urlparse
    u = urlparse(url)
    s = socket.create_connection((u.hostname, u.port), timeout=timeout)
    s.settimeout(timeout)
    req = f"GET {u.path} HTTP/1.1\r\nHost: {u.hostname}\r\n"
    for k, v in (headers or {}).items():
        req += f"{k}: {v}\r\n"
    req += "Connection: close\r\n\r\n"
    s.sendall(req.encode())
    buf = b""
    frames = []
    while len(frames) < n_data:
        try:
            chunk = s.recv(512)
        except socket.timeout:
            break
        if not chunk:
            break
        buf += chunk
        while b"\n\n" in buf:
            block, buf = buf.split(b"\n\n", 1)
            if b"data:" in block:
                lines = block.decode(errors="ignore").splitlines()
                id_line = next((ln for ln in lines if ln.startswith("id:")), None)
                data_line = next(ln for ln in lines if ln.startswith("data:"))
                frames.append((id_line, json.loads(data_line[len("data: "):])))
    s.close()
    return frames


def test_sse_frames_and_ordering(server):
    srv, bus, _ = server
    bus.emit("stage", stage="analyze", payload={"phase": "start"})
    bus.emit("section", section=0, payload={"look": "wash"})
    bus.emit("done")
    frames = _read_sse_frames(srv.url + "events", 3)
    assert [f[1]["type"] for f in frames] == ["stage", "section", "done"]
    assert frames[0][0] == "id: 1" and frames[1][0] == "id: 2"   # id ordering


def test_sse_reconnect_replays_since(server):
    srv, bus, _ = server
    bus.emit("stage", stage="analyze")     # 1
    bus.emit("stage", stage="groups")      # 2
    bus.emit("stage", stage="design")      # 3
    frames = _read_sse_frames(srv.url + "events", 1, headers={"Last-Event-ID": "2"})
    assert frames[0][1]["seq"] == 3 and frames[0][1]["stage"] == "design"   # replay after 2


def test_checkpoint_round_trip_bool(server):
    srv, bus, gate = server
    result = {}

    async def go():
        task = asyncio.create_task(gate.wait("interpret", "review", ["proceed", "stop"]))
        # poll the event log for the checkpoint id (server-independent)
        cid = None
        for _ in range(50):
            await asyncio.sleep(0.01)
            cps = [e for e in bus.events() if e.type == "checkpoint"]
            if cps:
                cid = cps[-1].payload["id"]; break
        assert cid is not None
        # POST the action like the browser would
        status = _post(srv.url + "checkpoint/" + cid, {"action": "proceed"})
        assert status == 200
        result["action"] = await task

    asyncio.run(go())
    assert result["action"] == "proceed"
    # a resolution event was emitted
    assert any(e.type == "checkpoint_resolved" for e in bus.events())


def test_checkpoint_refine_returns_decision(server):
    from types import SimpleNamespace

    from xlights_orchestrator.progress import browser_refine_checkpoint
    srv, bus, gate = server
    decide = browser_refine_checkpoint(gate)
    report = SimpleNamespace(objective_score=70, advisory_score=80)
    verdict = SimpleNamespace(score=75, verdict="iterate", revisions=[])
    result = {}

    async def go():
        task = asyncio.create_task(decide(report, verdict, []))
        cid = None
        for _ in range(50):
            await asyncio.sleep(0.01)
            cps = [e for e in bus.events() if e.type == "checkpoint"]
            if cps:
                cid = cps[-1].payload["id"]; break
        _post(srv.url + "checkpoint/" + cid, {"action": "approve"})
        result["decision"] = await task

    asyncio.run(go())
    assert result["decision"].action == "approve"


def test_stale_checkpoint_token_409(server):
    srv, _, _ = server
    status = _post(srv.url + "checkpoint/does-not-exist", {"action": "proceed"})
    assert status == 409


def _post(url, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
