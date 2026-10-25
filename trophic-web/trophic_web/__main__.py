"""CLI for the trophic-web simulator."""
import argparse
from .model import meadow, simulate


def main() -> int:
    parser = argparse.ArgumentParser(description="simulate a three-species generalized Lotka–Volterra web")
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--dt", type=float, default=0.01)
    args = parser.parse_args()
    web, initial = meadow()
    try:
        states = simulate(web, initial, args.dt, args.steps)
    except (ValueError, OverflowError) as exc:
        parser.error(str(exc))
    print("time," + ",".join(web.names))
    for i, state in enumerate(states):
        if i == 0 or i == len(states) - 1 or i % max(1, len(states) // 10) == 0:
            print(f"{i * args.dt:.3f}," + ",".join(f"{x:.6f}" for x in state))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
