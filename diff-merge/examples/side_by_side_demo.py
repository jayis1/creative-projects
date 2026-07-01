"""
Side-by-side diff example.

Demonstrates the side-by-side visual diff renderer with colour output.
"""

from diff_merge import side_by_side

a = [
    "def greet(name):",
    "    print('Hello, ' + name)",
    "    return True",
    "",
    "greet('World')",
]

b = [
    "def greet(name):",
    "    print(f'Hello, {name}!')",
    "    return True",
    "",
    "greet('World')",
    "greet('Python')",
]

if __name__ == "__main__":
    lines = side_by_side(a, b, width=70, color=True)
    for line in lines:
        print(line)