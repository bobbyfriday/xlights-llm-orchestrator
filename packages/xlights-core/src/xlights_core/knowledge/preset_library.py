"""Lookup + assemble API over the committed preset catalog (the generator's menu)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .models import Knob, Look, Palette
from .validators import validate_knob_value

_PRESETS_DIR = Path(__file__).parent / "presets"


class PresetLibrary:
    """Loads the committed catalog and serves looks, palettes, and assembly."""

    def __init__(self, presets_dir: str | Path = _PRESETS_DIR) -> None:
        self._dir = Path(presets_dir)
        looks_doc = json.loads((self._dir / "looks.json").read_text(encoding="utf-8"))
        pal_doc = json.loads((self._dir / "palettes.json").read_text(encoding="utf-8"))
        self.meta: dict = looks_doc.get("meta", {})
        self._looks: dict[str, list[Look]] = {
            t: [Look.model_validate(l) for l in looks]
            for t, looks in looks_doc["looks_by_type"].items()
        }
        self._palettes: list[Palette] = [Palette.model_validate(p) for p in pal_doc["palettes"]]

    # -- lookup ---------------------------------------------------------------

    def list_effect_types(self) -> list[str]:
        return sorted(self._looks)

    def get_looks(self, effect_type: str, *, limit: int | None = None) -> list[Look]:
        looks = self._looks.get(effect_type, [])
        return looks[:limit] if limit else list(looks)

    def get_look(self, effect_type: str, look_id: str) -> Look:
        for lk in self._looks.get(effect_type, []):
            if lk.look_id == look_id:
                return lk
        raise KeyError(f"no look {look_id!r} for effect type {effect_type!r}")

    def get_palettes(self, *, tag: str | None = None, limit: int | None = None) -> list[Palette]:
        pals = self._palettes if tag is None else [p for p in self._palettes if tag in p.tags]
        return pals[:limit] if limit else list(pals)

    def get_palette(self, palette_id: str) -> Palette:
        for p in self._palettes:
            if p.palette_id == palette_id:
                return p
        raise KeyError(f"no palette {palette_id!r}")

    # -- assembly -------------------------------------------------------------

    def assemble(self, look: Look, knob_values: dict[str, str] | None = None) -> str:
        """Build a settings string from a look + chosen knob values (else defaults).

        Each supplied value is validated against its knob's corpus-derived constraint.
        """
        chosen = dict(knob_values or {})
        knobs_by_key: dict[str, Knob] = {k.key: k for k in look.knobs}

        unknown = set(chosen) - set(knobs_by_key)
        if unknown:
            raise KeyError(f"not knobs of {look.look_id}: {sorted(unknown)}")
        for key, value in chosen.items():
            validate_knob_value(knobs_by_key[key], value)

        pairs: list[tuple[str, str]] = []
        for key in look.key_order:
            if key in look.frozen_base:
                pairs.append((key, look.frozen_base[key]))
            elif key in knobs_by_key:
                pairs.append((key, chosen.get(key, knobs_by_key[key].default)))
        return ",".join(f"{k}={v}" for k, v in pairs)


@lru_cache(maxsize=1)
def get_library() -> PresetLibrary:
    """Process-wide cached library loaded from the committed catalog."""
    return PresetLibrary()
