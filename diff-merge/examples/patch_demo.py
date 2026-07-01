"""Example: patch generation and application."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from diff_merge import unified_diff, parse_unified_diff, apply_patch

original = [
    "import os\n",
    "import sys\n",
    "\n",
    "def main():\n",
    "    print('Hello World')\n",
    "    return 0\n",
    "\n",
    "if __name__ == '__main__':\n",
    "    main()\n",
]

modified = [
    "import os\n",
    "import sys\n",
    "import json\n",
    "\n",
    "def main():\n",
    "    print('Hello, World!')\n",
    "    data = json.loads('{}')\n",
    "    return 0\n",
    "\n",
    "if __name__ == '__main__':\n",
    "    main()\n",
]

# Generate a unified diff
print("=== Generated Patch ===")
patch = unified_diff(original, modified, fromfile="main.py", tofile="main.py")
for line in patch:
    print(line)

# Parse and apply the patch
print("\n=== Applying Patch ===")
hunks = parse_unified_diff(patch)
result = apply_patch(original, hunks)
print(f"Applied: {result.applied_hunks} hunks, rejected: {result.rejected_hunks}")
print(f"Match: {result.patched == modified}")

# Show the patched content
print("\n=== Patched Content ===")
for line in result.patched:
    print(line, end="")