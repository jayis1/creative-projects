"""
Example: Using the CLI interface.

This demonstrates the command-line interface for the Symbolic CAS.

Run with:
  python3 -m symbolic_cas.cli "sin(x)^2 + cos(x)^2"
  python3 -m symbolic_cas.cli --action diff "x^3 + 2*x"
  python3 -m symbolic_cas.cli --action solve "x^2 - 5*x + 6"
  python3 -m symbolic_cas.cli --action latex "sqrt(x^2 + 1)"
  python3 -m symbolic_cas.cli --action taylor "exp(x)" --order 6
  python3 -m symbolic_cas.cli --action integrate "x^2" --a 0 --b 1
  python3 -m symbolic_cas.cli --action eval "x^2 + 2*x" --vars x=3
  python3 -m symbolic_cas.cli --action limit "sin(x)/x" --point 0
  python3 -m symbolic_cas.cli --action json_export "x^2 + 1"
  python3 -m symbolic_cas.cli --repl
"""

import subprocess
import sys

examples = [
    # Basic simplify
    (["python3", "-m", "symbolic_cas.cli", "sin(x)^2 + cos(x)^2"], "Simplify sin²x + cos²x"),
    (["python3", "-m", "symbolic_cas.cli", "x^2 + 2*x + 1"], "Simplify polynomial"),

    # Differentiate
    (["python3", "-m", "symbolic_cas.cli", "--action", "diff", "x^3 + 2*x"], "Differentiate"),

    # Solve
    (["python3", "-m", "symbolic_cas.cli", "--action", "solve", "x^2 - 5*x + 6"], "Solve quadratic"),

    # LaTeX
    (["python3", "-m", "symbolic_cas.cli", "--action", "latex", "sqrt(x^2 + 1)"], "LaTeX output"),

    # Taylor
    (["python3", "-m", "symbolic_cas.cli", "--action", "taylor", "exp(x)", "--order", "6"], "Taylor series"),

    # Integrate
    (["python3", "-m", "symbolic_cas.cli", "--action", "integrate", "x^2", "--a", "0", "--b", "1"], "Numerical integration"),

    # Evaluate
    (["python3", "-m", "symbolic_cas.cli", "--action", "eval", "x^2 + 2*x", "--vars", "x=3"], "Evaluate"),

    # Limit
    (["python3", "-m", "symbolic_cas.cli", "--action", "limit", "sin(x)/x", "--point", "0"], "Limit"),

    # JSON export
    (["python3", "-m", "symbolic_cas.cli", "--action", "json_export", "x^2 + 1"], "JSON export"),
]

print("=" * 60)
print("Symbolic CAS — CLI Examples")
print("=" * 60)

for cmd, desc in examples:
    print(f"\n{desc}:")
    print(f"  $ {' '.join(cmd[2:])}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10,
                                cwd="/root/projects/creative-projects-improve/symbolic-algebra")
        if result.returncode == 0:
            print(f"  → {result.stdout.strip()}")
        else:
            print(f"  Error: {result.stderr.strip()}")
    except Exception as e:
        print(f"  Error: {e}")

print("\n" + "=" * 60)
print("To start the interactive REPL:")
print("  $ python3 -m symbolic_cas.cli --repl")
print("=" * 60)