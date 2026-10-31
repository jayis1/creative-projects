# Calendar Weaver

A dependency-free recurring-event planner that detects collisions and searches weekly schedules for available slots.

It expands weekday recurrence rules over a bounded date range, treats intervals as half-open (back-to-back events are valid), and reports conflicts or available windows.

## Usage

```sh
python3 main.py --demo
```

The demo schedules recurring focus blocks and prints conflicts plus candidate free windows. Event times use local wall-clock minutes after midnight; dates are ISO `YYYY-MM-DD`.

## Design

Each event has an inclusive start/end date, a set of ISO weekdays (Monday=0), start minute and positive duration. Expansion is bounded by the requested horizon. Pairwise collision checks operate on expanded occurrences and preserve event identity, making the output useful for resolving conflicts.

## Testing

Run `python3 -m unittest discover -v` from this directory.

## Limits

No timezone/DST conversion, external calendar import or persistence. All recurrence is weekly and local-time only.
