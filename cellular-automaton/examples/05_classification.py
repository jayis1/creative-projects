"""Example: Wolfram classification of elementary rules.

This example classifies all 256 Wolfram elementary rules and prints a
summary showing how many fall into each class.
"""
from cellular_automaton import classify_elementary_rule
from collections import Counter


def main():
    print("Wolfram Classification of Elementary Rules 0-255\n")
    print(f"{'Rule':>5}  {'Class':>5}  {'Entropy':>8}  {'Period':>6}  Description")
    print("-" * 80)

    classes: Counter = Counter()
    for n in range(256):
        result = classify_elementary_rule(n, width=51, steps=100)
        period_str = str(result.period) if result.period else "-"
        print(f"  {n:>3}   {result.classification:>5}  "
              f"{result.entropy:>8.4f}  {period_str:>6}  {result.description}")
        classes[result.classification] += 1

    print(f"\n{'='*80}")
    print("Summary:")
    for cls in ["I", "II", "III", "IV"]:
        count = classes.get(cls, 0)
        pct = 100 * count / 256
        print(f"  Class {cls}: {count:>3} rules ({pct:.1f}%)")


if __name__ == "__main__":
    main()