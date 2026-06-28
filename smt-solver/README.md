# SMT Solver

![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Tests: 73](https://img.shields.io/badge/tests-73-brightgreen)
![Version: 2.0](https://img.shields.io/badge/version-2.0-orange)

A **DPLL(T)-based Satisfiability Modulo Theories (SMT) solver** implemented from scratch in pure Python — no external dependencies required.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
  - [Command Line](#command-line)
  - [Python API](#python-api)
  - [Building Terms Programmatically](#building-terms-programmatically)
- [Architecture](#architecture)
- [Examples](#examples)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [License](#license)

## Overview

This solver implements the **DPLL(T)** architecture, which combines a CDCL (Conflict-Driven Clause Learning) SAT solver with theory-specific decision procedures:

- **SAT Engine**: CDCL with watched literals, VSIDS branching, 1-UIP conflict analysis, non-chronological backtracking, and Luby restarts.
- **EUF Theory**: Uninterpreted Functions with Equality — uses union-find based **congruence closure** to reason about equalities and disequalities involving function symbols.
- **LRA Theory**: Linear Real Arithmetic — uses **Fourier-Motzkin elimination** with back-substitution for feasibility checking and model generation.
- **String Theory**: Basic support for string operations (str.len, str.++, str.contains, str.prefixof, etc.).
- **BitVector Theory**: Basic data structures for fixed-width bit-vectors.
- **Theory Combination**: Equality atoms are shared between theories for cross-theory reasoning.
- **ITE Expansion**: If-then-else terms inside theory atoms are automatically expanded into Boolean case splits for correct model generation.

## Features

### Core Solver
- ✅ CDCL SAT engine with watched literals, VSIDS, 1-UIP, Luby restarts
- ✅ Tseitin CNF encoding for all Boolean connectives
- ✅ DPLL(T) loop with theory lemma learning
- ✅ Theory combination (EUF + LRA shared equalities)
- ✅ Model generation with theory-aware assignments
- ✅ Named assertions and basic UNSAT core extraction
- ✅ Incremental push/pop solving
- ✅ Solver statistics tracking (time, conflicts, rounds, atoms, clauses)

### Theories
- ✅ **EUF** — Congruence closure via union-find
- ✅ **LRA** — Fourier-Motzkin elimination with recursive disequality branching
- ✅ **Strings** — 10 string operations with model-based evaluation
- ✅ **BitVectors** — Basic data structures (arithmetic, bitwise, shifts, comparisons)

### Parser
- ✅ SMT-LIB v2 subset parser (S-expressions → AST)
- ✅ `declare-const`, `declare-fun`, `assert`, `check-sat`, `get-model`
- ✅ Boolean connectives: `and`, `or`, `not`, `=>`, `=`, `xor`, `distinct`, `ite`
- ✅ Arithmetic: `+`, `-`, `*`, `/`, `<`, `<=`, `>`, `>=`
- ✅ `let` bindings (including nested)
- ✅ `push`/`pop`/`reset` for incremental solving
- ✅ Named assertions: `(assert (! formula :named label))`
- ✅ String literals and string operations
- ✅ Comments (`;`)

### CLI
- ✅ `--model` — Print model when sat
- ✅ `--stats` — Print solver statistics
- ✅ `--check EXPECT` — Verify expected result
- ✅ `--logic LOGIC` — Set SMT logic
- ✅ `--config FILE` — Load JSON configuration
- ✅ `--batch DIR` — Run all .smt2 files in a directory
- ✅ `--expr EXPR` — Quick single-expression check
- ✅ `--verbose` — Debug logging

## Installation

```bash
# From the project directory
pip install -e .

# With test dependencies
pip install -e ".[test]"
```

## Usage

### Command Line

```bash
# Check an SMT-LIB file
smt-solver examples/01_lra_sat.smt2

# Print model when satisfiable
smt-solver examples/01_lra_sat.smt2 --model

# Print solver statistics
smt-solver examples/01_lra_sat.smt2 --stats

# Check expected result (exits 1 on mismatch)
smt-solver examples/02_lra_unsat.smt2 --check unsat

# Run all examples in a directory
smt-solver --batch examples/

# Quick expression check
smt-solver --expr '(> x 5.0)' --check sat

# Read from stdin
echo '(declare-const x Real) (assert (> x 0.0))' | smt-solver
```

### Python API

```python
from smt_solver import Solver

s = Solver()
s.parse_and_assert('(declare-const x Real)')
s.parse_and_assert('(assert (> x 5.0))')
s.parse_and_assert('(assert (< x 10.0))')
result = s.check()
print(result)  # "sat"

model = s.get_model()
print(model)  # x -> 8.0

# Get statistics
stats = s.get_statistics()
print(stats)
# Assertions:       2
# Theory atoms:     2
# ...
```

### Building Terms Programmatically

```python
from smt_solver import Solver, Var, NumConst, Gt, Lt, And, REAL

s = Solver()
x = s.declare_const('x', REAL)
s.assert_term(And(Gt(x, NumConst(5.0)), Lt(x, NumConst(10.0))))
print(s.check())  # "sat"
```

### Evaluate Terms Under a Model

```python
from smt_solver import Solver, Var, Add, REAL

s = Solver()
s.parse_and_assert('(declare-const x Real)')
s.parse_and_assert('(declare-const y Real)')
s.parse_and_assert('(assert (= x 3.0))')
s.parse_and_assert('(assert (= y 4.0))')
s.check()

val = s.evaluate(Add(Var('x', REAL), Var('y', REAL)))
print(val)  # 7.0
```

## Architecture

```
smt_solver/
├── __init__.py         # Public API exports
├── __main__.py         # CLI entry point (argparse, batch, config)
├── ast.py             # Term/Sort/Formula AST nodes, operators, helpers
├── exceptions.py       # Error hierarchy (SMTError, ParseError, TheoryError, ...)
├── parser.py          # SMT-LIB v2 parser (S-expressions → AST)
├── sat_solver.py       # CDCL SAT solver (watched literals, VSIDS, 1-UIP)
├── solver.py          # DPLL(T) integration, CNF encoding, model generation
├── theory_euf.py      # EUF: congruence closure (union-find)
├── theory_lra.py      # LRA: Fourier-Motzkin elimination with back-substitution
├── theory_strings.py   # String theory: basic string operation evaluation
└── theory_bv.py       # BitVector theory: data structures for fixed-width BVs
```

### DPLL(T) Loop

```
1. Abstract theory atoms as propositional variables
2. Encode Boolean structure into CNF (Tseitin transformation)
3. SAT solver finds a satisfying Boolean assignment
4. Theory solvers check if the assignment is theory-consistent
5. If inconsistent: learn a theory lemma (conflict clause), backtrack, repeat
6. If consistent: return SAT with a theory model
```

### ITE Expansion

When an ITE term appears inside a theory atom (e.g., `(= y (ite b 1.0 2.0))`),
the solver automatically expands it into a Boolean case split:

```
(= y (ite b 1.0 2.0))  →  (or (and b (= y 1.0)) (and (not b) (= y 2.0)))
```

This ensures that the theory solver sees individual atoms (`= y 1.0`, `= y 2.0`)
rather than an opaque ITE, enabling correct model generation.

## Examples

See the `examples/` directory for SMT-LIB input files:

| File | Description | Expected |
|------|-------------|----------|
| `01_lra_sat.smt2` | Linear arithmetic, satisfiable | sat |
| `02_lra_unsat.smt2` | Linear arithmetic, unsatisfiable | unsat |
| `03_euf_unsat.smt2` | Uninterpreted functions, unsatisfiable | unsat |
| `04_bool_implies.smt2` | Boolean implication chain, unsatisfiable | unsat |
| `05_ite_arith.smt2` | ITE in arithmetic context | sat |
| `06_distinct.smt2` | Distinct variables with bounds | sat |
| `07_multi_var.smt2` | Multi-variable LRA with constraints | sat |
| `08_strings.smt2` | String operations | sat |
| `09_euf_complex.smt2` | Complex EUF with multiple functions | sat |
| `10_push_pop.smt2` | Incremental push/pop solving | sat |
| `11_xor_eq.smt2` | XOR with Boolean equality | sat |
| `12_theory_combination.smt2` | EUF + LRA theory combination | sat |
| `13_named_assert.smt2` | Named assertions for UNSAT core | unsat |

## Known Issues (Resolved)

### v2.0.0 Fixes

1. **Boolean variable model bug** — Boolean variables (e.g., `(declare-const b Bool) (assert b)`)
   were always reported as `false` in the model. **Fix**: Track Boolean variable → SAT literal
   mappings in `_bool_var_to_lit` during Tseitin encoding, and use this mapping for model construction.

2. **ITE in arithmetic context** — `(= y (ite b 1.0 2.0))` with `(assert b)` produced
   `y -> 0.0` instead of `y -> 1.0`. **Fix**: Added ITE expansion pre-processing that
   transforms ITE-in-atom into Boolean case splits before CNF encoding.

3. **LRA disequality branching bug** — Three or more disequalities between unconstrained
   variables were incorrectly reported as `unsat`. **Fix**: Replaced single-level branching
   with recursive disequality branching that properly handles multiple disequalities.

4. **Boolean equality treated as theory atom** — `(= a b)` where both `a` and `b` are
   Bool-sorted was treated as a theory atom (sent to EUF) instead of being handled by
   the Tseitin encoding. **Fix**: Updated `is_atom()` to exclude Boolean equalities.

5. **SAT solver cancel_until reset** — After theory lemma learning, `cancel_until(0)` didn't
   fully reset the `_propagated` pointer, causing the SAT solver to return stale assignments
   on re-solve. **Fix**: Always set `_propagated = len(self.trail)` after backtracking.

## Roadmap

- [ ] Full Simplex method for LRA (replacing Fourier-Motzkin for better scalability)
- [ ] Theory propagation (send implied atoms back to SAT solver)
- [ ] Full string constraint solving (word equations, regex constraints)
- [ ] Bit-vector theory solver integration
- [ ] Quantifier support (forall/exists via instantiation)
- [ ] Parallel theory checking
- [ ] Proof generation ( UNSAT proofs)
- [ ] SMT-LIB v2.6 full compliance
- [ ] Non-linear arithmetic (Nielsen-Schonherr or NLSAT)
- [ ] Array theory
- [ ] Datatypes and enumerations

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run the test suite (`python3 -m pytest tests/ -v`)
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

### Development Setup

```bash
git clone https://github.com/jayis1/creative-projects
cd creative-projects/smt-solver
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
python3 -m pytest tests/ -v
```

### Adding a New Theory

1. Create a new module `theory_<name>.py` with a theory class
2. Implement `assert_atom()`, `assert_negation()`, `check()` methods
3. Add theory detection in `solver.py` (`_is_<name>_atom()`)
4. Add routing in `_check_theory()`
5. Add tests in `tests/test_solver.py`

## Changelog

### v2.0.0 — 2026-06-28

**Major improvements:**
- Added String theory (`theory_strings.py`) with 10 string operations
- Added BitVector theory data structures (`theory_bv.py`)
- Added solver statistics tracking (`SolverStatistics`)
- Added ITE expansion pre-processing for correct arithmetic models
- Added named assertions support (`(assert (! formula :named label))`)
- Added basic UNSAT core extraction
- Added `evaluate()` method for term evaluation under a model
- Added `--stats`, `--logic`, `--config`, `--batch` CLI options
- Added comprehensive test suite (73 tests)
- Added 10 new example files (13 total)
- Added `StrConst` AST node for string constants
- Added `STRING` sort
- Added proper push/pop with assertion stack tracking
- Added type hints throughout
- Added structured logging

**Bug fixes:**
- Fixed Boolean variable model generation (was always `false`)
- Fixed ITE in arithmetic context producing wrong models
- Fixed LRA disequality branching with 3+ disequalities
- Fixed Boolean equality treated as theory atom instead of connective
- Fixed SAT solver `cancel_until(0)` not resetting `_propagated`

### v1.0.0 — 2026-06-28

- Initial release with CDCL SAT, EUF, LRA, DPLL(T) integration
- SMT-LIB v2 parser
- CLI interface
- 3 example files

## License

MIT