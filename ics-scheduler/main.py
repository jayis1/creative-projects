"""Small, bounded iCalendar recurrence and conflict toolkit."""
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

UTC = timezone.utc
STAMP = "%Y%m%dT%H%M%SZ"
MAX_EVENTS = 10_000
MAX_OCCURRENCES = 100_000


def _validate_stamp(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None or value.utcoffset() != timedelta(0):
        raise ValueError("timestamps must be timezone-aware UTC")


def _stamp(value: datetime) -> str:
    _validate_stamp(value)
    return value.strftime(STAMP)


def _parse_stamp(value: str) -> datetime:
    if not re.fullmatch(r"\d{8}T\d{6}Z", value):
        raise ValueError("expected UTC timestamp YYYYMMDDTHHMMSSZ")
    try:
        return datetime.strptime(value, STAMP).replace(tzinfo=UTC)
    except ValueError as exc:
        raise ValueError(f"invalid UTC timestamp: {value}") from exc


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _unescape(value: str) -> str:
    result, i = [], 0
    while i < len(value):
        if value[i] == "\\":
            i += 1
            if i >= len(value):
                raise ValueError("trailing escape in SUMMARY")
            result.append("\n" if value[i] in "nN" else value[i])
        else:
            result.append(value[i])
        i += 1
    return "".join(result)


@dataclass(frozen=True)
class Recurrence:
    frequency: str
    interval: int = 1
    count: int | None = None
    until: datetime | None = None

    def __post_init__(self) -> None:
        if self.frequency not in {"DAILY", "WEEKLY", "MONTHLY"}:
            raise ValueError("frequency must be DAILY, WEEKLY, or MONTHLY")
        if not isinstance(self.interval, int) or isinstance(self.interval, bool) or self.interval < 1:
            raise ValueError("interval must be a positive integer")
        if self.count is not None and (not isinstance(self.count, int) or isinstance(self.count, bool) or self.count < 1):
            raise ValueError("count must be a positive integer")
        if self.count is not None and self.until is not None:
            raise ValueError("COUNT and UNTIL cannot both be set")
        if self.until is not None:
            _validate_stamp(self.until)


@dataclass(frozen=True)
class Event:
    start: datetime
    duration: timedelta
    summary: str
    recurrence: Recurrence | None = None

    def __post_init__(self) -> None:
        _validate_stamp(self.start)
        if self.duration <= timedelta(0) or self.duration.total_seconds() % 1:
            raise ValueError("duration must be a positive whole number of seconds")
        if not isinstance(self.summary, str) or not self.summary or any(ord(c) < 32 and c != "\n" for c in self.summary):
            raise ValueError("summary must be non-empty text without control characters")


def _month_add(start: datetime, months: int) -> datetime:
    index = start.year * 12 + start.month - 1 + months
    year, month0 = divmod(index, 12)
    if not 1 <= year <= 9999:
        raise ValueError("recurrence exceeds supported calendar range")
    month = month0 + 1
    # Clamp each monthly occurrence to the target month's final day.
    import calendar
    day = min(start.day, calendar.monthrange(year, month)[1])
    return start.replace(year=year, month=month, day=day)


def expand(event: Event, limit: int = MAX_OCCURRENCES) -> list[Event]:
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError("limit must be a positive integer")
    rule = event.recurrence
    if rule is None:
        return [event]
    if rule.count is not None and rule.count > limit:
        raise ValueError("recurrence exceeds occurrence limit")
    out, current = [], event.start
    while rule.count is None or len(out) < rule.count:
        if rule.until is not None and current > rule.until:
            break
        if len(out) >= limit:
            raise ValueError("recurrence exceeds occurrence limit")
        out.append(Event(current, event.duration, event.summary))
        try:
            if rule.frequency == "DAILY": current += timedelta(days=rule.interval)
            elif rule.frequency == "WEEKLY": current += timedelta(weeks=rule.interval)
            else: current = _month_add(event.start, rule.interval * (len(out)))
        except OverflowError as exc:
            raise ValueError("recurrence exceeds supported calendar range") from exc
    return out


def to_ics(events: list[Event]) -> str:
    if len(events) > MAX_EVENTS:
        raise ValueError(f"calendar exceeds {MAX_EVENTS} events")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//jayis1//ICS Scheduler//EN"]
    for event in events:
        lines.extend(("BEGIN:VEVENT", f"DTSTART:{_stamp(event.start)}", f"DURATION:PT{int(event.duration.total_seconds())}S", f"SUMMARY:{_escape(event.summary)}"))
        if event.recurrence:
            rule = event.recurrence
            fields = [f"FREQ={rule.frequency}"]
            if rule.interval != 1: fields.append(f"INTERVAL={rule.interval}")
            if rule.count is not None: fields.append(f"COUNT={rule.count}")
            if rule.until is not None: fields.append(f"UNTIL={_stamp(rule.until)}")
            lines.append("RRULE:" + ";".join(fields))
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def from_ics(text: str) -> list[Event]:
    if not isinstance(text, str) or len(text) > 1_000_000:
        raise ValueError("calendar must be text no larger than 1 MB")
    unfolded = re.sub(r"\r?\n[ \t]", "", text)
    events, fields, active = [], {}, False
    for line in unfolded.splitlines():
        if line == "BEGIN:VEVENT":
            if active: raise ValueError("nested VEVENT")
            active, fields = True, {}
        elif line == "END:VEVENT":
            if not active: raise ValueError("unexpected END:VEVENT")
            required = {"DTSTART", "DURATION", "SUMMARY"}
            if not required <= fields.keys(): raise ValueError("VEVENT missing required field")
            match = re.fullmatch(r"PT([1-9][0-9]*)S", fields["DURATION"])
            if not match: raise ValueError("unsupported DURATION")
            recurrence = None
            if "RRULE" in fields:
                parts = {}
                for item in fields["RRULE"].split(";"):
                    pair = item.split("=", 1)
                    if len(pair) != 2 or pair[0] in parts: raise ValueError("malformed RRULE")
                    parts[pair[0]] = pair[1]
                if set(parts) - {"FREQ", "INTERVAL", "COUNT", "UNTIL"}: raise ValueError("unsupported RRULE field")
                try:
                    recurrence = Recurrence(parts["FREQ"], int(parts.get("INTERVAL", "1")), int(parts["COUNT"]) if "COUNT" in parts else None, _parse_stamp(parts["UNTIL"]) if "UNTIL" in parts else None)
                except (KeyError, ValueError) as exc:
                    raise ValueError(f"invalid RRULE: {exc}") from exc
            events.append(Event(_parse_stamp(fields["DTSTART"]), timedelta(seconds=int(match.group(1))), _unescape(fields["SUMMARY"]), recurrence))
            if len(events) > MAX_EVENTS: raise ValueError(f"calendar exceeds {MAX_EVENTS} events")
            active = False
        elif active:
            if ":" not in line: raise ValueError("malformed content line")
            key, value = line.split(":", 1)
            if key in fields: raise ValueError(f"duplicate field: {key}")
            if key in {"DTSTART", "DURATION", "SUMMARY", "RRULE"}: fields[key] = value
    if active: raise ValueError("unterminated VEVENT")
    return events


def find_conflicts(events: list[Event]) -> list[tuple[Event, Event]]:
    ordered = sorted(events, key=lambda item: item.start)
    active: list[Event] = []
    conflicts = []
    for event in ordered:
        active = [prior for prior in active if prior.start + prior.duration > event.start]
        conflicts.extend((prior, event) for prior in active)
        active.append(event)
    return conflicts


def check_calendar(path: Path) -> int:
    """Print conflicts found after expanding the calendar's supported recurrences."""
    events = from_ics(path.read_text(encoding="utf-8"))
    occurrences = []
    for event in events:
        occurrences.extend(expand(event, limit=MAX_OCCURRENCES - len(occurrences)))
    conflicts = find_conflicts(occurrences)
    if not conflicts:
        print(f"No conflicts across {len(occurrences)} occurrences")
        return 0
    for first, second in conflicts:
        print(f"CONFLICT {first.start.isoformat()} [{first.summary}] / {second.start.isoformat()} [{second.summary}]")
    print(f"{len(conflicts)} conflict(s) across {len(occurrences)} occurrences")
    return 1


def demo(path: Path) -> None:
    event = Event(datetime(2026, 1, 5, 9, tzinfo=UTC), timedelta(minutes=30), "Planning, sync", Recurrence("WEEKLY", count=3))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_ics([event]), encoding="utf-8")
    imported = from_ics(path.read_text(encoding="utf-8"))[0]
    print(f"Wrote {path}: {len(expand(imported))} occurrences")
    for occurrence in expand(imported): print(" ", occurrence.start.isoformat(), occurrence.summary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--demo", action="store_true")
    mode.add_argument("--check", type=Path, metavar="ICS", help="expand supported recurrence and report overlaps")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "examples/team.ics")
    args = parser.parse_args()
    if args.demo: demo(args.output)
    elif args.check:
        try:
            raise SystemExit(check_calendar(args.check))
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
