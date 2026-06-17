# symbolic-algebra

A **symbolic algebra system** (computer algebra system / CAS) implemented in pure Python with no external dependencies. It supports parsing, differentiation, simplification, equation solving, expression expansion, Taylor series, numerical integration, Newton's method root finding, factorization, trigonometric identity simplification, pretty-printing, LaTeX output, and an interactive REPL.

## Features

- **Expression Parsing** — Parse infix math expressions with proper operator precedence: `3*x^2 + 2*x - 5`
- **Symbolic Differentiation** — Compute exact derivatives using chain rule, product rule, quotient rule, power rule, and trig/exp/log derivatives
- **Multi-pass Simplification** — Constant folding, identity elimination (`x+0=x`, `x*1=x`), double-negation cancellation, algebraic reduction, trig identity recognition (`sin²x+cos²x=1`, `1-cos²x=sin²x`)
- **Equation Solving** — Solve linear (`ax+b=0`) and quadratic (`ax²+bx+c=0`) equations, plus higher-degree polynomials via rational root theorem
- **Newton's Method** — Numerical root-finding for non-polynomial equations: `cos(x)=0`, `exp(x)=x+2`, etc.
- **Expression Expansion** — Distributive law expansion: `a*(b+c)` → `a*b + a*c`
- **Taylor Series** — Symbolic Taylor expansion around any point to arbitrary order
- **Numerical Integration** — Simpson's rule integration of any expression over an interval
- **Factorization** — Extract common factors from sum expressions: `2*x + 3*x` → `x*(2+3)`
- **Pretty-Printing** — Human-readable output with minimal parentheses based on operator precedence
- **LaTeX Output** — Convert any expression to publication-ready LaTeX
- **Interactive REPL** — Built-in command-line interface for exploration

## Usage

### Python API

```python
from symbolic import parse, x, y, sin, cos, exp, ln, sqrt, sym

# Build expressions via Python operators
f = 3 * x**2 + 2 * x - 5
print(f)          # (((3 * (x^2)) + (2 * x)) - 5)

# Parse from strings
g = parse("sin(x)^2 + cos(x)^2")
print(g.simplify())  # 1 (trig identity recognized!)

# Differentiation
df = f.diff('x')
print(df.simplify())  # ((6 * x) + 2)

# Chain rule
h = parse("exp(sin(x))")
dh = h.diff('x').simplify()
print(dh)  # (exp(sin(x)) * cos(x))

# Equation solving
eq = parse("x^2 - 5*x + 6")
roots = eq.solve('x')
print(roots)  # [Num(2), Num(3)]

# Newton's method for non-polynomial equations
root = parse("cos(x)").newton_solve('x', x0=1.0)
print(root)  # ≈ 1.5707963268 (π/2)

# Taylor series expansion
ts = parse("sin(x)").taylor('x', point=0, order=5)
print(ts.pretty())  # x - 1/6 * x^3 + 1/120 * x^5

# Numerical integration (Simpson's rule)
result = parse("exp(x)").integrate('x', 0, 1)
print(result)  # ≈ 1.71828... (= e - 1)

# Factorization
factored = parse("x + x^2").factor('x')
print(factored.pretty())  # x * (1 + x)

# Pretty-printing
expr = parse("3*x^2 + 2*x - 5")
print(expr.pretty())  # 3 * x^2 + 2 * x - 5

# LaTeX output
print(f.to_latex())  # \frac{3 \cdot {x}^{2} + 2 \cdot x}{- 5}

# Substitution
expr = parse("x^2 + y")
result = expr.substitute({'x': 3, 'y': sym('z')})
print(result)  # ((3^2) + z)
```

### REPL

```bash
python3 symbolic.py
```

```
>>> 3*x^2 + 2*x - 5
  Simplified: ...
>>> diff sin(x)^2 + cos(x)^2
  d/dx(...) = 0
>>> solve x^2 - 5*x + 6
  Solutions: 2, 3
>>> newton cos(x)
  Root (Newton): x ≈ 1.5707963268
>>> taylor exp(x)
  Taylor series: 1 + x + 1/2*x^2 + ...
>>> integrate exp(x)
  ∫₀¹ f(x)dx ≈ 1.7182818285
>>> factor x + x^2
  Factored: x * (1 + x)
>>> latex x^2 + 1
  LaTeX: {x}^{2} + 1
>>> pretty 3*x^2 + 2*x - 5
  3 * x^2 + 2 * x - 5
```

## How It Works

### Architecture

The system is built around an **immutable AST** (Abstract Syntax Tree):

- **`Expr`** — Abstract base class; all nodes are immutable and hashable
- **`Num`** — Numeric constants (integers and floats)
- **`Sym`** — Symbolic variables (`x`, `y`, `theta`, etc.)
- **`BinOp`** — Binary operations (`+`, `-`, `*`, `/`)
- **`UnaryOp`** — Unary negation
- **`Pow`** — Exponentiation (`base^exponent`)
- **`Func`** — Named functions (`sin`, `cos`, `exp`, `ln`, `sqrt`, etc.)

### Differentiation

Implemented via recursive structural pattern matching:
- **Power rule**: `d/dx(x^n) = n·x^(n-1)`
- **Product rule**: `d/dx(u·v) = u'·v + u·v'`
- **Quotient rule**: `d/dx(u/v) = (u'v - uv')/v²`
- **Chain rule**: Built into all composite derivatives
- **General exponentiation**: `d/dx(u^v) = u^v·(v'·ln(u) + v·u'/u)`
- **Trig/hyperbolic/inverse**: Full support for 16+ functions

### Simplification

Multi-pass fixed-point iteration applies rules until convergence:
1. Constant folding (`2+3` → `5`)
2. Additive/multiplicative identities (`x+0=x`, `x·1=x`, `x·0=0`)
3. Double negation (`-(-x)` → `x`)
4. Like-term merging via subtraction (`x-x` → `0`)
5. Constant association (`2·(3·x)` → `6·x`)
6. Power simplification (`x^1=x`, `x^0=1`, `x·x=x²`)
7. Function evaluation on constants (`sin(0)` → `0`)
8. **Trigonometric identities** (`sin²x+cos²x=1`, `1-sin²x=cos²x`, `1-cos²x=sin²x`)

### Taylor Series

Computes `f(x) ≈ Σ f^(n)(a)/n! · (x-a)^n` by:
1. Symbolically differentiating `f` to each order
2. Evaluating at the expansion point `a`
3. Constructing the polynomial approximation

### Numerical Integration

Uses **Simpson's rule** with configurable number of intervals:
`∫_a^b f(x)dx ≈ h/3 · [f(a) + 4·f(x₁) + 2·f(x₂) + ... + f(b)]`

### Newton's Method

Iterates `x_{n+1} = x_n - f(x_n)/f'(x_n)` with:
- Automatic derivative computation
- Convergence detection (tolerance 1e-10)
- Divergence/zero-derivative error handling

### Solving

- **Linear**: Extract coefficients, solve `ax + b = 0`
- **Quadratic**: Apply discriminant formula `(-b ± √(b²-4ac)) / 2a`
- **Higher degree**: Rational root theorem for integer-coefficient polynomials

### Parsing

Recursive descent parser with proper precedence:
1. Additive (`+`, `-`) — lowest precedence
2. Multiplicative (`*`, `/`)
3. Unary (`-x`, `+x`)
4. Power (`^`) — right-associative
5. Atoms (numbers, symbols, function calls, parenthesized subexpressions)

## Supported Functions

| Function | Description |
|----------|-------------|
| `sin`, `cos`, `tan` | Trigonometric |
| `asin`, `acos`, `atan` | Inverse trigonometric |
| `sinh`, `cosh`, `tanh` | Hyperbolic |
| `exp` | Exponential (eˣ) |
| `ln`, `log` | Natural logarithm |
| `log2`, `log10` | Base-2 and base-10 logarithm |
| `sqrt` | Square root |
| `abs` | Absolute value |
| `ceil`, `floor` | Rounding |
| `sign` | Sign function |

## Project Structure

```
symbolic-algebra/
├── symbolic.py     # Complete implementation (single file, no dependencies)
├── tests.py        # Comprehensive test suite (115 tests)
└── README.md       # This file
```

## Requirements

- Python 3.8+ (no external dependencies)

## License

MIT