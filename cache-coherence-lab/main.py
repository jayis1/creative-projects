"""CLI for the cache-coherence lab."""
import argparse
import json
from coherence import MESISimulator

def main():
    parser = argparse.ArgumentParser(description="Simulate MESI cache coherence from JSON trace records")
    parser.add_argument("trace", nargs="?", help="JSON file containing [[core, op, address], ...]")
    parser.add_argument("--cores", type=int, default=2)
    parser.add_argument("--capacity", type=int, default=4)
    parser.add_argument("--line-size", type=int, default=16)
    args = parser.parse_args()
    if args.trace:
        with open(args.trace, encoding="utf-8") as source:
            trace = json.load(source)
    else:
        trace = [[0, "R", 0], [1, "R", 0], [0, "W", 0], [1, "R", 0]]
    sim = MESISimulator(args.cores, args.capacity, args.line_size)
    sim.run(trace)
    print(json.dumps(sim.report(), indent=2))

if __name__ == "__main__":
    main()
