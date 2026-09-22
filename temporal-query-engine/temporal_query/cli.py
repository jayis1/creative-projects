"""Command-line interface for interval queries."""
from __future__ import annotations

import argparse
import json
import logging
from . import Event, IntervalIndex, load_events

LOGGER = logging.getLogger(__name__)


def _event_arg(raw: str) -> Event:
    bits = raw.split(":", 3)
    if len(bits) < 3:
        raise ValueError("event must be ID:START:END[:LABEL]")
    return Event(bits[0], float(bits[1]), float(bits[2]), bits[3] if len(bits) == 4 else "")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Query labelled half-open time intervals")
    parser.add_argument("start", type=float)
    parser.add_argument("end", type=float)
    parser.add_argument("--event", action="append", default=[], metavar="ID:START:END[:LABEL]")
    parser.add_argument("--events-file", metavar="PATH", help="load events from JSON or TOML")
    parser.add_argument("--label", help="only return events with this exact label")
    parser.add_argument("--verbose", action="store_true", help="enable diagnostic logging")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING,
                        format="%(levelname)s %(name)s: %(message)s")
    try:
        events = load_events(args.events_file) if args.events_file else []
        events.extend(_event_arg(raw) for raw in args.event)
        index = IntervalIndex(events)
        results = index.overlaps(args.start, args.end, args.label)
        LOGGER.info("matched %d events", len(results))
        print(json.dumps([{"id": e.id, "start": e.start, "end": e.end, "label": e.label}
                          for e in results], sort_keys=True))
        return 0
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
