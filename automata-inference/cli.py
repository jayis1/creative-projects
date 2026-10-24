"""Command line interface for automata-inference."""
import argparse
import json
import sys

from automata_inference import infer


def main(argv=None):
    parser = argparse.ArgumentParser(description="Infer a DFA from positive/negative JSON word lists")
    parser.add_argument("samples", help="JSON file with positive and negative arrays")
    parser.add_argument("--minimize", action="store_true", help="minimize the inferred DFA")
    args = parser.parse_args(argv)
    try:
        with open(args.samples, encoding="utf-8") as stream:
            data = json.load(stream)
        dfa = infer(data["positive"], data["negative"])
        if args.minimize:
            dfa = dfa.minimize()
        print(json.dumps(dfa.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
