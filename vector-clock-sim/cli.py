import argparse
from vector_clock_sim import Trace, TraceError


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze causal event traces")
    parser.add_argument("processes", nargs="+", help="process names")
    parser.add_argument("--event", action="append", default=[], metavar="P:K[:PEER[:PAYLOAD]]",
                        help="record an event; repeat for a sequence")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--summary", action="store_true", help="emit aggregate counts")
    args = parser.parse_args()
    try:
        trace = Trace(tuple(args.processes))
        actions = [tuple(x.split(":", 3)) for x in args.event]
        trace.record(actions)
    except TraceError as exc:
        parser.error(str(exc))
    if args.json:
        print(trace.to_json())
    elif args.summary:
        for key, value in trace.summary().items():
            print(f"{key}: {value}")
    else:
        for event in trace.events:
            print(f"{event.process}: {event.kind} L={event.lamport} V={event.vector}")
        print(f"concurrent pairs: {len(trace.concurrent_pairs())}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
