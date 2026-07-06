"""The layout manifest (spec §6) — emitted AND consumed (F-E generalization).

``layout_semantics.json`` is the ONLY layout representation downstream LLM planners receive:
per-prop role/capability/position/sweep/mirror/focal/confidence + group membership with ordering.
Written to the show dir (canonical) plus a cache copy so hermetic runs read it without the show
folder mounted; ``load_manifest`` is version-tolerant (returns ``None`` on absence or mismatch).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from .layout_classify import ClassifyResult, SpatialSummary

log = logging.getLogger(__name__)

MANIFEST_VERSION = 1
MANIFEST_NAME = "layout_semantics.json"


class PropPos(BaseModel):
    x: float = 0.0
    y: float = 0.0
    band: str = "MID"
    side: str = "CENTER"


class PropRecord(BaseModel):
    id: str                                    # the model name
    role: str = "CUSTOM_PROP"
    res: str = "POINT"                         # capability class
    nodes: int = 0
    pos: PropPos = Field(default_factory=PropPos)
    sweep_order: int | None = None
    mirror_of: str | None = None
    focal: bool = False
    confidence: float = 1.0
    submodels: list[str] = Field(default_factory=list)


class GroupRecord(BaseModel):
    members: list[str] = Field(default_factory=list)
    ordered: bool = False                      # _LTR groups traverse members in order
    layout_mode: str = ""                      # the §5.7 layout-mode token


class DisplayBlock(BaseModel):
    width_units: float = 0.0
    focal_x: float = 0.5
    symmetric: bool = False


class LayoutManifest(BaseModel):
    version: int = MANIFEST_VERSION
    generated: str = ""                        # ISO timestamp + optional xLights version, forensics
    display: DisplayBlock = Field(default_factory=DisplayBlock)
    props: list[PropRecord] = Field(default_factory=list)
    groups: dict[str, GroupRecord] = Field(default_factory=dict)
    review: list[str] = Field(default_factory=list)   # prop names awaiting resolution (spec §7.4)

    # -- convenience lookups the consumers use -------------------------------------------------
    def prop_by_id(self) -> dict[str, PropRecord]:
        return {p.id: p for p in self.props}


def build_manifest(result: ClassifyResult, summary: SpatialSummary,
                   groups: dict[str, list[str]], *,
                   modes: dict[str, str] | None = None,
                   generated: str | None = None) -> LayoutManifest:
    """Assemble a manifest from a classify result + spatial summary + the SEM_ group plan.

    ``review`` collects every prop below 0.8 confidence and every excluded outlier (spec §7.4)."""
    modes = modes or {}
    prop_recs = [
        PropRecord(id=p.name, role=p.role, res=p.res, nodes=p.nodes,
                   pos=PropPos(x=round(p.x, 4), y=round(p.y, 4), band=p.band, side=p.side),
                   sweep_order=p.sweep_order, mirror_of=p.mirror_of, focal=p.focal,
                   confidence=p.confidence, submodels=p.submodels)
        for p in result.props
    ]
    group_recs = {
        name: GroupRecord(members=list(members), ordered=name.endswith("_LTR"),
                          layout_mode=modes.get(name, ""))
        for name, members in groups.items()
    }
    review_names = sorted({p.name for p in result.props if p.confidence < 0.8}
                          | {p.name for p in summary.excluded})
    return LayoutManifest(
        version=MANIFEST_VERSION,
        generated=datetime.now(timezone.utc).isoformat() if generated is None else generated,
        display=DisplayBlock(width_units=round(summary.width_units, 3),
                             focal_x=round(summary.focal_x, 4), symmetric=summary.symmetric),
        props=prop_recs, groups=group_recs, review=review_names,
    )


def _cache_manifest_path(cache_root: Path) -> Path:
    return Path(cache_root) / "layout" / MANIFEST_NAME


def emit_manifest(m: LayoutManifest, show_dir, *, cache_root=None) -> Path:
    """Write ``layout_semantics.json`` to the show dir (canonical) + a cache copy.

    Returns the show-dir path. The JSON is compact (``exclude_defaults`` drops every default field
    — spec §6's ~10 KB target is met on a small/typical layout; a large layout with verbose model
    names scales linearly, so the per-prop density is what stays bounded)."""
    data = m.model_dump(exclude_defaults=True)
    data["version"] = m.version                        # always present for the version-tolerant load
    payload = json.dumps(data)
    show_path = Path(show_dir) / MANIFEST_NAME
    show_path.parent.mkdir(parents=True, exist_ok=True)
    show_path.write_text(payload)
    if cache_root is not None:
        cache_path = _cache_manifest_path(cache_root)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(payload)
    return show_path


def load_manifest(show_dir_or_path, *, cache_root=None) -> LayoutManifest | None:
    """Tolerant load: ``None`` when absent OR the version doesn't match (forward-compat guard).

    Accepts the show dir, a direct file path, or falls back to the cache copy."""
    candidates: list[Path] = []
    if show_dir_or_path is not None:
        p = Path(show_dir_or_path)
        candidates.append(p if p.suffix == ".json" else p / MANIFEST_NAME)
    if cache_root is not None:
        candidates.append(_cache_manifest_path(cache_root))
    for path in candidates:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text())
        except (ValueError, OSError):
            return None
        if data.get("version") != MANIFEST_VERSION:      # version mismatch → tolerant None
            return None
        try:
            return LayoutManifest.model_validate(data)
        except Exception as exc:  # noqa: BLE001 — a malformed manifest loads as nothing, not a crash
            log.debug("malformed layout manifest at %s ignored: %s", path, exc)
            return None
    return None


# ------------------------------------------------------------------------------------------------
# plan_diff — the dry-run three-way per-group membership diff (spec §6 / migration plan)
# ------------------------------------------------------------------------------------------------
class GroupDiff(BaseModel):
    only_in_file: list[str] = Field(default_factory=list)
    only_in_plan: list[str] = Field(default_factory=list)
    order_changed: bool = False


def read_sem_groups(rgb_path) -> dict[str, list[str]]:
    """The SEM_ groups currently in an rgbeffects.xml (name -> member list), for the dry-run diff."""
    import xml.etree.ElementTree as ET
    root = ET.parse(rgb_path).getroot()
    mg = root.find("modelGroups")
    out: dict[str, list[str]] = {}
    for g in (mg.findall("modelGroup") if mg is not None else []):
        name = g.get("name", "")
        if name.startswith("SEM_"):
            out[name] = [m for m in (g.get("models", "") or "").split(",") if m]
    return out


def plan_diff(file_groups: dict[str, list[str]],
              plan_groups: dict[str, list[str]]) -> dict[str, GroupDiff]:
    """Three-way per-group diff (only-in-file / only-in-plan / member-order-changed).

    Only groups that actually differ appear in the result — a converged layout diffs empty."""
    out: dict[str, GroupDiff] = {}
    for name in sorted(set(file_groups) | set(plan_groups)):
        fmembers = list(file_groups.get(name, []))
        pmembers = list(plan_groups.get(name, []))
        fset, pset = set(fmembers), set(pmembers)
        only_file = sorted(fset - pset)
        only_plan = sorted(pset - fset)
        # order changed only when the shared membership is identical as a set but not in sequence
        order_changed = (fset == pset and fmembers != pmembers)
        if only_file or only_plan or order_changed:
            out[name] = GroupDiff(only_in_file=only_file, only_in_plan=only_plan,
                                  order_changed=order_changed)
    return out
