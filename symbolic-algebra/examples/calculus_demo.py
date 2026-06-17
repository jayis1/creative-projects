"""
Example: Advanced calculus operations.

Run with: python3 examples/calculus_demo.py
"""

from symbolic_cas import parse, x, y

print("=" * 60)
print("Symbolic CAS — Calculus Demo")
print("=" * 60)

# ─── Chain Rule ───
print("\n--- Chain Rule ---")
f = parse("sin(cos(x))")
df = f.diff('x').simplify()
print(f"  f(x) = {f.pretty()}")
print(f"  f'(x) = {df.pretty()}")

# ─── Product Rule ───
print("\n--- Product Rule ---")
f = parse("x * sin(x)")
df = f.diff('x').simplify()
print(f"  f(x) = {f.pretty()}")
print(f"  f'(x) = {df.pretty()}")

# ─── Quotient Rule ───
print("\n--- Quotient Rule ---")
f = parse("x / sin(x)")
df = f.diff('x').simplify()
print(f"  f(x) = {f.pretty()}")
print(f"  f'(x) = {df.pretty()}")

# ─── General Power Rule ───
print("\n--- General Power Rule: d/dx(x^x) ---")
f = parse("x^x")
df = f.diff('x').simplify()
print(f"  f(x) = {f.pretty()}")
print(f"  f'(x) = {df.pretty()}")

# ─── Higher-Order Derivatives ───
print("\n--- Higher-Order Derivatives ---")
f = parse("x^4")
df1 = f.diff('x').simplify()
df2 = df1.diff('x').simplify()
df3 = df2.diff('x').simplify()
print(f"  f(x)  = {f.pretty()}")
print(f"  f'(x) = {df1.pretty()}")
print(f"  f''(x)= {df2.pretty()}")
print(f"  f'''(x)= {df3.pretty()}")

# ─── Taylor Series at Different Points ───
print("\n--- Taylor Series ---")
for func_str in ["exp(x)", "sin(x)", "cos(x)", "ln(x + 1)"]:
    f = parse(func_str)
    ts = f.taylor('x', point=0, order=5)
    print(f"  {func_str} ≈ {ts.pretty()}")

# ─── Partial Derivatives ───
print("\n--- Partial Derivatives ---")
f = parse("x^2 * y + sin(x)")
df_dx = f.diff('x').simplify()
df_dy = f.diff('y').simplify()
print(f"  f(x,y) = {f.pretty()}")
print(f"  ∂f/∂x = {df_dx.pretty()}")
print(f"  ∂f/∂y = {df_dy.pretty()}")

# ─── Limits ───
print("\n--- Limits ---")
limits = [
    ("sin(x)/x", 0),
    ("(exp(x) - 1)/x", 0),
    ("1/x", "inf"),
]
for expr_str, point in limits:
    expr = parse(expr_str)
    result = expr.limit('x', point)
    print(f"  lim(x→{point}) {expr_str} = {result}")