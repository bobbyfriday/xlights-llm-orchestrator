"""A local browser form for editing the creative brief — friendly dropdowns, multi-selects, and
color swatches instead of raw JSON.

Reads `creative_brief.json` + its sibling `creative_brief.schema.json` (the enum vocabulary the
schema carries), serves a one-page form on localhost, and writes the edited brief back on Save —
preserving every field the form doesn't render (group_motifs, key_moments, …) and the `$schema`
key. Stdlib only (http.server); no framework, no CDN.
"""

from __future__ import annotations

import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from xlights_core.knowledge.colors import NAMED_COLORS, _resolve

from .show_plan import ShowPlan


def _color_hex_map() -> dict[str, str]:
    """name -> hex for the color swatches (the schema's palette enum is color NAMES)."""
    return {n: (_resolve(n) or "#888888") for n in NAMED_COLORS}


_PAGE = r"""<!doctype html>
<html><head><meta charset="utf-8"><title>Creative Brief</title>
<style>
 body{font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#0f1115;color:#e6e6e6}
 header{position:sticky;top:0;background:#171a21;padding:12px 20px;border-bottom:1px solid #2a2f3a;
   display:flex;align-items:center;gap:16px;z-index:10}
 h1{font-size:16px;margin:0}
 #status{color:#8fbf7f}
 button{background:#3b82f6;color:#fff;border:0;border-radius:6px;padding:8px 16px;font-size:14px;cursor:pointer}
 button.sec{background:#2a2f3a;padding:4px 10px;font-size:12px}
 main{padding:20px;max-width:900px;margin:0 auto}
 .card{background:#171a21;border:1px solid #2a2f3a;border-radius:10px;padding:16px 18px;margin:0 0 16px}
 .card h2{font-size:14px;margin:0 0 4px;color:#cfe3ff}
 .card .sub{color:#8a93a3;font-size:12px;margin-bottom:12px}
 .f{margin:10px 0}
 .f>label{display:block;font-weight:600;font-size:12px;color:#a9b4c4;margin-bottom:3px}
 select,input[type=text],textarea{width:100%;box-sizing:border-box;background:#0f1115;color:#e6e6e6;
   border:1px solid #2a2f3a;border-radius:6px;padding:6px 8px;font:inherit}
 textarea{min-height:46px;resize:vertical}
 .multi{display:flex;flex-wrap:wrap;gap:6px}
 .chip{display:inline-flex;align-items:center;gap:5px;background:#0f1115;border:1px solid #2a2f3a;
   border-radius:14px;padding:3px 9px;font-size:12px;cursor:pointer;user-select:none}
 .chip.on{background:#1e3a5f;border-color:#3b82f6;color:#fff}
 .pal{display:flex;flex-direction:column;gap:6px}
 .palrow{display:flex;align-items:center;gap:8px}
 .sw{width:20px;height:20px;border-radius:4px;border:1px solid #2a2f3a;flex:none}
 .palrow select{flex:1}
 .rng{display:flex;align-items:center;gap:10px}
 .rng input{flex:1}
 .x{color:#e06b6b;cursor:pointer;font-weight:700;padding:0 4px}
 .muted{color:#8a93a3;font-size:12px}
</style></head>
<body>
<header><h1>Creative Brief</h1><button id="save">Save</button><span id="status"></span>
 <span class="muted" id="path"></span></header>
<main>
 <div class="card">
  <h2>Show</h2>
  <div class="f"><label>experience (what the audience sees/feels)</label><textarea id="experience"></textarea></div>
  <div class="f"><label>concept</label><textarea id="concept"></textarea></div>
  <div class="muted">Advanced show fields (palette, group_motifs, key_moments) are preserved as-is.</div>
 </div>
 <div id="sections"></div>
</main>
<script>
const BRIEF=__BRIEF__, SCHEMA=__SCHEMA__, COLORS=__COLORS__;
const SP=(SCHEMA.$defs&&SCHEMA.$defs.SectionPlan&&SCHEMA.$defs.SectionPlan.properties)||{};
const ORDER=["look","scene_id","scene_adaptation","target_groups","palette","effect_family",
 "effect_types","motion","transition","intensity","rationale","pulse_groups","follow_stem",
 "accent_effect","pulse_on"];
const LONG=new Set(["look","rationale","scene_adaptation","motion","transition"]);
const COLNAMES=Object.keys(COLORS);
const ms=v=>{v=Math.round((v||0)/1000);return Math.floor(v/60)+":"+String(v%60).padStart(2,"0")};

function el(t,a={},...kids){const e=document.createElement(t);for(const k in a){
 if(k==="class")e.className=a[k];else if(k.startsWith("on"))e[k]=a[k];else e.setAttribute(k,a[k]);}
 for(const c of kids)e.append(c);return e;}

function field(sec,name){
 const sch=SP[name]||{}; const wrap=el("div",{class:"f"});
 wrap.append(el("label",{},name));
 if(name==="palette"){wrap.append(paletteWidget(sec));return wrap;}
 if(sch.enum){ // dropdown
  const s=el("select",{onchange:e=>sec[name]=e.target.value});
  for(const o of sch.enum){const opt=el("option",{},o===""?"(none)":o);opt.value=o;
   if((sec[name]||"")===o)opt.selected=true;s.append(opt);}
  wrap.append(s);return wrap;}
 if(sch.type==="array"&&sch.items&&sch.items.enum){ // multi-select chips
  if(!Array.isArray(sec[name]))sec[name]=[];
  const box=el("div",{class:"multi"});
  for(const o of sch.items.enum){const on=sec[name].includes(o);
   const c=el("span",{class:"chip"+(on?" on":"")},o);
   c.onclick=()=>{const i=sec[name].indexOf(o);if(i>=0)sec[name].splice(i,1);else sec[name].push(o);
    c.classList.toggle("on");};box.append(c);}
  wrap.append(box);return wrap;}
 if(sch.type==="number"){ // slider (intensity)
  const lo=sch.minimum??0,hi=sch.maximum??1;const rng=el("div",{class:"rng"});
  const out=el("span",{},String(sec[name]??0));
  const inp=el("input",{type:"range",min:lo,max:hi,step:0.01,value:sec[name]??0,
   oninput:e=>{sec[name]=parseFloat(e.target.value);out.textContent=e.target.value;}});
  rng.append(inp,out);wrap.append(rng);return wrap;}
 // text / textarea
 const inp=LONG.has(name)?el("textarea",{}):el("input",{type:"text"});
 inp.value=sec[name]||"";inp.oninput=e=>sec[name]=e.target.value;
 wrap.append(inp);return wrap;}

function paletteWidget(sec){
 if(!Array.isArray(sec.palette))sec.palette=[];
 const box=el("div",{class:"pal"});
 const draw=()=>{box.innerHTML="";
  sec.palette.forEach((col,i)=>{const row=el("div",{class:"palrow"});
   const sw=el("span",{class:"sw"});sw.style.background=COLORS[col]||col||"#000";
   const s=el("select",{onchange:e=>{sec.palette[i]=e.target.value;sw.style.background=COLORS[e.target.value]||"#000";}});
   for(const n of COLNAMES){const o=el("option",{},n);o.value=n;if(n===col)o.selected=true;s.append(o);}
   const x=el("span",{class:"x",title:"remove"},"×");x.onclick=()=>{sec.palette.splice(i,1);draw();};
   row.append(sw,s,x);box.append(row);});
  const add=el("button",{class:"sec"},"+ color");
  add.onclick=()=>{sec.palette.push(COLNAMES[0]);draw();};box.append(add);};
 draw();return box;}

function render(){
 document.getElementById("experience").value=BRIEF.experience||"";
 document.getElementById("experience").oninput=e=>BRIEF.experience=e.target.value;
 document.getElementById("concept").value=BRIEF.concept||"";
 document.getElementById("concept").oninput=e=>BRIEF.concept=e.target.value;
 const host=document.getElementById("sections");host.innerHTML="";
 (BRIEF.sections||[]).forEach((sec,i)=>{const card=el("div",{class:"card"});
  card.append(el("h2",{},"Section "+(i+1)+"  ·  "+ms(sec.start_ms)+"–"+ms(sec.end_ms)));
  card.append(el("div",{class:"sub"},sec.look||""));
  for(const f of ORDER)if(f in SP||f==="palette")card.append(field(sec,f));
  host.append(card);});}

document.getElementById("save").onclick=async()=>{
 const st=document.getElementById("status");st.textContent="saving…";
 try{const r=await fetch("/save",{method:"POST",body:JSON.stringify(BRIEF)});
  const j=await r.json();st.textContent=r.ok?("✓ saved "+new Date().toLocaleTimeString()):("✗ "+(j.error||"error"));
  st.style.color=r.ok?"#8fbf7f":"#e06b6b";}
 catch(e){st.textContent="✗ "+e;st.style.color="#e06b6b";}};
render();
</script></body></html>"""


def render_page(brief: dict, schema: dict, colors: dict, brief_path: str = "") -> str:
    return (_PAGE
            .replace("__BRIEF__", json.dumps(brief))
            .replace("__SCHEMA__", json.dumps(schema))
            .replace("__COLORS__", json.dumps(colors)))


def save_brief(brief_path: Path, payload: dict) -> None:
    """Validate the posted brief as a ShowPlan (ignoring `$schema`) and write it back atomically,
    preserving the `$schema` key. Raises ValueError on invalid content."""
    body = {k: v for k, v in payload.items() if k != "$schema"}
    ShowPlan.model_validate(body)                     # raises if the edit is structurally invalid
    out = dict(payload)
    if "$schema" not in out:
        out = {"$schema": "./creative_brief.schema.json", **out}
    tmp = brief_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(out, indent=1))
    tmp.replace(brief_path)


def _handler(brief_path: Path, schema: dict, colors: dict):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # quiet
            pass

        def _send(self, code, body, ctype="application/json"):
            data = body.encode() if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                brief = json.loads(brief_path.read_text())
                self._send(200, render_page(brief, schema, colors, str(brief_path)), "text/html; charset=utf-8")
            else:
                self._send(404, "{}")

        def do_POST(self):
            if self.path != "/save":
                self._send(404, "{}"); return
            n = int(self.headers.get("Content-Length", 0))
            try:
                payload = json.loads(self.rfile.read(n) or b"{}")
                save_brief(brief_path, payload)
                self._send(200, json.dumps({"ok": True}))
            except Exception as exc:  # noqa: BLE001 — report to the form
                self._send(400, json.dumps({"error": str(exc)[:300]}))
    return Handler


def serve(brief_path, *, port: int = 0, open_browser: bool = True):
    """Serve the editor for `brief_path` (its sibling `creative_brief.schema.json` supplies the
    dropdown vocab) until Ctrl+C. A missing schema → text-only form (no enums)."""
    brief_path = Path(brief_path)
    schema_path = brief_path.with_name("creative_brief.schema.json")
    schema = json.loads(schema_path.read_text()) if schema_path.exists() else {}
    colors = _color_hex_map()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), _handler(brief_path, schema, colors))
    url = f"http://127.0.0.1:{httpd.server_address[1]}/"
    print(f"Editing {brief_path}\nOpen {url} (Ctrl+C to stop). Edits save back to the file.")
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
    finally:
        httpd.server_close()
