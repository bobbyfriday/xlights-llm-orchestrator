"""Offline extractor: mine a parameterized preset catalog from community .xsq files.

Usage:
    python -m xlights_core.knowledge.xsq_extractor /path/to/show [--out <dir>]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

from .constants import ASSET_BOUND_TYPES, classify_kind
from .models import Catalog, Knob, Look, Palette
from .settings import (
    classify_value_curve,
    parse_settings,
    value_curve_is_active,
)

DEFAULT_OUT = Path(__file__).parent / "presets"


# -- corpus iteration ---------------------------------------------------------

def iter_corpus(show_dir: str | Path):
    """Yield community-authored .xsq paths: author not 'xlight*', skipping Backup/."""
    show = Path(show_dir)
    for path in sorted(show.glob("*.xsq")):  # top-level only -> never enters Backup/
        author, _ = _read_head(path)
        if author.lower().startswith("xlight"):
            continue
        yield path


def _read_head(path: Path) -> tuple[str, str]:
    """Return (author, version) from the <head> without full parse cost guarantees."""
    head = path.read_text(encoding="utf-8", errors="replace")[:4000]
    import re

    a = re.search(r"<author>(.*?)</author>", head)
    v = re.search(r"<version>(.*?)</version>", head)
    return (a.group(1).strip() if a else "", v.group(1).strip() if v else "?")


# -- per-file dereference -----------------------------------------------------

def _has_active_timing_track_curve(pairs: list[tuple[str, str]]) -> bool:
    for k, v in pairs:
        if classify_kind(k) == "valuecurve" and value_curve_is_active(v):
            if classify_value_curve(v) == "timing-track":
                return True
    return False


def extract_file(path: Path):
    """Yield (effect_type, settings_string, version) and collect palette strings.

    Returns (records, palette_strings, skipped_counts).
    """
    _, version = _read_head(path)
    root = ET.parse(path).getroot()

    edb = root.find("EffectDB")
    settings_db = [(e.text or "").strip() for e in edb.findall("Effect")] if edb is not None else []
    palettes = [(e.text or "").strip() for e in root.findall("ColorPalettes/ColorPalette")]

    records = []
    skipped = Counter()
    for eff in root.iter("Effect"):
        ref = eff.get("ref")
        name = eff.get("name")
        if ref is None or name is None:
            continue  # an EffectDB entry, not a placed effect
        if name in ASSET_BOUND_TYPES:
            skipped["asset_type"] += 1
            continue
        i = int(ref)
        if not (0 <= i < len(settings_db)):
            skipped["bad_ref"] += 1
            continue
        s = settings_db[i]
        if _has_active_timing_track_curve(parse_settings(s)):
            skipped["timing_track_vc"] += 1
            continue
        records.append((name, s, version))
    return records, palettes, skipped


# -- catalog construction -----------------------------------------------------

def _build_knob(key: str, values: list[str]) -> Knob:
    kind = classify_kind(key)
    default = Counter(values).most_common(1)[0][0]
    distinct = sorted(set(values))
    if kind == "slider":
        try:
            nums = [float(v) for v in values]
            return Knob(key=key, kind=kind, numeric=True,
                        min=min(nums), max=max(nums), default=default)
        except ValueError:
            pass  # non-numeric slider -> treat categorical
    if kind == "valuecurve":
        classes = {classify_value_curve(v) for v in values}
        vc_class = classes.pop() if len(classes) == 1 else "mixed"
        return Knob(key=key, kind=kind, options=distinct, vc_class=vc_class, default=default)
    return Knob(key=key, kind=kind, options=distinct, default=default)


def build_catalog(show_dir: str | Path) -> tuple[Catalog, dict]:
    by_type: dict[str, list[tuple[list[tuple[str, str]], str]]] = defaultdict(list)
    palette_strings: list[str] = []
    files = 0
    versions: set[str] = set()
    skipped_total: Counter = Counter()

    for path in iter_corpus(show_dir):
        files += 1
        records, palettes, skipped = extract_file(path)
        skipped_total.update(skipped)
        palette_strings.extend(palettes)
        for name, s, version in records:
            versions.add(version)
            by_type[name].append((parse_settings(s), version))

    looks_by_type: dict[str, list[Look]] = {}
    for etype, entries in by_type.items():
        groups: dict[tuple[str, ...], list[tuple[list[tuple[str, str]], str]]] = defaultdict(list)
        for pairs, version in entries:
            sig = tuple(sorted({k for k, _ in pairs}))
            groups[sig].append((pairs, version))

        looks: list[Look] = []
        for idx, (sig, members) in enumerate(sorted(groups.items())):
            # per-key observed values across the group
            values_by_key: dict[str, list[str]] = defaultdict(list)
            full_strings: Counter = Counter()
            vers: set[str] = set()
            rep_order: list[str] | None = None
            for pairs, version in members:
                vers.add(version)
                full_strings[tuple(pairs)] += 1
                for k, v in pairs:
                    values_by_key[k].append(v)
            rep = full_strings.most_common(1)[0][0]
            rep_order = [k for k, _ in rep]

            frozen, knob_keys = {}, []
            for k in rep_order:
                if len(set(values_by_key[k])) == 1:
                    frozen[k] = values_by_key[k][0]
                else:
                    knob_keys.append(k)
            knobs = [_build_knob(k, values_by_key[k]) for k in knob_keys]
            looks.append(Look(
                look_id=f"{etype}#{idx}",
                effect_type=etype,
                key_signature=list(sig),
                key_order=rep_order,
                frozen_base=frozen,
                knobs=knobs,
                source_versions=sorted(vers),
                count=len(members),
            ))
        looks_by_type[etype] = looks

    catalog = Catalog(
        schema_version=1,
        meta={
            "corpus": str(show_dir),
            "files": files,
            "xlights_versions": sorted(versions),
            "skipped": dict(skipped_total),
            "totals": {
                "effect_types": len(looks_by_type),
                "looks": sum(len(v) for v in looks_by_type.values()),
                "palettes_raw": len(palette_strings),
            },
        },
        looks_by_type=looks_by_type,
        palettes=build_palettes(palette_strings),
    )
    catalog.meta["totals"]["palettes"] = len(catalog.palettes)
    return catalog, dict(skipped_total)


# -- palettes -----------------------------------------------------------------

def _palette_colors(palette_string: str) -> list[str]:
    import re
    seen, out = set(), []
    for c in re.findall(r"#[0-9A-Fa-f]{6}", palette_string):
        cu = c.upper()
        if cu not in seen:
            seen.add(cu); out.append(cu)
    return out


def _palette_tags(colors: list[str]) -> list[str]:
    tags = [f"count:{len(colors)}"]
    if len(colors) == 1:
        tags.append("monochrome")
    warm = cool = 0
    for c in colors:
        r, _, b = int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
        if r >= b:
            warm += 1
        else:
            cool += 1
    if colors:
        tags.append("warm" if warm >= cool else "cool")
    return tags


def build_palettes(palette_strings: list[str]) -> list[Palette]:
    by_colorset: dict[tuple[str, ...], str] = {}
    for s in palette_strings:
        if not s:
            continue
        cols = _palette_colors(s)
        if not cols:
            continue
        key = tuple(sorted(cols))  # color-SET identity (order-independent)
        by_colorset.setdefault(key, s)  # keep first representative (its slot order)
    out = []
    for idx, (_key, rep) in enumerate(sorted(by_colorset.items())):
        repcols = _palette_colors(rep)
        out.append(Palette(palette_id=f"pal#{idx}", palette_string=rep,
                           colors=repcols, tags=_palette_tags(repcols)))
    return out


# -- write + CLI --------------------------------------------------------------

def write_catalog(catalog: Catalog, out_dir: str | Path = DEFAULT_OUT) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    looks_doc = {
        "schema_version": catalog.schema_version,
        "meta": catalog.meta,
        "looks_by_type": {t: [l.model_dump() for l in looks]
                          for t, looks in catalog.looks_by_type.items()},
    }
    (out / "looks.json").write_text(json.dumps(looks_doc, indent=1), encoding="utf-8")
    pal_doc = {"schema_version": catalog.schema_version,
               "palettes": [p.model_dump() for p in catalog.palettes]}
    (out / "palettes.json").write_text(json.dumps(pal_doc, indent=1), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Mine an xLights effect-preset catalog.")
    ap.add_argument("show_dir", help="xLights show folder (mines top-level community .xsq)")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="catalog output dir")
    args = ap.parse_args(argv)

    catalog, skipped = build_catalog(args.show_dir)
    write_catalog(catalog, args.out)
    t = catalog.meta["totals"]
    print(f"files mined:        {catalog.meta['files']}")
    print(f"xlights versions:   {', '.join(catalog.meta['xlights_versions'])}")
    print(f"effect types:       {t['effect_types']}")
    print(f"looks:              {t['looks']}")
    print(f"palettes:           {t['palettes']}  (from {t['palettes_raw']} raw)")
    print(f"skipped:            {skipped}")
    print(f"written to:         {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
