"""
Example 5: HTML visualization and batch processing.

Generates HTML reports for truth tables, K-maps, and runs batch minimization
on multiple functions with JSON export.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from logicmin import (
    BooleanFunction, QuineMcCluskey, full_report_html,
    BatchProcessor, batch_summary, batch_to_json, truth_table_html, kmap_html,
)

# Generate a full HTML report for a 4-var function
f = BooleanFunction(n_vars=4, minterms=[4, 8, 10, 11, 12, 15], dontcare=[9, 14])
qm = QuineMcCluskey(4)
result = qm.minimize(f)
html = full_report_html(f, result)

output_dir = os.path.dirname(__file__)
output_path = os.path.join(output_dir, "report_output.html")
with open(output_path, "w") as fh:
    fh.write(html)
print(f"Full report saved to {output_path}")

# Also generate just a K-map
kmap_html_text = kmap_html(f)
kmap_path = os.path.join(output_dir, "kmap_output.html")
with open(kmap_path, "w") as fh:
    fh.write(kmap_html_text)
print(f"K-map saved to {kmap_path}")

# Batch processing: minimize multiple functions
print("\n--- Batch Processing ---")
functions = [
    BooleanFunction(n_vars=3, minterms=[1, 3, 5, 7], name="f1"),
    BooleanFunction(n_vars=3, minterms=[0, 2, 4, 6], name="f2"),
    BooleanFunction(n_vars=4, minterms=[4, 8, 10, 11, 12, 15], dontcare=[9, 14], name="f3"),
    BooleanFunction(n_vars=4, minterms=[0, 1, 2, 5, 7, 8, 9, 10, 14], name="f4"),
    BooleanFunction(n_vars=2, minterms=[1, 2], name="xor"),
]

bp = BatchProcessor(minimizer="qm")
entries = bp.process_batch(functions)
summary = batch_summary(entries)

print(f"{'Name':<10} {'Vars':>4} {'Terms':>6} {'Lits':>5} {'Time(ms)':>10} {'OK':>4}")
print("-" * 45)
for e in entries:
    ok = "✓" if e.correct else "✗"
    print(f"{e.name:<10} {e.n_vars:>4} {e.n_terms:>6} {e.n_literals:>5} {e.elapsed_ms:>10.2f} {ok:>4}")

print(f"\nSummary: {summary.n_functions} functions, "
      f"{summary.total_terms} terms, {summary.total_literals} literals, "
      f"{summary.total_time_ms:.1f}ms")
print(f"All correct: {'Yes' if summary.all_correct else 'NO'}")

# Export to JSON
json_output = batch_to_json(entries)
print(f"\nJSON export ({len(json_output)} chars)")