# SMT Solver

A DPLL(T)-based Satisfiability Modulo Theories (SMT) solver implemented from scratch in pure Python.

## Overview

This solver implements the **DPLL(T)** architecture, which combines a CDCL (Conflict-Driven Clause Learning) SAT solver with theory-specific decision procedures:

- **SAT Engine**: CDCL with watched literals, VSIDS branching, 1-UIP conflict analysis, non-chronological backtracking, and Luby restarts.
- **EUF Theory**: Uninterpreted Functions with Equality — uses union-find based **congruence closure** to reason about equalities and disequalities involving function symbols.
- **LRA Theory**: Linear Real Arithmetic — uses **Fourier-Motzkin elimination** for feasibility checking with back-substitution for model generation.
- **Theory Combination**: Equality atoms are shared between theories for cross-theory reasoning (e.g., `a = b` in LRA enables `f(a) = f(b)` in EUF via congruence).

## How It Works

### DPLL(T) Loop

```
1. Abstract theory atoms as propositional variables
2. Encode Boolean structure into CNF (Tseitin transformation)
3. SAT solver finds a satisfying Boolean assignment
4. Theory solvers check if the assignment is theory-consistent
5. If inconsistent: learn a theory lemma (conflict clause), backtrack, repeat
6. If consistent: return SAT with a theory model
```

### SMT-LIB Parser

Supports a subset of SMT-LIB v2:
- `declare-const`, `declare-fun`
- `assert`, `check-sat`, `get-model`
- Boolean connectives: `and`, `or`, `not`, `=>`, `=`, `xor`, `distinct`, `ite`
- Arithmetic: `+`, `-`, `*`, `/`, `<`, `<=`, `>`, `>=`
- `let` bindings
- `push`/`pop`/`reset` for incremental solving

## Installation

```bash
pip install -e .
```

## Usage

### Command Line

```bash
# Check an SMT-LIB file
smt-solver examples/01_lra_sat.smt2 --model

# Check expected result
smt-solver examples/02_lra_unsat.smt2 --check unsat
```

### Python API

```python
from smt_solver import Solver

s = Solver()
s.parse_and_assert("(declare-const x Real)")
s.parse_and_assert("(assert (> x 5.0))")
s.parse_and_assert("(assert (< x 10.0))")
result = s.check()
print(result)  # "sat"

model = s.get_model()
print(model)  # x -> 8.0
```

### Building Terms Programmatically

```python
from smt_solver import Solver, Var, NumConst, Gt, Lt, REAL

s = Solver()
x = s.declare_const("x", REAL)
s.assert_term(Gt(x, NumConst(5.0)))
s.assert_term(Lt(x, NumConst(10.0)))
print(s.check())  # "sat"
```

## Examples

See the `examples/` directory for SMT-LIB input files:

| File | Description | Expected |
|------|-------------|----------|
| `01_lra_sat.smt2` | Linear arithmetic, satisfiable | sat |
| `02_lra_unsat.smt2` | Linear arithmetic, unsatisfiable | unsat |
| `03_euf_unsat.smt2` | Uninterpreted functions, unsatisfiable | unsat |

## Architecture

```
smt_solver/
├── __init__.py       # Public API
├── __main__.py       # CLI entry point
├── ast.py            # Term/Sort/Formula AST nodes
├── exceptions.py     # Error hierarchy
├── parser.py         # SMT-LIB v2 parser (S-expressions → AST)
├── sat_solver.py     # CDCL SAT solver (watched literals, VSIDS, 1-UIP)
├── solver.py         # DPLL(T) integration, CNF encoding, model generation
├── theory_euf.py     # EUF: congruence closure (union-find)
└── theory_lra.py     # LRA: Fourier-Motzkin elimination
```

## Limitations

- Quantifiers (forall/exists) are not supported
- Nonlinear arithmetic is not supported (multiplication of two variables)
- Arrays, bit-vectors, and other theories are not supported
- The Fourier-Motzkin approach has exponential worst-case complexity
- No incremental push/pop across check() calls (declarations persist)

## License

MIT