"""Per-section preview stills from the compiled `.fseq` + layout geometry — offline, no xLights,
no model (``xlo stills``, design D8/D9).

One PNG per brief section into ``out_dir``, named ``NN-<label-slug>.png`` (``NN`` = section index),
at the section's lit-coverage peak when a ``FseqSeries`` is given, else at its midpoint. Reuses
``xlights_core.preview.PreviewRenderer`` (the offline preview renderer) — needs the
``[preview]`` extra. A missing ``.fseq`` returns ``[]`` so the caller can print how to produce one
(``xlo apply --render``). Stale ``NN-*.png`` files in ``out_dir`` are removed first, so the folder
always holds exactly the current brief's sections.
"""

from __future__ import annotations

import re
from pathlib import Path

CANVAS = (1280, 720)
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_STILL_NAME = re.compile(r"^\d{2}-.*\.png$")


def section_slug(sec) -> str:
    """``"Chorus 2 (big!)"`` → ``chorus-2-big``; ``"section"`` when the section has no label."""
    label = str(getattr(sec, "label", "") or "")
    return _NON_ALNUM.sub("-", label.lower()).strip("-")[:48].rstrip("-") or "section"


def still_name(index: int, sec) -> str:
    return f"{index:02d}-{section_slug(sec)}.png"


def _peak_ms(series, sec) -> int | None:
    """Timestamp of the section's lit-coverage peak over its target groups (all series groups when
    none of its targets are in the series); None when the series has nothing for it."""
    import numpy as np
    sl = series.section_slice(sec.start_ms, sec.end_ms)
    keep = [g for g in (getattr(sec, "target_groups", None) or []) if g in sl]
    curves = [sl[g]["lit"] for g in (keep or list(sl)) if sl[g]["lit"].size]
    if not curves:
        return None
    curve = np.mean(np.stack(curves), axis=0)
    first = max(0, int(sec.start_ms) // series.step_ms)
    return int((first + int(np.argmax(curve))) * series.step_ms)


def still_time(sec, series=None) -> int:
    """The moment to picture a section: its coverage peak (series given) else its midpoint."""
    if series is not None:
        t = _peak_ms(series, sec)
        if t is not None:
            return t
    return int((int(sec.start_ms) + int(sec.end_ms)) // 2)


def still_times(sections, series=None) -> list[int]:
    """One timestamp per section (what ``render_stills`` pictures) — for the command's summary."""
    return [still_time(sec, series) for sec in sections]


def render_stills(fseq_path, show_folder, sections, out_dir, *, series=None,
                  canvas: tuple[int, int] = CANVAS) -> list[Path]:
    """Write one PNG per section and return their paths in section order.

    ``fseq_path`` is the compiled render; ``show_folder`` holds ``xlights_rgbeffects.xml`` and
    ``xlights_networks.xml``. Returns ``[]`` (writing nothing) when the ``.fseq`` is missing."""
    fseq_path = Path(fseq_path)
    if not fseq_path.exists():
        return []
    from xlights_core.preview import PreviewRenderer     # [preview] extra: numpy/zstandard/pillow
    show_folder = Path(show_folder)
    renderer = PreviewRenderer(fseq_path, show_folder / "xlights_rgbeffects.xml",
                               show_folder / "xlights_networks.xml")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for stale in out_dir.iterdir():
        if stale.is_file() and _STILL_NAME.match(stale.name):
            stale.unlink()
    paths: list[Path] = []
    for i, sec in enumerate(sections):
        png = renderer.render_frame(still_time(sec, series), canvas=canvas)
        path = out_dir / still_name(i, sec)
        path.write_bytes(png)
        paths.append(path)
    return paths
