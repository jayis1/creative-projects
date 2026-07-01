"""Example: three-way merge."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from diff_merge import three_way_merge

# Common ancestor
base = [
    "def calculate(a, b):\n",
    "    result = a + b\n",
    "    return result\n",
    "\n",
    "def main():\n",
    "    print(calculate(1, 2))\n",
]

# Our version: added error handling
ours = [
    "def calculate(a, b):\n",
    "    if a is None or b is None:\n",
    "        raise ValueError('None input')\n",
    "    result = a + b\n",
    "    return result\n",
    "\n",
    "def main():\n",
    "    print(calculate(1, 2))\n",
]

# Their version: changed operation to multiply
theirs = [
    "def calculate(a, b):\n",
    "    result = a * b\n",
    "    return result\n",
    "\n",
    "def main():\n",
    "    print(calculate(3, 4))\n",
]

print("=== Three-Way Merge ===")
result = three_way_merge(base, ours, theirs)
print(f"Clean: {result.clean}")
print(f"Conflicts: {len(result.conflicts)}")
print()
for line in result.lines:
    print(line, end="")

# Clean merge example
print("\n\n=== Clean Merge Example ===")
base2 = ["line1\n", "line2\n", "line3\n"]
ours2 = ["line1\n", "line2 ours\n", "line3\n"]
theirs2 = ["line1\n", "line2\n", "line3 theirs\n"]
result2 = three_way_merge(base2, ours2, theirs2)
print(f"Clean: {result2.clean}")
for line in result2.lines:
    print(line, end="")