"""The project-wide Veo clip ledger: one appended line per generated clip, counted per day.

Veo's daily quota is per Gemini project, not per song, so the ledger lives at the cache ROOT
(`veo_ledger.jsonl`), not in a song's directory. The media planner reads it to say how many clips
are renderable today; the Veo renderer (a later change) is the only writer. Append-only JSONL, read
tolerantly: a bad line is skipped and logged, never fatal.

The day boundary is the configured quota-reset timezone (`video.veo.quota_reset_tz`); `day` is
stored on each entry so re-reading never depends on the current zone setting.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ValidationError

log = logging.getLogger(__name__)

LEDGER_NAME = "veo_ledger.jsonl"


class LedgerEntry(BaseModel):
    ts: str                       # ISO-8601 UTC timestamp of the generation
    day: str                      # YYYY-MM-DD in the quota-reset timezone at generation time
    clip_id: str
    song_key: str
    asset: str                    # the media plan's asset id this clip renders
    seconds: float
    model: str = ""


def ledger_path(root: Path | None = None) -> Path:
    if root is None:
        from .pipeline.cache import cache_root
        root = cache_root()
    return root / LEDGER_NAME


def day_for(ts: datetime, tz: str) -> str:
    """The quota day a UTC/aware timestamp falls in, in zone `tz`."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(ZoneInfo(tz)).date().isoformat()


def read(path: Path | None = None) -> list[LedgerEntry]:
    p = ledger_path() if path is None else path
    if not p.exists():
        return []
    out: list[LedgerEntry] = []
    for n, line in enumerate(p.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            out.append(LedgerEntry.model_validate(json.loads(line)))
        except (json.JSONDecodeError, ValidationError) as exc:
            log.warning("veo ledger %s line %d skipped: %s", p, n, exc)
    return out


def append(entry: LedgerEntry, path: Path | None = None) -> None:
    p = ledger_path() if path is None else path
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(entry.model_dump_json() + "\n")


def new_entry(*, clip_id: str, song_key: str, asset: str, seconds: float, model: str = "",
              tz: str, now: datetime | None = None) -> LedgerEntry:
    now = now or datetime.now(timezone.utc)
    return LedgerEntry(ts=now.isoformat(), day=day_for(now, tz), clip_id=clip_id, song_key=song_key,
                       asset=asset, seconds=seconds, model=model)


def used_today(tz: str, *, path: Path | None = None, now: datetime | None = None) -> int:
    today = day_for(now or datetime.now(timezone.utc), tz)
    return sum(1 for e in read(path) if e.day == today)


def remaining_today(limit: int, tz: str, *, path: Path | None = None,
                    now: datetime | None = None) -> int:
    """Clips still generable today across ALL songs: the daily limit minus today's entries. Never
    negative. A missing ledger means the full limit and creates nothing."""
    return max(0, int(limit) - used_today(tz, path=path, now=now))
