"""Example: basic diff operations."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from diff_merge import myers_diff, patience_diff, histogram_diff, lcs_diff
from diff_merge.myers import Operation

a = ["def hello():", "    print('Hello')", "    return 0"]
b = ["def hello():", "    print('Hi there')", "    return 1"]

print("=== Myers Diff ===")
ops = myers_diff(a, b)
for op in ops:
    print(f"  {op}")

print("\n=== Patience Diff ===")
ops = patience_diff(a, b)
for op in ops:
    print(f"  {op}")

print("\n=== Histogram Diff ===")
ops = histogram_diff(a, b)
for op in ops:
    print(f"  {op}")

print("\n=== LCS Diff ===")
ops = lcs_diff(a, b)
for op in ops:
    print(f"  {op}")

print("\n=== Unified Diff Output ===")
from diff_merge import unified_diff
for line in unified_diff(a, b, fromfile="hello.py", tofile="hello.py"):
    print(line)