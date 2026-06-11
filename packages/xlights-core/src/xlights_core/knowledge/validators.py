"""Per-knob validity enforcement for assembled settings."""

from __future__ import annotations

from .models import Knob


class KnobValueError(ValueError):
    """A chosen knob value violates its corpus-derived constraint."""


def validate_knob_value(knob: Knob, value: str) -> None:
    """Raise KnobValueError unless ``value`` is permitted for ``knob``.

    - numeric slider: within observed [min, max]
    - everything else (choice/checkbox/text/notebook/button/valuecurve/other):
      must be one of the observed values (value-curves are never synthesized)
    """
    if knob.numeric and knob.min is not None and knob.max is not None:
        try:
            x = float(value)
        except ValueError as exc:
            raise KnobValueError(f"{knob.key}: {value!r} is not numeric") from exc
        if not (knob.min <= x <= knob.max):
            raise KnobValueError(
                f"{knob.key}: {x} outside observed range [{knob.min}, {knob.max}]"
            )
        return
    options = knob.options or []
    if value not in options:
        raise KnobValueError(
            f"{knob.key}: {value!r} not an observed value (no synthesis; "
            f"{len(options)} options known)"
        )
