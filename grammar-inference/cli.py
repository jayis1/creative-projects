"""CLI for grammar-inference."""
import argparse
from core import learn


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo")
    demo.add_argument("--seed", type=int, default=7)
    train = sub.add_parser("learn")
    train.add_argument("sentences", nargs="+")
    train.add_argument("--samples", type=int, default=1)
    train.add_argument("--seed", type=int, default=7)
    args = parser.parse_args(argv)
    corpus = ["red birds fly", "small birds fly", "red birds sing", "small birds sing"] if args.command == "demo" else args.sentences
    try:
        grammar = learn(corpus)
        if args.command == "demo":
            print(f"corpus sentences: {len(corpus)}")
            print(f"learned span rules: {grammar.rule_count}")
            print(f"sample: {grammar.sample(seed=args.seed)}")
        else:
            if not 1 <= args.samples <= 100:
                parser.error("--samples must be between 1 and 100")
            for i in range(args.samples):
                print(grammar.sample(seed=args.seed + i))
    except ValueError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
