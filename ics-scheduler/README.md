# ICS Scheduler

A dependency-free, bounded recurrence and conflict toolkit for a practical subset of iCalendar (ICS).

## Demo

```sh
python3 main.py --demo
```

The demo writes `examples/team.ics`, reloads it, and prints three weekly UTC occurrences.

## How it works

`Event` and `Recurrence` are immutable validated records. `expand` supports DAILY, WEEKLY, and MONTHLY recurrence, inclusive UNTIL dates, COUNT, and explicit occurrence limits. Monthly dates clamp to the last valid day (for example, January 31 becomes February 28).

The exporter/importer handles UTC timestamps, positive whole-second durations, escaped summaries, and the recurrence subset above. `find_conflicts` returns overlapping event pairs using half-open interval semantics: events whose endpoints merely touch do not conflict. The `--check ICS` command expands every event's supported recurrence, reports the exact overlapping pairings, and exits with status 1 when conflicts are present (0 for a clean calendar). ICS parsing and recurrence expansion impose size/count bounds.

This is deliberately an offline calendar-interchange utility, not a full RFC 5545 implementation or a calendar server. Unlike this repository's scheduling-adjacent tournament fixture generator, it focuses on parsing and emitting calendar files with recurrence rules.

## Usage

From this directory:

```sh
python3 main.py --demo
python3 main.py --check examples/team.ics
python3 -m unittest discover -s tests -v
```

To select an output location for the demo, run `python3 main.py --demo --output /path/to/calendar.ics`.

Library entry points: `Event`, `Recurrence`, `expand`, `to_ics`, `from_ics`, and `find_conflicts` in `main.py`.

## Known Issues (Resolved)

- Imported SUMMARY values with unknown backslash escapes were silently altered (for example, `\\q` became `q`). The parser now rejects unsupported escapes with `ValueError`; regression test: `test_rejects_unknown_summary_escape` (observed failing before the fix, passing afterward).

## Requirements and limitations

Python 3.10 or newer; standard library only. Import supports the VEVENT subset emitted by this tool. It rejects unsupported time zones, duration formats, recurrence fields, and malformed records rather than attempting lossy interpretation. COUNT and UNTIL are mutually exclusive. Demo output is written to the selected path.
