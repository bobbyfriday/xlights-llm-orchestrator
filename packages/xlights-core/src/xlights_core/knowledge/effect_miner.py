"""Per-effect corpus miner: the **Corpus facts** block of an `xlo-effects` skill file.

Reads the community corpus named by `corpus_manifest.json` (plain `.xsq` or `.xsqz`/`.zip`
packages, byte-identical files dropped), collects every placement of ONE effect type with its
context (prop, layer, duration in seconds and beats, section label, settings, palette, and the
effects that overlap it on the same model), and renders the facts as markdown. Every share
carries its *breadth* (how many sequences / songs it occurs in) so one dense sequencer's habit
never reads as the community's.

Layer orientation: in an `.xsq`, the first `<EffectLayer>` is the TOP layer (xLights composites
bottom → top), so a partner with a smaller layer index sits ABOVE the mined effect.

Usage:  xlo mine-effect <Type> [--write] [--json <path>]
"""

from __future__ import annotations

import hashlib
import json
import re
import statistics
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from .settings import parse_settings

DEFAULT_MANIFEST = Path(__file__).parent / "corpus_manifest.json"
FACTS_HEADING = "## Corpus facts"
CRAFT_HEADING = "## Craft"
CRAFT_SECTIONS = (
    "Identity and role", "Thematic fit", "Anchors (starting points, not a menu)",
    "Layering recipes", "Value curves", "Prop fit and render style", "Timing", "Exemplars",
    "Anti-patterns", "What code can realize today",
)

# Prop class from a foreign layout's model name (first keyword wins).
_PROP_CLASSES: tuple[tuple[str, str], ...] = (
    ("mega", "megatree"), ("tree", "tree"), ("matrix", "matrix"), ("p10", "matrix"), ("p5", "matrix"),
    ("cane", "cane"), ("arch", "arch"), ("spinner", "spinner"), ("star", "star"),
    ("snowflake", "snowflake"), ("flake", "snowflake"), ("wreath", "wreath"), ("window", "window"),
    ("roof", "roofline"), ("eave", "roofline"), ("outline", "roofline"), ("ridge", "roofline"),
    ("icicle", "icicle"), ("pole", "pole"), ("column", "pole"), ("pillar", "pole"), ("stake", "stake"),
    ("bush", "bush"), ("whole", "group_all"), ("entire", "group_all"), ("all", "group_all"),
    ("group", "group"), ("house", "house"), ("pixel", "pixels"), ("face", "face"),
    ("tombstone", "tombstone"), ("pumpkin", "pumpkin"), ("candle", "candle"), ("present", "present"),
    ("gift", "present"), ("fence", "fence"), ("flood", "flood"),
)
_CONTEXT_KEYS = ("B_CHOICE_BufferStyle", "B_CHOICE_BufferTransform", "T_CHOICE_LayerMethod",
                 "T_TEXTCTRL_Fadein", "T_TEXTCTRL_Fadeout", "T_CHOICE_In_Transition_Type",
                 "T_CHOICE_Out_Transition_Type", "B_SLIDER_Blur")


def prop_class(model_name: str) -> str:
    n = model_name.lower()
    for key, cls in _PROP_CLASSES:
        if key in n:
            return cls
    return "other"


# -- manifest ---------------------------------------------------------------------------------

@dataclass(frozen=True)
class CorpusEntry:
    path: Path                       # resolved; a .xsq, or a .xsqz/.zip holding one
    song: str
    sequencer: str = ""
    weight: float = 1.0
    exemplary_for: tuple[str, ...] = ()
    rel: str = ""                    # the manifest's own path string (unique; two files may share a basename)

    @property
    def name(self) -> str:
        return self.rel or self.path.name


@dataclass
class Manifest:
    root: Path
    entries: list[CorpusEntry]
    missing: list[str] = field(default_factory=list)


def load_manifest(path: str | Path = DEFAULT_MANIFEST, *, root: str | Path | None = None) -> Manifest:
    """Read the manifest; entries whose file is absent are listed in `missing`, not raised."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    base = Path(root) if root is not None else Path(doc.get("root", "."))
    entries: list[CorpusEntry] = []
    missing: list[str] = []
    for row in doc.get("sequences", []):
        p = base / row["path"]
        if not p.exists():
            missing.append(row["path"])
            continue
        entries.append(CorpusEntry(path=p, song=str(row.get("song", "")).strip(),
                                   sequencer=str(row.get("sequencer", "")).strip(),
                                   weight=float(row.get("weight", 1.0)),
                                   exemplary_for=tuple(row.get("exemplary_for", [])),
                                   rel=str(row["path"])))
    return Manifest(root=base, entries=entries, missing=missing)


def read_sequence_bytes(path: Path) -> bytes:
    """The `.xsq` bytes: the file itself, or the first real `.xsq` member of a package."""
    if path.suffix.lower() not in {".xsqz", ".zip"}:
        return path.read_bytes()
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            parts = Path(info.filename).parts
            if (info.filename.lower().endswith(".xsq") and "__MACOSX" not in parts
                    and not parts[-1].startswith("._")):
                return zf.read(info)
    raise FileNotFoundError(f"no .xsq inside {path}")


def _head(raw: bytes) -> dict[str, str]:
    h = raw[:4000].decode("utf-8", "replace")

    def g(tag: str) -> str:
        m = re.search(rf"<{tag}>(.*?)</{tag}>", h)
        return m.group(1).strip() if m else ""
    return {"author": g("author"), "version": g("version"), "song": g("song")}


def iter_sequences(manifest: Manifest):
    """Yield `(entry, root, head)` per DISTINCT sequence (byte-identical files yield once)."""
    seen: set[str] = set()
    for entry in manifest.entries:
        raw = read_sequence_bytes(entry.path)
        digest = hashlib.md5(raw).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        yield entry, ET.fromstring(raw), _head(raw)


# -- mining -----------------------------------------------------------------------------------

@dataclass
class Placement:
    file: str
    song: str
    model: str
    cls: str
    layer: int
    start_ms: int
    end_ms: int
    beats: int | None
    section: str
    settings: dict[str, str]
    colors: list[str]
    sparkles: bool

    @property
    def dur_s(self) -> float:
        return (self.end_ms - self.start_ms) / 1000.0

    @property
    def key(self) -> tuple[str, str, int, int]:
        return (self.file, self.model, self.start_ms, self.layer)


@dataclass
class StackPair:
    file: str
    song: str
    me: tuple[str, str, int, int]        # Placement.key
    other_type: str
    other_layer: int
    other_blend: str                     # the partner's T_CHOICE_LayerMethod
    other_settings: dict[str, str]


@dataclass
class EffectFacts:
    effect_type: str
    mined_on: str
    n_sequences: int                     # distinct sequences in the corpus
    n_songs: int
    versions: list[str]
    placements: list[Placement]
    pairs: list[StackPair]
    per_file: Counter
    labels: dict[str, str]               # file name → "Song (sequencer)" for rendering
    files_with: int
    songs_with: int
    duplicates_dropped: int
    missing: list[str]


def _timing_tracks(root: ET.Element) -> tuple[list[int], list[tuple[int, int, str]]]:
    beats: list[int] = []
    secs: list[tuple[int, int, str]] = []
    ee = root.find("ElementEffects")
    if ee is None:
        return beats, secs
    for el in ee:
        if el.get("type") != "timing":
            continue
        n = (el.get("name") or "").lower()
        marks = [(int(e.get("startTime", 0)), int(e.get("endTime", 0)), e.get("label") or "")
                 for e in el.iter("Effect") if e.get("startTime")]
        if not marks:
            continue
        if (not beats and ("beat" in n or n == "1/4 notes")
                and not any(x in n for x in ("x2", "256", "off", "_2", "_3"))):
            beats = sorted(m[0] for m in marks)
        if not secs and any(x in n for x in ("structure", "break", "layout", "section")):
            secs = marks
    return beats, secs


def _active_colors(pal: dict[str, str]) -> list[str]:
    out = []
    for i in range(1, 9):
        if pal.get(f"C_CHECKBOX_Palette{i}") == "1":
            out.append(pal.get(f"C_BUTTON_Palette{i}", ""))
    return out


def mine_effect(effect_type: str, manifest: Manifest, *, mined_on: str = "") -> EffectFacts:
    placements: list[Placement] = []
    pairs: list[StackPair] = []
    per_file: Counter = Counter()
    labels: dict[str, str] = {}
    versions: set[str] = set()
    songs: set[str] = set()
    n_seq = 0
    for entry, root, head in iter_sequences(manifest):
        n_seq += 1
        songs.add(entry.song.lower() or head["song"].lower())
        versions.add(head["version"] or "?")
        edb = root.find("EffectDB")
        db = [(e.text or "").strip() for e in edb.findall("Effect")] if edb is not None else []
        pals = [(e.text or "").strip() for e in root.findall("ColorPalettes/ColorPalette")]
        beats, secs = _timing_tracks(root)
        ee = root.find("ElementEffects")
        if ee is None:
            continue
        song = entry.song or head["song"]
        labels[entry.name] = f"{song} ({entry.sequencer})" if entry.sequencer else song
        for el in ee:
            if el.get("type") != "model":
                continue
            model = el.get("name") or ""
            placed: list[dict[str, Any]] = []

            def walk(container: ET.Element, sub: str) -> None:
                for li, layer in enumerate(container.findall("EffectLayer")):
                    for e in layer.findall("Effect"):
                        if e.get("ref") is None:
                            continue
                        placed.append(dict(layer=li, sub=sub, name=e.get("name"), ref=int(e.get("ref", 0)),
                                           s=int(e.get("startTime", 0)), e=int(e.get("endTime", 0)),
                                           pal=e.get("palette")))
            walk(el, "")
            for sm in el.findall("SubModel"):
                walk(sm, sm.get("name") or "")
            for ef in placed:
                if ef["name"] != effect_type:
                    continue
                st = dict(parse_settings(db[ef["ref"]])) if ef["ref"] < len(db) else {}
                pal = (dict(parse_settings(pals[int(ef["pal"])]))
                       if ef["pal"] is not None and int(ef["pal"]) < len(pals) else {})
                dur = ef["e"] - ef["s"]
                nb = sum(1 for b in beats if ef["s"] <= b < ef["e"]) if beats else None
                sec = next((lab for (a, b, lab) in secs if a <= ef["s"] < b), "")
                p = Placement(file=entry.name, song=song, model=model, cls=prop_class(model),
                              layer=ef["layer"], start_ms=ef["s"], end_ms=ef["e"], beats=nb, section=sec,
                              settings=st, colors=_active_colors(pal),
                              sparkles=any(k == "C_SLIDER_SparkleFrequency" for k in pal))
                placements.append(p)
                per_file[entry.name] += 1
                for other in placed:
                    if other is ef or other["sub"] != ef["sub"]:
                        continue
                    ov = min(ef["e"], other["e"]) - max(ef["s"], other["s"])
                    if ov <= 0 or ov < 0.5 * dur:
                        continue
                    ost = dict(parse_settings(db[other["ref"]])) if other["ref"] < len(db) else {}
                    pairs.append(StackPair(file=entry.name, song=song, me=p.key,
                                           other_type=str(other["name"]), other_layer=other["layer"],
                                           other_blend=ost.get("T_CHOICE_LayerMethod", "Normal"),
                                           other_settings={k: v for k, v in ost.items()
                                                           if k.startswith(("E_", "B_", "T_"))}))
    n_entries = len(manifest.entries)
    return EffectFacts(
        effect_type=effect_type, mined_on=mined_on, n_sequences=n_seq, n_songs=len(songs),
        versions=sorted(versions), placements=placements, pairs=pairs, per_file=per_file, labels=labels,
        files_with=len({p.file for p in placements}), songs_with=len({p.song.lower() for p in placements}),
        duplicates_dropped=n_entries - n_seq, missing=list(manifest.missing))


# -- rendering --------------------------------------------------------------------------------

def _breadth(rows: list[Placement]) -> str:
    seq, songs = len({r.file for r in rows}), len({r.song.lower() for r in rows})
    return f"{seq} seq / {songs} song" + ("s" if songs != 1 else "")


def _share(n: int, total: int) -> str:
    return f"{100 * n / total:.0f}%" if total else "0%"


# Keys xLights saves for the effect panel's own widgets, not the effect: the open notebook tab
# (`E_NOTEBOOK_Fan`, `E_NOTEBOOK1`) and unnamed static text (`E_TEXTCTRL1`, Kaleidoscope's help
# line). They are not dials and never make a facts row.
_PANEL_CHROME = re.compile(r"^E_NOTEBOOK(_|\d*$)|^E_TEXTCTRL\d+$")


def _short_key(k: str, effect_type: str) -> str:
    for pre in ("E_SLIDER_", "E_TEXTCTRL_", "E_CHECKBOX_", "E_CHOICE_", "E_VALUECURVE_"):
        if k.startswith(pre):
            k = k[len(pre):]
            tag = pre[2:-1].lower()
            break
    else:
        return f"`{k}`"
    k = k.replace(effect_type.replace(" ", "") + "_", "").replace(effect_type + "_", "")
    return f"`{k}` ({tag})"


def _vc_type(v: str) -> str:
    m = re.search(r"Type=([^|]+)", v)
    return m.group(1) if m else "Flat"      # xLights omits Type for the default flat curve


def _is_active_vc(v: str) -> bool:
    return "Active=TRUE" in v


def _numeric(v: str) -> float | None:
    try:
        return float(v)
    except ValueError:
        return None


def render_facts(f: EffectFacts, *, top_n: int = 8) -> str:
    P = f.placements
    N = len(P)
    out: list[str] = []
    w = out.append
    w(FACTS_HEADING)
    w("")
    w(f"> Generated {f.mined_on or 'by xlo mine-effect'} from the deduped corpus: **{f.n_sequences} community "
      f"sequences, {f.n_songs} distinct songs** (xLights {f.versions[0] if f.versions else '?'}–"
      f"{f.versions[-1] if f.versions else '?'}; {f.duplicates_dropped} byte-identical files dropped"
      + (f"; {len(f.missing)} manifest entries missing on disk" if f.missing else "") + "). "
      f"{f.files_with} sequences / {f.songs_with} songs use {f.effect_type}: **{N:,} placements, "
      f"{len(f.pairs):,} overlapping pairs.** Every share carries its breadth (sequences / songs); a "
      f"habit in one sequence is one sequencer's habit, however many placements it has.")
    if N == 0:
        w(">")
        w(f"> No placements of {f.effect_type} in the corpus.")
        return "\n".join(out) + "\n"
    src = " · ".join(f"{f.labels.get(name, name)} {n}" for name, n in f.per_file.most_common(8))
    rest = N - sum(n for _, n in f.per_file.most_common(8))
    w(">")
    w(f"> Sources by placements: {src}" + (f" · the other {len(f.per_file) - 8} files {rest} together" if rest else "") + ".")
    w("")
    # where
    w("### Where it is placed")
    w("")
    w("| Prop class | Share | Breadth | Example model names |")
    w("|---|---|---|---|")
    for cls, n in Counter(p.cls for p in P).most_common(12):
        rows = [p for p in P if p.cls == cls]
        names = ", ".join(m for m, _ in Counter(p.model for p in rows).most_common(3))
        w(f"| {cls} | {_share(n, N)} | {_breadth(rows)} | {names} |")
    w("")
    # dials
    w("### Dials observed")
    w("")
    w("Share · breadth per value; `curved` = that key has an active value curve instead of a static value.")
    w("")
    w("| Key | Values |")
    w("|---|---|")
    e_keys = sorted({k for p in P for k in p.settings
                     if k.startswith("E_") and "VALUECURVE" not in k and not _PANEL_CHROME.match(k)})
    for key in e_keys + [k for k in _CONTEXT_KEYS if any(k in p.settings for p in P)]:
        vc_key = key.replace("E_SLIDER_", "E_VALUECURVE_").replace("E_TEXTCTRL_", "E_VALUECURVE_")
        curved = [p for p in P if _is_active_vc(p.settings.get(vc_key, ""))] if key.startswith("E_") else []
        static = [p for p in P if p not in curved] if curved else P
        c = Counter(p.settings.get(key, "<absent>") for p in static)
        cells = []
        if curved:
            cells.append(f"**curved {_share(len(curved), N)} · {_breadth(curved)}**")
        for v, n in c.most_common(top_n):
            rows = [p for p in static if p.settings.get(key, "<absent>") == v]
            cells.append(f"{v}: {_share(n, N)} · {_breadth(rows)}")
        nums = [x for p in static if (x := _numeric(p.settings.get(key, ""))) is not None]
        rng = f" — range {min(nums):g}…{max(nums):g}" if nums and len(set(nums)) > 1 else ""
        w(f"| {_short_key(key, f.effect_type)} | {' — '.join(cells)}{rng} |")
    w("")
    # value curves
    w("### Value curves")
    w("")
    vc_keys = sorted({k for p in P for k, v in p.settings.items() if "VALUECURVE" in k and _is_active_vc(v)})
    any_vc = [p for p in P if any("VALUECURVE" in k and _is_active_vc(v) for k, v in p.settings.items())]
    tt = [p for p in P if any("TT=" in v and _is_active_vc(v) for v in p.settings.values())]
    w("| Parameter | Share · breadth | Shapes |")
    w("|---|---|---|")
    w(f"| any curve | {_share(len(any_vc), N)} · {_breadth(any_vc)} | |")
    for key in vc_keys:
        rows = [p for p in P if _is_active_vc(p.settings.get(key, ""))]
        shapes = " · ".join(f"{t} {n}" for t, n in Counter(_vc_type(p.settings[key]) for p in rows).most_common(8))
        w(f"| `{key}` | {_share(len(rows), N)} · {_breadth(rows)} | {shapes} |")
    if tt:
        w(f"| timing-track curves (`TT=`) | {_share(len(tt), N)} · {_breadth(tt)} | "
          + ", ".join(sorted({m.group(1) for p in tt for v in p.settings.values()
                              if (m := re.search(r'TT=([^|]+)', v))})) + " |")
    w("")
    w("Most-used exact strings (copy verbatim; `Min`/`Max` are the parameter range, `P*` the real values):")
    w("")
    w("```")
    for key in vc_keys:
        c = Counter(p.settings[key] for p in P if _is_active_vc(p.settings.get(key, "")))
        for v, n in c.most_common(4):
            rows = [p for p in P if p.settings.get(key) == v]
            w(f"{key} ({n}, {_breadth(rows)}): {v}")
    w("```")
    w("")
    # palette
    w("### Palette habits")
    w("")
    nc = Counter(len(p.colors) for p in P)
    w("Colors per placement: " + " · ".join(f"{k}: {_share(n, N)}" for k, n in sorted(nc.items())) + ".")
    black = [p for p in P if "#000000" in p.colors]
    spark = [p for p in P if p.sparkles]
    w(f"Black as a color: {_share(len(black), N)} · {_breadth(black)}. Sparkles on: {_share(len(spark), N)} · {_breadth(spark)}.")
    pal = Counter(tuple(c for c in p.colors if not c.startswith("Active=")) for p in P)
    w("Top palettes: " + " · ".join(f"{'+'.join(k) if k else '(gradient)'} {n}" for k, n in pal.most_common(8)) + ".")
    w("")
    # duration
    w("### Duration")
    w("")
    durs = [p.dur_s for p in P]
    buckets = Counter(("<1 s" if x < 1 else "1–2 s" if x < 2 else "2–4 s" if x < 4 else "4–8 s" if x < 8
                       else "8–16 s" if x < 16 else "≥16 s") for x in durs)
    order = ["<1 s", "1–2 s", "2–4 s", "4–8 s", "8–16 s", "≥16 s"]
    w(f"Median {statistics.median(durs):.2f} s. " + " · ".join(f"{b} {_share(buckets[b], N)}" for b in order if buckets[b]) + ".")
    bts = [p.beats for p in P if p.beats is not None]
    if bts:
        w(f"In beats ({len(bts)} placements with a beat track): "
          + " · ".join(f"{k} beats {_share(n, len(bts))}" for k, n in Counter(bts).most_common(8)) + ".")
    w("")
    # stacking
    w("### Stacking")
    w("")
    by: dict[tuple[str, str, int, int], list[StackPair]] = defaultdict(list)
    for s in f.pairs:
        by[s.me].append(s)
    with1 = [p for p in P if len(by.get(p.key, [])) >= 1]
    with3 = [p for p in P if len({(s.other_layer, s.other_type) for s in by.get(p.key, [])}) >= 3]
    w(f"**{_share(len(with1), N)} of placements share the model with at least one concurrent effect "
      f"({_breadth(with1)}); {_share(len(with3), N)} with three or more ({_breadth(with3)}).**")
    w("")
    pt = Counter(s.other_type for s in f.pairs)
    w("Partner types (pairs · sequences): " + " · ".join(
        f"{t} {n} · {len({s.file for s in f.pairs if s.other_type == t})}" for t, n in pt.most_common(20)) + ".")
    w("")
    me_layer = {p.key: p.layer for p in P}
    me_blend = {p.key: p.settings.get("T_CHOICE_LayerMethod", "Normal") for p in P}
    top = Counter((s.other_type, s.other_blend) for s in f.pairs if s.other_layer < me_layer[s.me])
    bot = Counter((s.other_type, me_blend[s.me]) for s in f.pairs if s.other_layer > me_layer[s.me])
    w(f"Above {f.effect_type} (partner type, the partner's blend): "
      + " · ".join(f"{t} {n} {b}" for (t, b), n in top.most_common(20)) + ".")
    w("")
    w(f"Beneath {f.effect_type} (partner type, {f.effect_type}'s own blend over it): "
      + " · ".join(f"{t} {n} {b}" for (t, b), n in bot.most_common(20)) + ".")
    w("")
    comp: Counter = Counter()
    for p in P:
        partners = {(s.other_layer, s.other_type) for s in by.get(p.key, [])}
        stack = sorted(partners | {(p.layer, f"*{f.effect_type}")})
        comp[" > ".join(n for _, n in stack)] += 1
    w("Recurring full stacks (top → bottom, `*` = the mined effect): "
      + " · ".join(f"{k} ({n})" for k, n in comp.most_common(16)) + ".")
    w("")
    twins = [s for s in f.pairs if s.other_type == f.effect_type and s.other_layer < me_layer[s.me]]
    if twins:
        me_set = {p.key: p.settings for p in P}
        ident = sum(1 for s in twins if {k: v for k, v in me_set[s.me].items() if k.startswith("E_")}
                    == {k: v for k, v in s.other_settings.items() if k.startswith("E_")})
        tdiff = sum(1 for s in twins if me_set[s.me].get("B_CHOICE_BufferTransform", "-")
                    != s.other_settings.get("B_CHOICE_BufferTransform", "-"))
        signs = []
        for key in e_keys:
            opp = 0
            for s in twins:
                a, b = _numeric(me_set[s.me].get(key, "")), _numeric(s.other_settings.get(key, ""))
                if a is not None and b is not None and a * b < 0:
                    opp += 1
            if opp:
                signs.append(f"{_short_key(key, f.effect_type)} opposite sign {_share(opp, len(twins))}")
        w(f"Same-type twins ({len(twins)} top-over-bottom pairs): identical effect settings "
          f"{_share(ident, len(twins))}; buffer transform differs {_share(tdiff, len(twins))}"
          + ("; " + "; ".join(signs) if signs else "") + ".")
        w("")
    return "\n".join(out).rstrip("\n") + "\n"


# -- the skill file -----------------------------------------------------------------------------

def splice_facts(md: str, block: str, effect_type: str) -> str:
    """Replace the facts block of an effect file (or build a fresh file around it)."""
    block = block.rstrip("\n") + "\n"
    if FACTS_HEADING in md and CRAFT_HEADING in md:
        a = md.index(FACTS_HEADING)
        b = md.index(CRAFT_HEADING)
        sep = md.rfind("---", a, b)
        tail = md[sep:] if sep != -1 else "---\n\n" + md[b:]
        return md[:a] + block + "\n" + tail
    craft = "\n\n".join(f"### {s}\n\n_(to write)_" for s in CRAFT_SECTIONS)
    return f"# {effect_type}\n\n_(one line: what it is)_\n\n---\n\n{block}\n---\n\n{CRAFT_HEADING}\n\n{craft}\n"


def write_effect_file(path: Path, facts: EffectFacts) -> Path:
    block = render_facts(facts)
    md = path.read_text(encoding="utf-8") if path.exists() else ""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(splice_facts(md, block, facts.effect_type), encoding="utf-8")
    return path


def facts_to_json(facts: EffectFacts) -> dict[str, Any]:
    return {
        "effect_type": facts.effect_type, "n_sequences": facts.n_sequences, "n_songs": facts.n_songs,
        "placements": [p.__dict__ for p in facts.placements],
        "pairs": [{**s.__dict__, "me": list(s.me)} for s in facts.pairs],
    }
