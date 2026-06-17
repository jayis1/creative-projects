"""
Example: Basic usage of the Symbolic CAS.

Run with: python3 examples/basic_usage.py
"""

from symbolic_cas import parse, x, y, sin, cos, exp, ln, sqrt

print("=" * 60)
print("Symbolic CAS — Basic Usage Examples")
print("=" * 60)

# ─── Parsing & Simplification ───
print("\n--- Parsing & Simplification ---")
expr = parse("sin(x)^2 + cos(x)^2")
print(f"  Input:    {expr}")
print(f"  Simplify: {expr.simplify()}")

expr = parse("3*x^2 + 2*x - 5")
print(f"  Input:    {expr}")
print(f"  Pretty:   {expr.pretty()}")

# ─── Differentiation ───
print("\n--- Differentiation ---")
f = parse("x^3 + 2*x^2 - x + 5")
df = f.diff('x').simplify()
print(f"  f(x) = {f.pretty()}")
print(f"  f'(x) = {df.pretty()}")
print(f"  f'(1) = {df.evaluate({'x': 1})}")

# ─── Equation Solving ───
print("\n--- Equation Solving ---")
eq = parse("x^2 - 5*x + 6")
roots = eq.solve('x')
print(f"  Equation: {eq.pretty()} = 0")
print(f"  Roots: {[r.pretty() for r in roots]}")

# ─── Taylor Series ───
print("\n--- Taylor Series ---")
ts = parse("sin(x)").taylor('x', point=0, order=5)
print(f"  sin(x) ≈ {ts.pretty()}")
print(f"  sin(0.5) ≈ {ts.evaluate({'x': 0.5}):.6f}")
print(f"  sin(0.5) = {sin(0.5).evaluate():.6f}")

# ─── Numerical Integration ───
print("\n--- Numerical Integration ---")
result = parse("exp(x)").integrate('x', 0, 1)
print(f"  ∫₀¹ exp(x) dx ≈ {result:.10f}")
print(f"  Exact: e - 1 = {2.718281828 - 1:.10f}")

# ─── Newton's Method ───
print("\n--- Newton's Method ---")
f = parse("x^2 - 2")
root = f.newton_solve('x', x0=1.5)
print(f"  x² - 2 = 0")
print(f"  Root: x ≈ {root:.10f}")
print(f"  √2 = {2**0.5:.10f}")

# ─── LaTeX Output ───
print("\n--- LaTeX Output ---")
expr = parse("x^2 + 2*x + 1")
print(f"  Expression: {expr.pretty()}")
print(f"  LaTeX: {expr.to_latex()}")

expr = parse("sin(x)/cos(x)")
print(f"  Expression: {expr.pretty()}")
print(f"  LaTeX: {expr.to_latex()}")

# ─── Limits (new feature!) ───
print("\n--- Limits ---")
expr = parse("sin(x)/x")
lim = expr.limit('x', 0)
print(f"  lim(x→0) sin(x)/x = {lim}")

expr = parse("1/x")
lim = expr.limit('x', 'inf')
print(f"  lim(x→∞) 1/x = {lim}")

# ─── Serialization (new feature!) ───
print("\n--- Serialization ---")
from symbolic_cas.serialize import to_json, from_json
expr = parse("x^2 + 2*x + 1")
json_str = to_json(expr)
print(f"  Expression: {expr.pretty()}")
print(f"  JSON: {json_str}")
restored = from_json(json_str)
print(f"  Restored: {restored.pretty()}")
print(f"  Round-trip OK: {expr == restored}")