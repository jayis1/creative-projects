"""
Directory diff example.

Compares two directory trees and shows which files were added, removed,
or modified.
"""

import tempfile
import os
import textwrap

from diff_merge import diff_directories

if __name__ == "__main__":
    # Create two temporary directories
    tmp = tempfile.mkdtemp()
    dir_a = os.path.join(tmp, "v1")
    dir_b = os.path.join(tmp, "v2")
    os.makedirs(dir_a)
    os.makedirs(dir_b)

    # Populate v1
    with open(os.path.join(dir_a, "main.py"), "w") as f:
        f.write("print('hello')\n")
    with open(os.path.join(dir_a, "utils.py"), "w") as f:
        f.write("def helper():\n    pass\n")

    # Populate v2 (modify main.py, remove utils.py, add config.py)
    with open(os.path.join(dir_b, "main.py"), "w") as f:
        f.write("print('hello world')\n")
    with open(os.path.join(dir_b, "config.py"), "w") as f:
        f.write("DEBUG = True\n")

    result = diff_directories(dir_a, dir_b)

    print("Directory diff results:")
    print("=" * 50)
    for change in result.changes:
        if change.change_type.value == "added":
            print(f"  + {change.path}")
        elif change.change_type.value == "removed":
            print(f"  - {change.path}")
        elif change.change_type.value == "modified":
            if change.diffstat:
                print(f"  ~ {change.path}  ({change.diffstat.summary()})")
            else:
                print(f"  ~ {change.path}")

    print()
    print(result.summary())