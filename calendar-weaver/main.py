"""Weekly recurring calendar collision analysis and availability search."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
import argparse
import json
from pathlib import Path

@dataclass(frozen=True)
class Event:
    name: str
    start_date: date
    end_date: date
    weekdays: frozenset[int]
    start_minute: int
    duration: int

    def __post_init__(self):
        if not self.name.strip(): raise ValueError("event name cannot be empty")
        if self.end_date < self.start_date: raise ValueError("end_date precedes start_date")
        if not self.weekdays or any(d < 0 or d > 6 for d in self.weekdays): raise ValueError("weekdays must be 0..6")
        if not 0 <= self.start_minute < 1440: raise ValueError("start_minute must be 0..1439")
        if self.duration <= 0 or self.start_minute + self.duration > 1440: raise ValueError("event must fit within one day")

@dataclass(frozen=True, order=True)
class Occurrence:
    day: date
    start: int
    end: int
    event: str

def expand(events, start, end):
    if end < start: raise ValueError("end precedes start")
    if (end-start).days > 3660: raise ValueError("horizon exceeds 10 years")
    result=[]
    for e in events:
        day=max(start,e.start_date); last=min(end,e.end_date)
        while day <= last:
            if day.weekday() in e.weekdays: result.append(Occurrence(day,e.start_minute,e.start_minute+e.duration,e.name))
            day += timedelta(days=1)
    return sorted(result)

def conflicts(events, start, end):
    by_day={}
    for occ in expand(events,start,end): by_day.setdefault(occ.day,[]).append(occ)
    found=[]
    for rows in by_day.values():
        rows.sort(key=lambda o:(o.start,o.end,o.event))
        for i,a in enumerate(rows):
            for b in rows[i+1:]:
                if b.start >= a.end: break
                if a.event != b.event and max(a.start,b.start)<min(a.end,b.end): found.append((a,b))
    return found

def free_slots(events, day, *, opening=540, closing=1020, minimum=30):
    if not 0 <= opening < closing <= 1440: raise ValueError("invalid working window")
    if minimum <= 0: raise ValueError("minimum must be positive")
    occupied=sorted((o.start,o.end) for o in expand(events,day,day))
    cursor=opening; out=[]
    for a,b in occupied:
        a=max(a,opening); b=min(b,closing)
        if b <= cursor: continue
        if a-cursor >= minimum: out.append((cursor,a))
        cursor=max(cursor,b)
    if closing-cursor >= minimum: out.append((cursor,closing))
    return out

def clock(minute): return f"{minute//60:02d}:{minute%60:02d}"

def parse_clock(value):
    """Parse strict 24-hour HH:MM wall-clock text into minutes after midnight."""
    if not isinstance(value, str) or len(value) != 5 or value[2] != ":" or not (value[:2] + value[3:]).isdigit():
        raise ValueError(f"invalid time {value!r}; expected HH:MM")
    try:
        hour, minute = int(value[:2]), int(value[3:])
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(f"invalid time {value!r}; expected HH:MM") from exc
    if not 0 <= hour < 24 or not 0 <= minute < 60:
        raise ValueError(f"invalid time {value!r}; expected HH:MM")
    return hour * 60 + minute

def load_events(path):
    """Load a JSON array of recurrence rules, validating every event."""
    try:
        rows = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(rows, list):
            raise ValueError("event document must be a JSON array")
        result = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("each event must be a JSON object")
            result.append(Event(
                row["name"], date.fromisoformat(row["start_date"]),
                date.fromisoformat(row["end_date"]), frozenset(row["weekdays"]),
                parse_clock(row["start"]), row["duration"],
            ))
        return result
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError(f"cannot load events from {path}: {exc}") from exc

def main(argv=None):
    parser = argparse.ArgumentParser(description="Find recurring calendar collisions and free windows")
    parser.add_argument("--input", type=Path, help="JSON event file (see README)")
    parser.add_argument("--from", dest="start", type=date.fromisoformat, help="inclusive start date")
    parser.add_argument("--to", dest="end", type=date.fromisoformat, help="inclusive end date")
    parser.add_argument("--day", type=date.fromisoformat, help="show free windows for one date")
    args = parser.parse_args(argv)
    try:
        if not args.input:
            demo()
            return 0
        if not args.start or not args.end:
            parser.error("--input requires --from and --to")
        events = load_events(args.input)
        found = conflicts(events, args.start, args.end)
        for a, b in found:
            print(f"{a.day}: {a.event} {clock(a.start)}-{clock(a.end)} overlaps {b.event} {clock(b.start)}-{clock(b.end)}")
        if args.day:
            slots = free_slots(events, args.day)
            print(f"Free slots {args.day}: " + ", ".join(f"{clock(a)}-{clock(b)}" for a, b in slots))
        return 0
    except ValueError as exc:
        parser.error(str(exc))

def demo():
    monday=date(2026,11,2)
    events=[Event("Focus",monday,monday+timedelta(days=28),frozenset({0,2,4}),540,90),Event("Review",monday,monday+timedelta(days=28),frozenset({0}),600,45)]
    print("Conflicts:")
    for a,b in conflicts(events,monday,monday+timedelta(days=6)):
        print(f"  {a.day}: {a.event} {clock(a.start)}-{clock(a.end)} overlaps {b.event} {clock(b.start)}-{clock(b.end)}")
    print("Free slots Monday:", ", ".join(f"{clock(a)}-{clock(b)}" for a,b in free_slots(events,monday)))

if __name__ == '__main__':
    raise SystemExit(main())
