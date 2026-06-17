# 🧮 Symbolic CAS

[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](tests/)

A **pure-Python symbolic algebra system** (computer algebra system / CAS) with zero external dependencies. Supports expression parsing, symbolic differentiation, simplification, equation solving, Taylor series, numerical integration, Newton's method, factorization, limit computation, serialization, pretty-printing, LaTeX output, and an interactive REPL / CLI.

## 📑 Table of Contents

- [Features](#-features)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Usage Examples](#-usage-examples)
  - [Python API](#python-api)
  - [CLI Interface](#cli-interface)
  - [REPL](#repl)
- [Architecture](#-architecture)
- [Supported Functions](#-supported-functions)
- [New Features in v2.0](#-new-features-in-v20)
- [Project Structure](#-project-structure)
- [Running Tests](#-running-tests)
- [Known Issues (Resolved)](#-known-issues-resolved)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [Changelog](#-changelog)
- [License](#-license)

## ✨ Features

| Category | Capabilities |
|----------|-------------|
| **Parsing** | Full infix notation with operator precedence, unary operators, function calls |
| **Differentiation** | Power, product, quotient, chain rules; 16+ trig/exp/log derivatives; partial derivatives |
| **Simplification** | Constant folding, identity elimination, double-negation, trig identities (`sin²x+cos²x=1`) |
| **Equation Solving** | Linear, quadratic, rational root theorem for higher-degree polynomials |
| **Newton's Method** | Numerical root-finding for non-polynomial equations |
| **Taylor Series** | Symbolic expansion around any point to arbitrary order |
| **Numerical Integration** | Simpson's rule with configurable precision |
| **Factorization** | Common factor extraction from sum expressions |
| **Limits** | Numerical limit computation (one-sided, two-sided, at infinity) |
| **Expansion** | Distributive law expansion, binomial expansion |
| **Pretty-Printing** | Minimal parentheses based on operator precedence |
| **LaTeX Output** | Publication-ready LaTeX rendering |
| **Serialization** | JSON export/import for expression trees |
| **CLI** | Full command-line interface with argparse flags |
| **REPL** | Interactive read-eval-print loop |

## 📦 Installation

### From Source

```bash
cd symbolic-algebra
pip install -e .
```

### Development Install

```bash
pip install -e ".[dev]"
```

### Requirements

- Python 3.8+ (no external dependencies!)

## 🚀 Quick Start

```python
from symbolic_cas import parse, x, sin, cos, exp

# Parse and simplify
expr = parse("sin(x)^2 + cos(x)^2")
print(expr.simplify())  # 1

# Differentiate
f = parse("x^3 + 2*x")
df = f.diff('x').simplify()
print(df)  # (3 * (x^2)) + 2

# Solve equations
roots = parse("x^2 - 5*x + 6").solve('x')
print(roots)  # [Num(2), Num(3)]

# Taylor series
ts = parse("exp(x)").taylor('x', point=0, order=5)
print(ts.pretty())

# Numerical integration
result = parse("exp(x)").integrate('x', 0, 1)
print(f"∫₀¹ exp(x) dx ≈ {result:.10f}")  # ≈ 1.7182818285

# Limits
result = parse("sin(x)/x").limit('x', 0)  # 1.0

# JSON export
from symbolic_cas.serialize import to_json
print(to_json(parse("x^2 + 1")))
```

## 📖 Usage Examples

### Python API

```python
from symbolic_cas import (
    parse, x, y, sin, cos, tan, exp, ln, sqrt,
    sym, num, simplify, differentiate
)

# ─── Construction ───
expr = 3 * x**2 + 2 * x - 5          # Via Python operators
expr = parse("3*x^2 + 2*x - 5")       # Via string parsing
expr = BinOp('+', Num(1), Sym('x'))    # Via explicit constructors

# ─── Differentiation ───
f = parse("exp(sin(x))")
df = f.diff('x').simplify()
print(df)  # exp(sin(x)) * cos(x)

# ─── Solving ───
# Quadratic
roots = parse("x^2 - 5*x + 6").solve('x')  # [2, 3]

# Newton's method for non-polynomial equations
root = parse("cos(x)").newton_solve('x', x0=1.0)  # ≈ π/2

# ─── Taylor Series ───
ts = parse("sin(x)").taylor('x', point=0, order=5)
# x - (1/6) * x^3 + (1/120) * x^5

# ─── Factorization ───
result = parse("x + x^2").factor('x')
# x * (1 + x)

# ─── Pretty-Printing & LaTeX ───
expr = parse("3*x^2 + 2*x - 5")
print(expr.pretty())   # 3 * x^2 + 2 * x - 5
print(expr.to_latex()) # 3 \cdot {x}^{2} + 2 \cdot x - 5

# ─── Limits (NEW) ───
lim = parse("sin(x)/x").limit('x', 0)       # 1.0
lim = parse("(exp(x)-1)/x").limit('x', 0)    # 1.0
lim = parse("1/x").limit('x', 'inf')          # 0.0

# ─── Serialization (NEW) ───
from symbolic_cas.serialize import to_json, from_json
json_str = to_json(parse("x^2 + 1"))
restored = from_json(json_str)  # Perfect round-trip

# ─── Expression Tree Metrics (NEW) ───
expr = parse("x^2 + 2*x + 1")
print(expr.depth())  # 4
print(expr.size())   # 9
```

### CLI Interface

```bash
# Simplify an expression
symbolic-cas "sin(x)^2 + cos(x)^2"

# Differentiate
symbolic-cas --action diff "x^3 + 2*x"

# Solve an equation
symbolic-cas --action solve "x^2 - 5*x + 6"

# Convert to LaTeX
symbolic-cas --action latex "sqrt(x^2 + 1)"

# Taylor series
symbolic-cas --action taylor "exp(x)" --order 6

# Numerical integration
symbolic-cas --action integrate "x^2" --a 0 --b 1

# Evaluate with variable bindings
symbolic-cas --action eval "x^2 + 2*x" --vars x=3

# Compute a limit
symbolic-cas --action limit "sin(x)/x" --point 0

# JSON export
symbolic-cas --action json_export "x^2 + 1"

# Use JSON output format
symbolic-cas --action simplify "x^2 + 1" --format json
```

### REPL

```bash
symbolic-cas --repl
# or: python3 -m symbolic_cas.cli --repl
```

```
>>> sin(x)^2 + cos(x)^2
  Simplified: 1
>>> diff x^3 + 2*x
  d/dx(...) = (3 * (x^2)) + 2
>>> solve x^2 - 5*x + 6
  Solutions: 2, 3
>>> taylor exp(x)
  Taylor series: 1 + x + (1/2) * (x^2) + ...
>>> limit sin(x)/x
  Limit: 1.0
>>> json x^2 + 1
  {"type": "BinOp", "op": "+", ...}
```

## 🏗️ Architecture

### Expression AST

All expressions are represented as an immutable, hashable AST:

```
Expr (abstract)
├── Num        — Numeric constants (int/float)
├── Sym        — Symbolic variables (x, y, theta, ...)
├── BinOp      — Binary operations (+, -, *, /)
├── UnaryOp    — Unary negation (-)
├── Pow        — Exponentiation (base^exponent)
└── Func        — Named functions (sin, cos, exp, ln, ...)
```

### Module Structure

```
symbolic_cas/
├── __init__.py     — Package exports and version
├── expr.py         — AST node classes (Expr, Num, Sym, BinOp, etc.)
├── parser.py       — Recursive descent expression parser
├── calculus.py      — Differentiation and Taylor series
├── simplify.py      — Simplification, expansion, and factorization
├── evaluate.py      — Numerical evaluation and integration
├── solve.py         — Equation solving and Newton's method
├── display.py       — Pretty-printing and LaTeX output
├── substitute.py    — Substitution and symbol collection
├── limits.py        — Limit computation (NEW)
├── serialize.py     — JSON serialization (NEW)
└── cli.py           — Command-line interface (NEW)
```

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
4. Like-term merging (`x-x` → `0`)
5. Constant association (`2·(3·x)` → `6·x`)
6. Power simplification (`x^1=x`, `x^0=1`, `x·x=x²`)
7. Division simplification (`x/(-1)=-x`, `x/x=1`)
8. Function evaluation on constants (`sin(0)` → `0`)
9. **Trigonometric identities** (`sin²x+cos²x=1`, `1-sin²x=cos²x`)

## 📊 Supported Functions

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

## 🆕 New Features in v2.0

### Limit Computation
```python
from symbolic_cas import parse
result = parse("sin(x)/x").limit('x', 0)       # → 1.0
result = parse("(exp(x)-1)/x").limit('x', 0)   # → 1.0
result = parse("1/x").limit('x', 'inf')          # → 0.0
```

Supports one-sided limits (`direction='left'` or `'right'`) and limits at infinity.

### JSON Serialization
```python
from symbolic_cas.serialize import to_json, from_json
json_str = to_json(parse("sin(x) + 1"))
expr = from_json(json_str)  # Perfect round-trip
```

### CLI Interface
Full argparse-based command-line interface with actions, variable bindings, and output format control.

### Expression Tree Metrics
```python
expr = parse("x^2 + 2*x + 1")
expr.depth()  # → 4
expr.size()   # → 9
```

### Modular Architecture
Refactored from a single 1877-line file into 10 focused modules for maintainability.

## 📁 Project Structure

```
symbolic-algebra/
├── symbolic_cas/          — Main package
│   ├── __init__.py        — Package exports
│   ├── expr.py            — AST node classes
│   ├── parser.py          — Expression parser
│   ├── calculus.py         — Differentiation & Taylor series
│   ├── simplify.py         — Simplification, expansion, factorization
│   ├── evaluate.py         — Numerical evaluation & integration
│   ├── solve.py            — Equation solving & Newton's method
│   ├── display.py          — Pretty-printing & LaTeX
│   ├── substitute.py       — Substitution & symbol collection
│   ├── limits.py           — Limit computation (NEW)
│   ├── serialize.py        — JSON serialization (NEW)
│   └── cli.py              — CLI interface (NEW)
├── tests/
│   └── test_symbolic.py   — Comprehensive pytest suite
├── examples/
│   ├── basic_usage.py      — Basic usage examples
│   ├── calculus_demo.py    — Calculus examples
│   └── cli_demo.py         — CLI examples
├── symbolic.py             — Original single-file version (legacy)
├── tests.py                — Original test suite (legacy)
├── pyproject.toml          — Package configuration
├── CONTRIBUTING.md         — Contribution guide
├── LICENSE                  — MIT License
└── README.md               — This file
```

## 🧪 Running Tests

```bash
# Run the pytest suite
cd symbolic-algebra
pip install pytest
pytest tests/test_symbolic.py -v

# Run the legacy test suite (still works)
python3 tests.py

# Run with coverage
pip install pytest-cov
pytest tests/test_symbolic.py --cov=symbolic_cas

# Run a specific test class
pytest tests/test_symbolic.py::TestDifferentiation -v
```

## 🐛 Known Issues (Resolved)

1. **`0^0` simplified to `0` instead of `1`** — The `0^x = 0` rule didn't check whether the exponent was positive. Fixed to defer to `x^0 = 1` for the `0^0` case.

2. **`x / (-1)` didn't simplify to `-x`** — Added `x / (-1) → -x` to the division simplification pass.

3. **`_rational_root_candidates` only returned positive integer divisors** — Rewritten to generate all ±(p_i/q_j) candidates per the rational root theorem.

4. **`_collect_polynomial_coeffs` had a dead code branch** — Removed unreachable `isinstance(expr, Sym)` check inside `Pow` handler.

5. **`(-1)^0.5` evaluation returned a Python complex number** — `evaluate()` now raises `ValueError` for complex results.

## 🗺️ Roadmap

- [ ] **Symbolic integration** — Closed-form integration for common patterns
- [ ] **Polynomial GCD** — For more sophisticated simplification
- [ ] **Matrix expressions** — Symbolic matrix operations
- [ ] **Implicit differentiation** — d/dx for implicit functions
- [ ] **Series summation** — Sum symbolic series like Σ(1/n²)
- [ ] **3D pretty-printing** — Unicode art rendering of fractions
- [ ] **Variable-precision arithmetic** — Support for arbitrary precision via `decimal` module
- [ ] **Plotting integration** — Matplotlib-based expression plotting
- [ ] **WebAssembly build** — Run in browser via Pyodide

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Development setup
- Running tests
- Code style requirements
- Adding new features (expression types, functions, simplification rules, CLI commands)

## 📋 Changelog

### v2.0.0 (2026-06-17) — Comprehensive Improvement
- **New**: Modular package architecture (10 modules)
- **New**: Limit computation (`expr.limit()`)
- **New**: JSON serialization (`to_json()`, `from_json()`)
- **New**: CLI interface with argparse (`symbolic-cas` command)
- **New**: Expression tree metrics (`depth()`, `size()`)
- **New**: `pyproject.toml` for pip-installable package
- **New**: Comprehensive pytest test suite
- **New**: GitHub Actions CI configuration
- **New**: Examples directory with 3 demo scripts
- **New**: CONTRIBUTING.md and MIT LICENSE
- **Improved**: Dramatically enhanced README with badges, TOC, and examples
- **Improved**: Type hints on all public functions
- **Improved**: Better error messages throughout

### v1.0.0 (2026-06-17) — Initial Release
- Expression parsing, differentiation, simplification
- Equation solving, Taylor series, numerical integration
- Newton's method, factorization, pretty-printing, LaTeX output
- REPL interface
- 124 tests passing

## 📄 License

This project is licensed under the [MIT License](LICENSE).