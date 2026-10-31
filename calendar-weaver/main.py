"""Weekly recurring calendar collision analysis and availability search."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta

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

def demo():
    monday=date(2026,11,2)
    events=[Event("Focus",monday,monday+timedelta(days=28),frozenset({0,2,4}),540,90),Event("Review",monday,monday+timedelta(days=28),frozenset({0}),600,45)]
    print("Conflicts:")
    for a,b in conflicts(events,monday,monday+timedelta(days=6)):
        print(f"  {a.day}: {a.event} {clock(a.start)}-{clock(a.end)} overlaps {b.event} {clock(b.start)}-{clock(b.end)}")
    print("Free slots Monday:", ", ".join(f"{clock(a)}-{clock(b)}" for a,b in free_slots(events,monday)))

if __name__ == '__main__': demo()
