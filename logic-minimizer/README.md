# logicmin — Boolean Logic Minimization Toolkit

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests: 93](https://img.shields.io/badge/tests-93-brightgreen.svg)](tests/)
[![Pure stdlib](https://img.shields.io/badge/pure-stdlib-success.svg)](https://docs.python.org/3/library/)

A from-scratch boolean logic minimization toolkit implementing the **Quine–McCluskey** exact algorithm, **Petrick's method** for minimum cover selection, an **Espresso-style** heuristic minimizer, **Product-of-Sums** minimization via De Morgan duality, **multi-output** minimization with shared implicants, **multi-level factorization**, **ROBDDs** (Reduced Ordered Binary Decision Diagrams), **sensitivity analysis**, **boolean difference** computation, **unate classification**, **PLA format** I/O, **don't-care optimization**, **HTML visualization**, **batch processing**, and **JSON serialization** — all in pure Python with zero dependencies.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Core Algorithms](#core-algorithms)
- [Advanced Features](#advanced-features)
- [CLI Usage](#cli-usage)
- [API Reference](#api-reference)
- [Examples](#examples)
- [Testing](#testing)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [License](#license)

---

## Features

| Algorithm / Feature | Description |
|---------------------|-------------|
| **Quine–McCluskey** | Exact two-level SOP minimization via the tabular method |
| **Petrick's Method** | Exact minimum-cost cover of the cyclic core (absorption-pruned product-of-sums expansion) |
| **Espresso Heuristic** | Expand → Irredundant → Reduce loop for scalable heuristic minimization |
| **POS Minimization** | Product-of-sums form via De Morgan duality on the off-set |
| **Multi-Output** | Output-tagged prime implicant generation with shared implicant detection |
| **Factorizer** | Greedy algebraic extraction for multi-level factored forms |
| **ROBDD** | Reduced Ordered Binary Decision Diagrams with ITE, SAT counting, SOP extraction |
| **Sensitivity Analysis** | Boolean difference, sensitivity metrics, unate/binate classification |
| **Karnaugh Map** | ASCII and HTML K-map rendering with Gray-code ordering (2–5 variables) and cover highlighting |
| **PLA I/O** | Full Berkeley PLA format reader/writer with validation and statistics |
| **Don't-Care Optimization** | Greedy assignment of don't-cares to minimize cover cost |
| **HTML Visualization** | Styled HTML truth tables, K-maps, and full analysis reports |
| **Batch Processing** | Minimize many functions at once with JSON serialization |
| **Benchmark** | QM vs. Espresso vs. POS comparison with timing and literal-cost metrics |
| **Config System** | JSON / TOML / YAML configuration with load/save |
| **Serialization** | JSON import/export for functions and minimization results |
| **Exception Hierarchy** | Structured exceptions for parse, minimization, and Petrick errors |

### Additional Capabilities

- Don't-care (`dc`) handling throughout all algorithms
- Prime implicant chart with essential PI detection
- PLA (Berkeley Espresso) format parser (single & multi-output)
- Truth-table, minterm-list, and SOP-string input formats
- Truth table rendering (ASCII and HTML)
- SOP verification (minimized expression vs. original function)
- Literal cost metric for solution quality comparison
- JSON output mode for CLI integration
- Variable names auto-assigned (A, B, C, …) or custom
- Structured logging (text or JSON format)
- Minterm adjacency graph and Hamming distance matrix

---

## Installation

### From source (recommended)

```bash
cd logic-minimizer
pip install -e .
```

### Direct usage (no install)

```bash
cd logic-minimizer
PYTHONPATH=. python3 -m logicmin.cli minimize -n 4 -m "4 8 10 11 12 15 d: 9 14"
```

### Requirements

- Python ≥ 3.10
- No third-party dependencies (pure stdlib)
- `pytest` for running tests (optional, dev only)

---

## Quick Start

```python
from logicmin import QuineMcCluskey, BooleanFunction, Espresso, POSMinimizer

# F(A,B,C,D) = Σm(4,8,10,11,12,15) + d(9,14)
f = BooleanFunction(n_vars=4, minterms=[4, 8, 10, 11, 12, 15], dontcare=[9, 14])

# Exact SOP minimization
qm = QuineMcCluskey(n_vars=4)
result = qm.minimize(f)
print(result.sop)        # "BC'D' + AD' + AC"
print(result.n_terms)    # 3
print(result.n_literals) # 7

# Heuristic minimization (scales better for many vars)
esp = Espresso(n_vars=4)
result = esp.minimize(f)
print(result.sop)        # "BC'D' + AD' + AC"

# POS minimization (via De Morgan duality on off-set)
pm = POSMinimizer(n_vars=4)
pos = pm.minimize(f)
print(pos.pos)           # "(C + D') · (A + C') · (A + B)"
```

### ROBDD Construction

```python
from logicmin import BDDManager, BooleanFunction

f = BooleanFunction(n_vars=3, minterms=[1, 3, 5, 7])  # f = C
mgr = BDDManager(3)
root = mgr.from_function(f)
print(mgr.node_count(root))        # 1 (very compact!)
print(mgr.count_satisfying(root))  # 4

# Extract SOP from BDD
cubes = mgr.to_sop(root)  # ['--1'] → f = C
```

### Sensitivity Analysis

```python
from logicmin import BooleanFunction, all_sensitivities, unate_profile

f = BooleanFunction(n_vars=4, minterms=[12, 13, 14, 15, 3, 7, 11])  # AB + CD
sens = all_sensitivities(f)
# {0: 0.375, 1: 0.375, 2: 0.375, 3: 0.375} — all variables equally important

profile = unate_profile(f)
# {0: 'positive', 1: 'positive', 2: 'positive', 3: 'positive'} — all positive-unate
```

### Karnaugh Map

```python
from logicmin import KarnaughMap, BooleanFunction, QuineMcCluskey

f = BooleanFunction(n_vars=4, minterms=[4,8,10,11,12,15], dontcare=[9,14])
km = KarnaughMap(f)
print(km.render())
#      A  B |   00    01    11    10
#    --------------------------------
#        00 |   0     0     0     0
#        01 |   1     0     0     0
#        11 |   1     0     1     -
#        10 |   1     -     1     1

# Highlight the minimized cover
qm = QuineMcCluskey(4)
r = qm.minimize(f)
print(km.render_with_coverage(r.sop_cubes))
```

### Multi-Output Minimization

```python
from logicmin import MultiOutputMinimizer, BooleanFunction

# 2-bit adder: Sum and Carry
sum_out = BooleanFunction(3, [1,2,4,7], name="sum")
carry   = BooleanFunction(3, [3,5,6,7], name="carry")

mom = MultiOutputMinimizer(3)
result = mom.minimize([sum_out, carry])
print(result.sop)           # per-output SOP list
print(result.total_literals)
```

### HTML Visualization

```python
from logicmin import BooleanFunction, QuineMcCluskey, full_report_html

f = BooleanFunction(n_vars=4, minterms=[4,8,10,11,12,15], dontcare=[9,14])
qm = QuineMcCluskey(4)
result = qm.minimize(f)
html = full_report_html(f, result)
with open("report.html", "w") as fh:
    fh.write(html)
# Open report.html in a browser for a styled truth table + K-map + prime implicants
```

### Benchmarking

```python
from logicmin import Benchmark

bench = Benchmark(n_vars=4, n_trials=10, seed=42)
results = bench.run()
from logicmin.benchmark import Benchmark as B
print(B.format_results(results))
# Method               Vars  Terms  Lits   Time(ms)
# --------------------------------------------------
# quine-mccluskey         4      3    10       0.09
# espresso                4      3    10       5.80
# pos-dual                4      4     9       0.24
```

---

## Architecture

```
logicmin/
├── boolean.py         # Core: BooleanFunction, TruthTable, Implicant, cube operations
├── quine_mccluskey.py  # Exact QM minimizer (prime implicants + Petrick's method)
├── petrick.py          # Petrick's method (absorption-pruned POS expansion)
├── espresso.py        # Heuristic Espresso (expand → irredundant → reduce loop)
├── multi_output.py     # Multi-output QM with output-tagged shared implicants
├── pos.py             # POS minimization (De Morgan duality on off-set)
├── factorizer.py      # Multi-level algebraic factorization (common divisor extraction)
├── kmap.py            # Karnaugh map ASCII rendering (2–5 variables, Gray code)
├── bdd.py             # ROBDD: ITE, hash-consing, SAT count, SOP extraction, render
├── analysis.py        # Boolean difference, sensitivity, unate classification, adjacency
├── pla.py             # Full PLA reader/writer with validation and statistics
├── dc_optimize.py     # Greedy don't-care assignment optimization
├── htmlviz.py         # HTML visualization (truth tables, K-maps, full reports)
├── batch.py           # Batch processing of multiple functions with JSON export
├── serialize.py       # JSON serialization for functions and results
├── benchmark.py       # QM vs Espresso vs POS benchmarking
├── config.py          # JSON/TOML/YAML configuration system
├── parser.py          # Input format parsers (truth table, minterm, SOP, PLA)
├── exceptions.py      # Custom exception hierarchy
├── logging_config.py  # Structured logging (text or JSON)
└── cli.py             # CLI with 19 subcommands
```

### Design Principles

1. **Pure stdlib** — no third-party dependencies, ever.
2. **Type-hinted** — all public APIs have full type annotations.
3. **Composable** — each module is independent and can be used standalone.
4. **Testable** — 93 tests covering all algorithms and edge cases.
5. **Documented** — every public function/class has a docstring.

---

## Core Algorithms

### Quine–McCluskey Method

The classic exact algorithm for two-level logic minimization:

1. **Prime Implicant Generation**: All minterms (and don't-cares) are grouped by their number of 1-bits. Adjacent groups are compared pairwise — cubes that differ in exactly one position are merged (that position becomes a `-` wildcard). This continues until no more merges are possible. Unmerged cubes are **prime implicants**.

2. **Prime Implicant Chart**: A coverage matrix where rows are prime implicants and columns are on-set minterms. An entry is marked if the prime covers that minterm.

3. **Essential Prime Implicants**: Any minterm covered by exactly one prime makes that prime **essential** — it must be in the final cover.

4. **Cyclic Core (Petrick's Method)**: After removing essentials and their covered minterms, the remaining chart may be cyclic (no more essentials). Petrick's method finds the exact minimum cover by:
   - Writing a product-of-sums constraint: for each remaining minterm, `(P₁ + P₂ + ...)` where `Pᵢ` are primes covering it.
   - Distributing into a sum-of-products: each product term is a valid cover.
   - Applying **absorption** (`A + AB = A`) to prune the expansion.
   - Selecting the minimum-cost solution (fewest primes, then fewest literals).

### Espresso Heuristic

For functions with many variables, the exact QM method is exponential. The Espresso algorithm iterates:

1. **Expand**: Grow each cube to its maximum size without covering any off-set minterm.
2. **Irredundant**: Remove cubes whose minterms are all covered by other cubes.
3. **Reduce**: Shrink each cube to the minimum size that still covers its uniquely-covered minterms, enabling the next expand to find different cube shapes.

The loop continues until no improvement in literal cost is observed.

### ROBDD (Binary Decision Diagrams)

A BDD is a rooted DAG that compactly represents a boolean function. At each internal node, a decision variable is tested; the two outgoing edges (low=0, high=1) lead to child nodes. Terminal nodes are **0** and **1**.

**Key properties:**
- **Reduced**: No two distinct nodes have the same variable and children; no node has identical children.
- **Ordered**: Variables are tested in a fixed order (A first, then B, etc.).
- **Canonical**: Two functions are equivalent iff their ROBDDs are identical (pointer equality).

**ITE (if-then-else)** is the core operation: `ITE(f, g, h) = f·g + f'·h`. All boolean operations (AND, OR, XOR, NOT) are implemented via ITE with memoization.

### POS Minimization

Product-of-sums is minimized by applying QM to the **off-set** (the zeros of the function). The resulting SOP represents the complement of the function; De Morgan's law converts each product term into a sum clause:

```
F' = A'B + CD'   (SOP of off-set)
F  = (A + B') · (C' + D)   (POS via De Morgan)
```

### Multi-Output Minimization

When several functions share inputs, prime implicants are generated with **output tags** — a cube can only merge with another cube if they serve the same set of outputs. This discovers implicants usable by multiple outputs, reducing total literal cost compared to independent minimization.

### Factorization

Given a SOP cover, the factorizer repeatedly finds the **most common divisor** — a set of literals appearing in two or more product terms — and extracts it, producing a nested factored form:

```
AB'C + AC + BC'
→ C(AB' + A + B')    # C is common to all three terms
```

This reduces total literal count at the cost of increasing logic depth.

### Sensitivity Analysis

The **boolean difference** (boolean derivative) of f w.r.t. variable x_i is:

```
∂f/∂x_i = f(x_i=0) ⊕ f(x_i=1)
```

It measures whether the function's output depends on x_i at all. The **sensitivity** is the fraction of input assignments where flipping x_i changes the output. A variable is **unate** (monotone) if the function is either entirely non-decreasing (positive-unate) or non-increasing (negative-unate) in that variable; otherwise it is **binate**.

---

## Advanced Features

### Don't-Care Optimization

After two-level minimization, don't-care minterms can be assigned to either the on-set or off-set to minimize the cover cost. The `assign_dontcares` function tries both assignments (all-to-on, all-to-off, and individual greedy assignment) and picks the best:

```python
from logicmin import BooleanFunction, assign_dontcares

f = BooleanFunction(n_vars=4, minterms=[4, 8, 10, 11, 12, 15], dontcare=[9, 14])
result = assign_dontcares(f, "qm")
print(result.original_cost)   # 7
print(result.optimized_cost)  # ≤ 7
print(result.improvement)     # ≥ 0
```

### PLA Format I/O

Full Berkeley PLA format support with validation:

```python
from logicmin import PLAData, parse_pla_full, write_pla

pla = parse_pla_full(open("circuit.pla").read())
funcs = pla.to_functions()
print(pla.stats())
errors = pla.validate()

# Write functions to PLA
text = write_pla(funcs)
```

### Batch Processing

Minimize many functions at once with automatic verification and JSON export:

```python
from logicmin import BatchProcessor, BooleanFunction

funcs = [
    BooleanFunction(3, [1, 3, 5, 7], name="f1"),
    BooleanFunction(3, [0, 2, 4, 6], name="f2"),
]
bp = BatchProcessor(minimizer="qm")
entries = bp.process_batch(funcs)
for e in entries:
    print(f"{e.name}: {e.sop} ({e.n_literals} lits, {'✓' if e.correct else '✗'})")
```

### JSON Serialization

```python
from logicmin import BooleanFunction, function_to_json, function_from_json

f = BooleanFunction(n_vars=4, minterms=[4, 8, 10, 11], name="test")
json_text = function_to_json(f)
f2 = function_from_json(json_text)
assert set(f2.minterms) == set(f.minterms)
```

---

## CLI Usage

The CLI has **19 subcommands**:

```bash
# Exact SOP minimization
logicmin minimize -n 4 -m "4 8 10 11 12 15 d: 9 14"
logicmin minimize -n 4 -m "4 8 10 11 12 15 d: 9 14" --show-primes --json

# Espresso heuristic
logicmin espresso -n 6 -m "0 1 2 5 6 7 8 9 10 14" --max-iter 100

# POS minimization
logicmin pos -n 4 -m "4 8 10 11 12 15 d: 9 14"

# Karnaugh map
logicmin kmap -n 4 -m "4 8 10 11 12 15 d: 9 14"
logicmin kmap -n 4 -m "4 8 10 11 12 15 d: 9 14" --cover

# BDD construction and analysis
logicmin bdd -n 3 -m "1 3 5 7" --count --render

# Sensitivity analysis
logicmin sensitivity -n 4 -m "12 13 14 15 3 7 11"

# Unate classification
logicmin unate -n 4 -m "12 13 14 15 3 7 11"

# Don't-care optimization
logicmin dc-optimize -n 4 -m "4 8 10 11 12 15 d: 9 14"

# Multi-output from PLA file
logicmin multi circuit.pla

# Batch minimize from PLA
logicmin batch circuit.pla --minimizer qm --json

# Factorize a SOP expression
logicmin factor "AB'C + AC + BC'"

# Benchmark QM vs Espresso
logicmin benchmark -n 4 -t 10 --seed 42

# HTML visualization
logicmin html -n 4 -m "4 8 10 11 12 15 d: 9 14" --mode report -o report.html

# Export to JSON
logicmin export -n 4 -m "4 8 10 11 12 15 d: 9 14" --result

# Configuration
logicmin config                          # show default config
logicmin config --save config.json       # save default config
logicmin config --load config.json       # load and display config

# Show truth table
logicmin truth -n 2 -m "1 2"

# Verify a minimized expression
logicmin verify -n 4 -m "4 8 10 11 12 15 d: 9 14" -s "BC'D' + AD' + AC"

# Show prime implicant chart info
logicmin info -n 4 -m "4 8 10 11 12 15 d: 9 14"

# Version info
logicmin version
```

### Input Formats

**Minterm list** (CLI `--minterms`):
```
4 8 10 11 12 15 d: 9 14
```
The `d:` separator switches to don't-care mode.

**SOP string** (CLI `--sop`):
```
AB'C + AC
```

**Truth table** (CLI `--tt`):
```
0 0 1 -
1 0 1 0
```
Each token is one entry (0, 1, or `-` for don't-care).

**PLA format** (for `multi` and `batch` subcommands):
```
.i 3
.o 2
.ilb A B C
.ob f0 f1
000 10
001 10
010 11
.e
```

---

## API Reference

### Core Classes

| Class | Description |
|-------|-------------|
| `BooleanFunction(n_vars, minterms, dontcare, name)` | Represents a boolean function. Methods: `from_truth_table()`, `from_sop()`, `eval()`, `truth_table()`. |
| `TruthTable(entries, n_vars)` | Truth table with ASCII rendering. |
| `Implicant(cube, minterms)` | A prime implicant with coverage bookkeeping. |

### Minimizers

| Class | Description |
|-------|-------------|
| `QuineMcCluskey(n_vars, use_petrick=True)` | Exact SOP minimizer. `minimize(func)` → `MinimizationResult`. |
| `Espresso(n_vars, max_iter=50, expand_strategy='guarded')` | Heuristic minimizer. Same `minimize(func)` interface. |
| `POSMinimizer(n_vars, use_petrick=True)` | POS minimizer. `minimize(func)` → `POSResult`. |
| `MultiOutputMinimizer(n_vars, use_petrick=True)` | Multi-output minimizer. `minimize(functions)` → `MultiOutputResult`. |
| `Factorizer(n_vars, max_rounds=20)` | Multi-level factorizer. `factorize(cubes)` or `factorize_sop(sop)` → `FactoredForm`. |

### BDD

| Class | Description |
|-------|-------------|
| `BDDManager(n_vars)` | ROBDD manager with ITE, hash-consing, SAT counting. |
| `BDDNode` | A node in the BDD (internal or terminal). |

Methods: `from_function(func)`, `from_sop_cubes(cubes)`, `to_sop(node)`, `count_satisfying(node)`, `node_count(node)`, `negate(f)`, `and_(f, g)`, `or_(f, g)`, `xor(f, g)`, `render_ascii(node)`.

### Analysis

| Function | Description |
|----------|-------------|
| `boolean_difference(func, var)` | Compute ∂f/∂x_var as a new BooleanFunction. |
| `sensitivity(func, var)` | Fraction of inputs where flipping var changes the output. |
| `all_sensitivities(func)` | Sensitivity for every variable. |
| `is_unate(func, var)` | True if func is unate (monotone) in var. |
| `unate_profile(func)` | Classify each variable as positive/negative/binate. |
| `minterm_adjacency(func)` | Pairs of on-set minterms differing by 1 bit. |
| `hamming_distance_matrix(func)` | Pairwise Hamming distances of on-set minterms. |

### Other Modules

| Module | Key Exports |
|--------|-------------|
| `pla` | `PLAData`, `parse_pla_full`, `write_pla` |
| `dc_optimize` | `assign_dontcares`, `minimize_with_dc_optimization`, `DCAssignmentResult` |
| `htmlviz` | `truth_table_html`, `kmap_html`, `kmap_with_cover_html`, `full_report_html` |
| `batch` | `BatchProcessor`, `BatchEntry`, `BatchSummary`, `batch_to_json`, `batch_from_json` |
| `serialize` | `serialize`, `function_to_json`, `function_from_json`, `result_to_json`, `save_function`, `load_function` |
| `benchmark` | `Benchmark`, `BenchmarkResult` |
| `config` | `Config` (JSON/TOML/YAML) |
| `kmap` | `KarnaughMap`, `gray_code` |
| `parser` | `parse_truth_table`, `parse_minterms`, `parse_sop`, `parse_pla` |
| `exceptions` | `LogicMinError`, `ParseError`, `MinimizationError`, `InvalidFunctionError`, `PetrickExpansionError` |

---

## Examples

Five example scripts are included in the `examples/` directory:

| Example | Description |
|---------|-------------|
| `01_basic_minimization.py` | QM minimization with prime implicant display and truth table |
| `02_bdd_analysis.py` | ROBDD construction, SAT counting, SOP extraction, boolean ops |
| `03_sensitivity_analysis.py` | Boolean difference, sensitivity, unate classification, adjacency |
| `04_multi_output_and_pla.py` | Multi-output minimization, PLA I/O, don't-care optimization |
| `05_html_and_batch.py` | HTML report generation, batch processing with JSON export |

Run them:

```bash
cd logic-minimizer
python3 examples/01_basic_minimization.py
python3 examples/02_bdd_analysis.py
python3 examples/03_sensitivity_analysis.py
python3 examples/04_multi_output_and_pla.py
python3 examples/05_html_and_batch.py
```

---

## Testing

```bash
cd logic-minimizer
pytest tests/ -v
```

**93 tests** covering:
- All minimization algorithms (QM, Espresso, POS, multi-output)
- BDD construction, SAT counting, SOP extraction, boolean operations
- Sensitivity analysis, boolean difference, unate classification
- PLA parsing and generation
- Don't-care optimization
- HTML visualization
- Batch processing
- JSON serialization
- CLI subcommands (19 commands tested)
- Edge cases (empty functions, tautologies, single minterms)
- Bug regression tests (5 bugs from the bug-hunt phase)

---

## Known Issues (Resolved)

The following bugs were identified during the bug hunt phase and fixed:

1. **SOP variable inference from letter count instead of position** (`from_sop`): `from_sop("AC")` raised `ValueError: unknown variable 'C'` because n_vars was inferred from the count of distinct letters (2) rather than the highest letter position (C = 3rd variable). Fixed to compute n_vars from `max(ord(c)) - ord('A') + 1`.

2. **`can_merge` silently truncates mismatched-length cubes**: `can_merge("01", "110")` returned `"-1"` instead of `None` because `zip()` truncates to the shorter length. Fixed by adding an explicit length check at the top of the function.

3. **Espresso `_intersects_off` dead code**: The method contained a `for` loop that called `cube_to_minterms(cube)` and did nothing (body was `pass`), wasting allocation on every call. Removed the dead code.

4. **Espresso final cost check was a no-op**: After the final expand+irredundant pass, the code had `best_cover = best_cover` (a self-assignment that does nothing). If the final pass regressed the cost, the better solution from the loop was lost. Fixed by saving the best cover from the loop and restoring it if the final pass worsens the result.

5. **Multi-output import inside nested loop**: `_generate_tagged_primes` imported `can_merge` inside a doubly-nested loop, causing redundant import lookups on every iteration. Fixed by moving the import to the top of the module.

### Bugs Fixed During Improvement Phase

6. **BDD `count_satisfying` skipped variable accounting**: When a BDD node's variable index was higher than the current level, the count did not multiply by `2^(skip_count)` for the skipped variables, producing incorrect counts (e.g., returning 1 instead of 4 for `f = C`). Fixed by multiplying by `2^skip` when recursing through skipped levels.

7. **BDD `negate` infinite recursion**: `negate(f)` called `ite(f, zero, one)`, which recognized the `g=1, h=0` pattern and called `negate(f)` again — infinite loop. Fixed by implementing direct terminal swapping via `_swap_terminals` with memoization.

8. **Boolean difference minterm projection**: `_cofactor` returned `m & ~mask` which only clears the variable's bit but doesn't compress remaining bits into the reduced variable space, causing minterm values to exceed the range for `n_vars - 1` variables. Fixed by properly projecting: splitting the minterm into lower and upper bits around the variable's position and recompressing.

---

## Roadmap

- **Dynamic variable ordering** for BDDs (sifting algorithm)
- **Multi-valued BDDs** (MDDs) for non-binary variables
- **Espresso exact mode** (two-level minimization with exact cover)
- **PLA output to Verilog** (generate RTL from minimized expressions)
- **Interactive K-map editor** (terminal or web)
- **Symbolic model checking** primitives (image computation, fixpoint)
- **Cube calculus** operations (sharp, disjoint sharp, intersection)
- **Cofactor tree** visualization for BDDs
- **Variable ordering heuristics** (fan-in, support-based)
- **Graphviz DOT export** for BDDs and K-maps

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding conventions, and pull request process.

---

## Changelog

### v2.0.0 (2026-08-07) — Comprehensive Improvement

**New modules (7):**
- `bdd.py` — ROBDD with ITE, hash-consing, SAT counting, SOP extraction, ASCII rendering
- `analysis.py` — Boolean difference, sensitivity, unate classification, adjacency analysis
- `pla.py` — Full PLA format reader/writer with validation and statistics
- `dc_optimize.py` — Don't-care assignment optimization
- `htmlviz.py` — HTML visualization (truth tables, K-maps, full reports)
- `batch.py` — Batch processing with JSON serialization
- `serialize.py` — JSON serialization for all result types

**New CLI subcommands (12 added, 19 total):**
- `bdd`, `sensitivity`, `unate`, `dc-optimize`, `batch`, `html`, `export`, `version` + existing 11

**Improvements:**
- Version bumped to 2.0.0
- pyproject.toml updated with full classifiers, keywords, optional deps
- Type hints added to `parse_sop` (fixed `int = None` type annotation)
- `__init__.py` expanded with 30+ new exports
- 59 new tests added (93 total, all passing)
- 5 example scripts added
- CONTRIBUTING.md and LICENSE added
- GitHub Actions CI added (Python 3.10–3.13)
- 3 bugs fixed during improvement (BDD count, BDD negate recursion, boolean difference projection)

### v1.0.0 — Initial Release

- Quine–McCluskey, Petrick's method, Espresso, POS, multi-output, factorizer
- K-map rendering, benchmark, config system, CLI (7 subcommands)
- PLA parser, truth-table/SOP/minterm inputs
- 34 tests, 5 bugs fixed

---

## License

MIT