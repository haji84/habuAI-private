from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

JST = timezone(timedelta(hours=9))

class FutureLeakageError(ValueError):
    pass

def parse_time(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=JST)
    return dt

def operational_night(value: datetime) -> str:
    return (value.astimezone(JST) - timedelta(hours=7)).date().isoformat()

def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))

def _time_of(row: dict) -> datetime | None:
    for key in ("datetime_jst", "time_jst", "timestamp_jst", "time_utc", "created_at", "available_at"):
        value = row.get(key)
        if value:
            try:
                return parse_time(str(value))
            except ValueError:
                pass
    return None

def filter_as_of(rows: Iterable[dict], cutoff: datetime) -> list[dict]:
    out = []
    for row in rows:
        t = _time_of(row)
        if t is None or t <= cutoff:
            out.append(row)
    return out

class HabuDataAccess:
    """Read-only canonical access shared by Chat/Work and future GORIQ."""

    def __init__(self, root: Path):
        self.root = Path(root)

    def canonical_index(self) -> dict:
        path = self.root / "data" / "processed" / "canonical_index.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"schema_version": 1, "datasets": {}}

    def night(self, night_date: str, cutoff: str | datetime | None = None) -> dict:
        cutoff_dt = parse_time(cutoff) if isinstance(cutoff, str) else cutoff
        events = _read_csv(self.root / "data" / "processed" / "events_normalized.csv")
        captures = _read_csv(self.root / "data" / "processed" / "captures_normalized.csv")
        events = [r for r in events if r.get("night_date") == night_date]
        captures = [r for r in captures if r.get("night_date") == night_date]
        if cutoff_dt:
            events = filter_as_of(events, cutoff_dt)
            captures = filter_as_of(captures, cutoff_dt)
        return {"night_date": night_date, "cutoff": cutoff_dt.isoformat() if cutoff_dt else None, "events": events, "captures": captures}

    def as_of(self, cutoff: str | datetime) -> dict:
        cutoff_dt = parse_time(cutoff) if isinstance(cutoff, str) else cutoff
        return {"cutoff": cutoff_dt.isoformat(), "night_date": operational_night(cutoff_dt), **self.night(operational_night(cutoff_dt), cutoff_dt)}
