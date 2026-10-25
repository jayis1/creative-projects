"""CLI for the trophic-web simulator."""
import argparse

from .io import load_web, write_csv
from .model import meadow, simulate


def main() -> int:
    parser = argparse.ArgumentParser(description="simulate a generalized Lotka–Volterra web")
    parser.add_argument("--steps", type=int, default=1000, help="integration steps (0..1,000,000)")
    parser.add_argument("--dt", type=float, default=0.01, help="positive finite step size")
    parser.add_argument("--model", help="JSON model file; defaults to the built-in meadow")
    parser.add_argument("--output", help="write every state to this CSV file")
    args = parser.parse_args()
    try:
        web, initial = load_web(args.model) if args.model else meadow()
        states = simulate(web, initial, args.dt, args.steps)
        if args.output:
            write_csv(args.output, web, states, args.dt)
    except (ValueError, OverflowError) as exc:
        parser.error(str(exc))
    print("time," + ",".join(web.names))
    stride = max(1, len(states) // 10)
    for i, state in enumerate(states):
        if i == 0 or i == len(states) - 1 or i % stride == 0:
            print(f"{i * args.dt:.6g}," + ",".join(f"{x:.6f}" for x in state))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
