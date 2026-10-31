# Calendar Weaver

A dependency-free recurring-event planner that detects collisions and searches weekly schedules for available slots. Unlike a textbook weekly timetable, it clips each weekday recurrence to inclusive date bounds and supports direct JSON input for real schedules.

It expands weekday recurrence rules over a bounded date range, treats intervals as half-open (back-to-back events are valid), and reports conflicts or available windows. Dates are local wall-clock dates, weekdays use Monday=0, and times use 24-hour `HH:MM`.

## Quick demo

From this directory:

```sh
python3 main.py
```

Expected output:

```text
Conflicts:
  2026-11-02: Focus 09:00-10:30 overlaps Review 10:00-10:45
Free slots Monday: 10:45-17:00
```

## JSON input

Provide a JSON array with one object per recurring event:

```json
[
  {"name":"Planning", "start_date":"2026-11-02", "end_date":"2026-11-30", "weekdays":[0,2], "start":"09:30", "duration":45}
]
```

Run collision analysis for a bounded period and show free windows on a date:

```sh
python3 main.py --input example-events.json --from 2026-11-02 --to 2026-11-30 --day 2026-11-02
```

`--help` lists all options. Invalid JSON shapes, dates, times, or event constraints produce a command-line error. The expansion horizon is limited to 10 years.

## Design

Each event has a name, inclusive start/end dates, a set of ISO weekdays, start time and positive duration. Occurrences are expanded only on matching dates; conflict detection reports overlapping intervals for distinct event names. Free-slot search clips occupied time to a configurable workday window.

## Testing

Run `python3 -m unittest discover -v` from this directory.

## Known Issues (Resolved)

- The JSON time parser accepted `9:00` even though the documented format is strict `HH:MM`. The CLI now rejects non-zero-padded or malformed time strings; `test_clock_rejects_non_padded_hour` reproduced the defect before the fix and passes afterward.

## Limits

No timezone/DST conversion, external calendar import, persistence, or multi-day events. All recurrence is weekly and local-time only.
