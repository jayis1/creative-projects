import argparse
from .sinogram_lab import demo


def main() -> None:
    parser = argparse.ArgumentParser(description="Toy parallel-beam tomography with algebraic reconstruction")
    parser.add_argument("--demo", action="store_true", help="run the deterministic reconstruction demo")
    parser.add_argument("--seed", type=int, default=7, help="noise seed (default: 7)")
    parser.add_argument("--size", type=int, default=12, help="square phantom size, 2..128 (default: 12)")
    args = parser.parse_args()
    if not 2 <= args.size <= 128:
        parser.error("--size must be between 2 and 128")
    print(demo(args.seed, args.size))


if __name__ == "__main__":
    main()
