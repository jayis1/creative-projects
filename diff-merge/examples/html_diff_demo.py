"""
HTML diff output example.

Generates an HTML diff document and saves it to disk.
"""

from diff_merge import html_diff_document

a = [
    "import os",
    "",
    "def main():",
    "    print('hello')",
    "    return 0",
    "",
    "if __name__ == '__main__':",
    "    main()",
]

b = [
    "import os",
    "import sys",
    "",
    "def main():",
    "    print('hello world')",
    "    return 0",
    "",
    "if __name__ == '__main__':",
    "    main()",
]

if __name__ == "__main__":
    doc = html_diff_document(a, b, fromfile="v1.py", tofile="v2.py",
                             title="Code Review: v1 → v2")
    with open("diff_output.html", "w") as f:
        f.write(doc)
    print("HTML diff saved to diff_output.html")
    print(f"Document size: {len(doc)} bytes")