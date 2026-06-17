# symbolic-algebra

A **symbolic algebra system** (computer algebra system / CAS) implemented in pure Python with no external dependencies. It supports parsing, differentiation, simplification, equation solving, expression expansion, LaTeX output, and an interactive REPL.

## Features

- **Expression Parsing** — Parse infix math expressions with proper operator precedence: `3*x^2 + 2*x - 5`
- **Symbolic Differentiation** — Compute exact derivatives using chain rule, product rule, quotient rule, power rule, and trig/exp/log derivatives
- **Multi-pass Simplification** — Constant folding, identity elimination (`x+0=x`, `x*1=x`), double-negation cancellation, algebraic reduction
- **Equation Solving** — Solve linear (`ax+b=0`) and quadratic (`ax²+bx+c=0`) equations, plus higher-degree polynomials via rational root theorem
- **Expression Expansion** — Distributive law expansion: `a*(b+c)` → `a*b + a*c`
- **Symbolic Substitution** — Replace symbols with values or other expressions
- **Numerical Evaluation** — Plug in values and compute results
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
print(g.simplify())  # Should simplify trig identities

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

# LaTeX output
print(f.to_latex())  # \left(\left(3 \cdot {x}\right)^{2} + 2 \cdot x\right) - 5

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
  d/dx(...) = ...
>>> solve x^2 - 5*x + 6
  Solutions: 2, 3
>>> latex x^2 + 1
  LaTeX: {x}^{2} + 1
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

### Simplification

Multi-pass fixed-point iteration applies rules until convergence:
1. Constant folding (`2+3` → `5`)
2. Additive/multiplicative identities (`x+0=x`, `x·1=x`, `x·0=0`)
3. Double negation (`-(-x)` → `x`)
4. Like-term merging via subtraction (`x-x` → `0`)
5. Constant association (`2·(3·x)` → `6·x`)
6. Power simplification (`x^1=x`, `x^0=1`)
7. Function evaluation on constants (`sin(0)` → `0`)

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
├── tests.py        # Test suite
└── README.md       # This file
```

## Requirements

- Python 3.8+ (no external dependencies)

## License

MIT