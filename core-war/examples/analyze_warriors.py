"""
Example: Analyze all built-in warriors and compare strategies.

This script loads all warriors from the warriors/ directory, analyzes
their strategies, and prints a comparison table.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core_war import load_warriors_from_dir, StrategyAnalyzer
from core_war.strategy_analyzer import StrategyType

WARRIORS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "warriors")


def main():
    warriors = load_warriors_from_dir(WARRIORS_DIR)
    analyzer = StrategyAnalyzer()

    print(f"Analyzing {len(warriors)} warriors:\n")

    # Analyze each warrior
    results = []
    for w in warriors:
        result = analyzer.analyze(w)
        results.append((w, result))

    # Print summary table
    print(f"{'Warrior':<15} {'Strategy':<15} {'Secondary':<15} {'Instrs':>6} "
          f"{'Aggr':>5} {'Resil':>5} {'Procs':>6} {'Vulns':>6}")
    print("-" * 80)
    for w, r in results:
        secondary = r.secondary_strategy.value if r.secondary_strategy else "-"
        print(f"{w.name:<15} {r.strategy.value:<15} {secondary:<15} "
              f"{r.instruction_count:>6} {r.estimated_aggressiveness:>5}/10 "
              f"{r.estimated_resilience:>5}/10 {r.process_estimate:>6} "
              f"{len(r.vulnerabilities):>6}")

    # Print detailed analysis for each
    print("\n" + "=" * 80)
    print("Detailed Analysis")
    print("=" * 80)
    for w, r in results:
        print(f"\n{'─' * 60}")
        print(f"  {w.name}")
        print(f"{'─' * 60}")
        print(f"  Strategy:      {r.strategy.value}")
        if r.secondary_strategy:
            print(f"  Secondary:     {r.secondary_strategy.value}")
        print(f"  Aggressiveness: {r.estimated_aggressiveness}/10")
        print(f"  Resilience:     {r.estimated_resilience}/10")
        print(f"  Process est:   {r.process_estimate}")
        print(f"  Self-modifying: {r.self_modifying}")

        if r.vulnerabilities:
            print(f"  Vulnerabilities:")
            for v in r.vulnerabilities:
                print(f"    [{v.severity.upper():>8}] {v.description}")

        # Opcode breakdown
        print(f"  Opcodes:")
        for name, count in r.opcode_freq.most_common():
            pct = r.opcode_freq.percentage(name)
            bar = "█" * int(pct / 5)
            print(f"    {name:<6} {count:>3} ({pct:>5.1f}%) {bar}")


if __name__ == "__main__":
    main()