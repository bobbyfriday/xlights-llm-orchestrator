"""Live browser progress surface — stdlib-only SSE server + self-contained page (F-I).

Extends the ``brief_editor`` stdlib-browser pattern (``http.server``, no framework, no CDN): a
``ThreadingHTTPServer`` on ``127.0.0.1`` port 0, daemon threads, serving a self-contained HTML
page and a Server-Sent-Events stream fed by the ``ProgressBus``. Browser checkpoints
(approve/edit/stop) POST back to ``/checkpoint/<id>`` and resolve the ``CheckpointGate`` without
parking the pipeline's event loop.

SSE over long-poll (decision 13): on localhost with one viewer the only cost is a pinned thread
per client, and the built-in ``EventSource`` gives auto-reconnect + ``Last-Event-ID`` replay for
free. Responses omit ``Content-Length`` and set ``text/event-stream`` + ``no-cache``.

Security: binds loopback only, no state-changing GET route, checkpoint ids are single-use random
tokens.
"""

from __future__ import annotations

import json
import logging
import queue
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

log = logging.getLogger(__name__)

_HEARTBEAT_S = 15.0        # forces a write so a dead/closed client's handler thread exits


# -- the page (a module constant + placeholder substitution; zero external resources) ---------

_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>xLights run __TITLE__</title>
<style>
 body{font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#12141a;color:#e6e6e6}
 header{padding:10px 16px;background:#1b1e27;border-bottom:1px solid #2a2e3a}
 h1{font-size:15px;margin:0;font-weight:600}
 main{padding:16px;max-width:960px;margin:0 auto;display:grid;gap:16px}
 .card{background:#1b1e27;border:1px solid #2a2e3a;border-radius:8px;padding:12px 14px}
 .card h2{font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:#8a90a0;margin:0 0 8px}
 #stages{display:flex;flex-wrap:wrap;gap:6px}
 .stage{padding:4px 10px;border-radius:14px;background:#252a36;color:#aab;font-size:12px}
 .stage.active{background:#3355dd;color:#fff}
 .stage.done{background:#2a5a3a;color:#cfe}
 #sections{display:grid;grid-template-columns:repeat(auto-fill,minmax(70px,1fr));gap:6px}
 .sec{background:#252a36;border-radius:6px;padding:6px;text-align:center;font-size:11px}
 svg{background:#12141a;border-radius:6px}
 #rev{max-height:220px;overflow:auto;font-family:ui-monospace,monospace;font-size:12px}
 #rev div{padding:2px 0;border-bottom:1px solid #23262f}
 #cp{display:none;background:#2a2030;border-color:#5a3a6a}
 #cp.show{display:block}
 button{font:inherit;padding:6px 14px;margin-right:8px;border:0;border-radius:6px;cursor:pointer;color:#fff}
 .go{background:#3355dd}.stop{background:#aa3344}.keep{background:#557755}
 pre{white-space:pre-wrap;background:#12141a;padding:8px;border-radius:6px;max-height:200px;overflow:auto}
 #status{color:#8a90a0;font-size:12px}
</style></head><body>
<header><h1>xLights run <span id="title">__TITLE__</span> · <span id="status">connecting…</span></h1></header>
<main>
 <div class="card"><h2>Stages</h2><div id="stages"></div></div>
 <div class="card"><h2>Sections</h2><div id="sections"></div></div>
 <div class="card"><h2>QA score (per refine iteration)</h2>
   <svg id="spark" width="920" height="80" viewBox="0 0 920 80"><polyline id="line" fill="none" stroke="#5b8cff" stroke-width="2"/></svg>
   <div id="subs"></div></div>
 <div class="card" id="cp"><h2>Checkpoint</h2><pre id="cpbody"></pre><div id="cpbtns"></div></div>
 <div class="card"><h2>Refine log</h2><div id="rev"></div></div>
</main>
<script>
const STAGES=["analyze","groups","interpret","design","generate","apply","refine","finalize"];
const st={}, sd=document.getElementById("stages");
STAGES.forEach(s=>{const e=document.createElement("span");e.className="stage";e.textContent=s;e.id="stg-"+s;st[s]=e;sd.appendChild(e);});
const secEl=document.getElementById("sections"), revEl=document.getElementById("rev");
const scores=[];
function setStatus(t){document.getElementById("status").textContent=t;}
function drawSpark(){
  if(!scores.length)return;
  const w=920,h=80,n=scores.length,mx=Math.max(1,n-1);
  const pts=scores.map((v,i)=>{const x=(i/mx)*(w-10)+5;const y=h-5-(v/100)*(h-10);return x+","+y;});
  document.getElementById("line").setAttribute("points",pts.join(" "));
}
function addSection(i,p){
  let e=document.getElementById("sec-"+i);
  if(!e){e=document.createElement("div");e.className="sec";e.id="sec-"+i;secEl.appendChild(e);}
  e.textContent="§"+i+" "+(p.look||"");e.title=(p.look||"")+" ["+p.start_ms+"–"+p.end_ms+"ms]";
}
function addRev(p){
  const d=document.createElement("div");
  const j=p.judge?(" judge "+p.judge.score+"/"+p.judge.verdict):"";
  d.textContent="iter "+p.iteration+" ["+(p.kind||"")+"] "+(p.human_decision||"")+j+
    (p.obj_delta!=null?(" Δ"+p.obj_delta):"")+(p.reverted?" (reverted)":"");
  revEl.insertBefore(d,revEl.firstChild);
}
function showCheckpoint(p){
  const cp=document.getElementById("cp"), body=document.getElementById("cpbody"), btns=document.getElementById("cpbtns");
  cp.classList.add("show");body.textContent=p.body_md||p.kind;btns.innerHTML="";
  (p.options||["proceed","stop"]).forEach(opt=>{
    const b=document.createElement("button");
    b.textContent=opt;b.className=opt==="stop"?"stop":(opt==="keep"?"keep":"go");
    b.onclick=()=>{fetch("/checkpoint/"+p.id,{method:"POST",body:JSON.stringify({action:opt})})
      .then(()=>{cp.classList.remove("show");});};
    btns.appendChild(b);
  });
}
function connect(){
  const es=new EventSource("/events");
  es.onopen=()=>setStatus("live");
  es.onerror=()=>setStatus("reconnecting…");
  es.onmessage=(e)=>{
    let ev;try{ev=JSON.parse(e.data);}catch(_){return;}
    const p=ev.payload||{};
    if(ev.type==="stage"){
      const el=st[ev.stage];if(el){if(p.phase==="start"){el.className="stage active";}else if(p.phase==="end"){el.className="stage done";}}
    }else if(ev.type==="section"){addSection(ev.section,p);}
    else if(ev.type==="score"){if(p.kind!=="finalize"||scores.length===0){scores.push(p.objective);drawSpark();}
      document.getElementById("subs").textContent="objective "+p.objective+" · advisory "+p.advisory;}
    else if(ev.type==="refine"){addRev(p);}
    else if(ev.type==="checkpoint"){showCheckpoint(p);}
    else if(ev.type==="checkpoint_resolved"){document.getElementById("cp").classList.remove("show");}
    else if(ev.type==="done"){setStatus("done");}
  };
}
connect();
</script></body></html>
"""


def render_page(title: str = "") -> str:
    import html
    return _PAGE.replace("__TITLE__", html.escape(title or "in progress"))


def _handler_factory(bus, gate, title):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # quiet
            pass

        # -- helpers --
        def _send(self, code, body, ctype="application/json"):
            data = body.encode() if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        # -- routes --
        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                self._send(200, render_page(title), "text/html; charset=utf-8")
            elif path == "/events":
                self._sse()
            elif path == "/revlog":
                self._revlog()
            else:
                self._send(404, "{}")

        def do_POST(self):
            path = self.path.split("?", 1)[0]
            if path.startswith("/checkpoint/") and gate is not None:
                cid = path[len("/checkpoint/"):]
                n = int(self.headers.get("Content-Length", 0))
                try:
                    payload = json.loads(self.rfile.read(n) or b"{}")
                except Exception:  # noqa: BLE001 — malformed body → bad request
                    self._send(400, json.dumps({"error": "bad json"})); return
                action = payload.get("action", "")
                if gate.resolve(cid, action):
                    self._send(200, json.dumps({"ok": True}))
                else:
                    self._send(409, json.dumps({"error": "stale or unknown checkpoint"}))
            else:
                self._send(404, "{}")

        # -- SSE stream --
        def _sse(self):
            since = int(self.headers.get("Last-Event-ID", 0) or 0)
            q = bus.subscribe(since=since)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()                              # NOTE: no Content-Length (streaming)
            try:
                while True:
                    try:
                        ev = q.get(timeout=_HEARTBEAT_S)
                    except queue.Empty:
                        self.wfile.write(b": hb\n\n")       # heartbeat forces a write → detect close
                        self.wfile.flush()
                        continue
                    frame = f"id: {ev.seq}\ndata: {json.dumps(ev.to_dict())}\n\n".encode()
                    self.wfile.write(frame)
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, ValueError):
                pass                                        # client closed → end the handler thread
            finally:
                bus.unsubscribe(q)

        def _revlog(self):
            params = dict(p.split("=", 1) for p in (self.path.split("?", 1)[1].split("&")
                          if "?" in self.path else []) if "=" in p)
            tail = int(params.get("tail", 20))
            refine = [e.to_dict() for e in bus.events() if e.type == "refine"][-tail:]
            self._send(200, json.dumps(refine))
    return Handler


class LiveProgressServer:
    """Serves the live page + SSE stream on a daemon thread. ``start`` opens the browser and
    returns the URL; ``stop`` shuts down and closes the socket."""

    def __init__(self, bus, gate=None, *, port: int = 0, title: str = "") -> None:
        self.bus = bus
        self.gate = gate
        self._httpd = ThreadingHTTPServer(("127.0.0.1", port), _handler_factory(bus, gate, title))
        self._httpd.daemon_threads = True                  # handler threads never block shutdown
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self._httpd.server_address[1]}/"

    def start(self, open_browser: bool = True) -> str:
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        if open_browser:
            threading.Timer(0.4, lambda: webbrowser.open(self.url)).start()
        return self.url

    def stop(self) -> None:
        try:
            self._httpd.shutdown()
            self._httpd.server_close()
        except Exception as exc:  # noqa: BLE001 — teardown is best-effort
            log.debug("live server stop failed: %s", exc)
