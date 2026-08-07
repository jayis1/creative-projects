# logic-minimizer — Boolean Logic Minimization Toolkit

A from-scratch boolean logic minimization toolkit implementing the **Quine–McCluskey** exact algorithm, **Petrick's method** for minimum cover selection, an **Espresso-style** heuristic minimizer, **Product-of-Sums** minimization via De Morgan duality, **multi-output** minimization with shared implicants, **multi-level factorization**, **Karnaugh map** rendering, and **benchmarking** — all in pure Python with zero dependencies.

## Features

| Algorithm / Feature | Description |
|---------------------|-------------|
| **Quine–McCluskey** | Exact two-level SOP minimization via the tabular method |
| **Petrick's Method** | Exact minimum-cost cover of the cyclic core (absorption-pruned product-of-sums expansion) |
| **Espresso Heuristic** | Expand → Irredundant → Reduce loop for scalable heuristic minimization |
| **POS Minimization** | Product-of-sums form via De Morgan duality on the off-set |
| **Multi-Output** | Output-tagged prime implicant generation with shared implicant detection |
| **Factorizer** | Greedy algebraic extraction for multi-level factored forms |
| **Karnaugh Map** | ASCII K-map rendering with Gray-code ordering (2–5 variables) and cover highlighting |
| **Benchmark** | QM vs. Espresso comparison with timing and literal-cost metrics |
| **Config System** | JSON / TOML / YAML configuration with load/save |
| **Exception Hierarchy** | Structured exceptions for parse, minimization, and Petrick errors |

### Additional capabilities

- Don't-care (`dc`) handling throughout all algorithms
- Prime implicant chart with essential PI detection
- PLA (Berkeley Espresso) format parser (single & multi-output)
- Truth-table, minterm-list, and SOP-string input formats
- Truth table rendering (ASCII)
- SOP verification (minimized expression vs. original function)
- Literal cost metric for solution quality comparison
- JSON output mode for CLI integration
- Variable names auto-assigned (A, B, C, …) or custom
- Structured logging (text or JSON format)
- Custom exception hierarchy (`LogicMinError` → `ParseError`, `MinimizationError`, etc.)

## Installation

```bash
cd logic-minimizer
pip install -e .
```

Or use directly with `PYTHONPATH=.`.

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

## How It Works

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

## CLI Usage

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

# Multi-output from PLA file
logicmin multi circuit.pla

# Factorize a SOP expression
logicmin factor "AB'C + AC + BC'"

# Benchmark QM vs Espresso
logicmin benchmark -n 4 -t 10 --seed 42

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

**PLA format** (for `multi` subcommand):
```
.i 3
.o 2
.ilb A B C
.ob f0 f1
000 10
001 10
010 11
...
.e
```

## API Reference

### `BooleanFunction(n_vars, minterms, dontcare, name)`
Represents a boolean function. Methods: `from_truth_table()`, `from_sop()`, `eval()`, `truth_table()`.

### `QuineMcCluskey(n_vars, use_petrick=True)`
Exact SOP minimizer. `minimize(func)` → `MinimizationResult` with `.sop`, `.n_terms`, `.n_literals`, `.prime_implicants`, `.essential_implicants`.

### `Espresso(n_vars, max_iter=50, expand_strategy='guarded')`
Heuristic minimizer. Same `minimize(func)` interface.

### `POSMinimizer(n_vars, use_petrick=True)`
POS minimizer. `minimize(func)` → `POSResult` with `.pos`, `.n_clauses`, `.n_literals`, `.dual_sop`.

### `MultiOutputMinimizer(n_vars, use_petrick=True)`
Multi-output minimizer. `minimize(functions)` → `MultiOutputResult` with `.per_output`, `.shared_implicants`, `.sop`, `.total_literals`.

### `KarnaughMap(func)`
K-map renderer. `render()` for plain, `render_with_coverage(cubes)` for highlighted cover.

### `Factorizer(n_vars, max_rounds=20)`
Multi-level factorizer. `factorize(cubes)` or `factorize_sop(sop_string)` → `FactoredForm`.

### `Benchmark(n_vars, n_trials, seed)`
Benchmark runner. `run()` → `List[BenchmarkResult]`. `run_trials()` for multiple random functions.

### `Config`
Configuration dataclass. `from_file(path)`, `save(path)`, `to_json()`, `to_dict()`. Supports JSON/TOML/YAML.

### `PetrickSolver`
Standalone Petrick's method solver. `solve(clauses)` returns minimum-cost covers.

### Exceptions
`LogicMinError` (base) → `ParseError`, `MinimizationError`, `InvalidFunctionError`, `PetrickExpansionError`.

## Examples

### 7-segment decoder (multi-output with don't-cares)

```python
from logicmin import QuineMcCluskey, BooleanFunction

# Segment 'a' of a BCD→7-segment decoder (digits 0-9, 10-15 are don't-care)
seg_a = BooleanFunction(
    n_vars=4,
    minterms=[0, 2, 3, 5, 6, 7, 8, 9],
    dontcare=[10, 11, 12, 13, 14, 15],
    name="seg_a",
)
qm = QuineMcCluskey(4)
print(qm.minimize(seg_a).sop)
```

### Configuration

```python
from logicmin import Config

cfg = Config(minimizer="espresso", n_vars=6, espresso_max_iter=100)
cfg.save("my_config.json")

cfg2 = Config.from_file("my_config.json")
print(cfg2.minimizer)  # "espresso"
```

## Testing

```bash
pytest tests/ -v
```

## Known Issues (Resolved)

The following bugs were identified during the bug hunt phase and fixed:

1. **SOP variable inference from letter count instead of position** (`from_sop`): `from_sop("AC")` raised `ValueError: unknown variable 'C'` because n_vars was inferred from the count of distinct letters (2) rather than the highest letter position (C = 3rd variable). Fixed to compute n_vars from `max(ord(c)) - ord('A') + 1`.

2. **`can_merge` silently truncates mismatched-length cubes**: `can_merge("01", "110")` returned `"-1"` instead of `None` because `zip()` truncates to the shorter length. Fixed by adding an explicit length check at the top of the function.

3. **Espresso `_intersects_off` dead code**: The method contained a `for` loop that called `cube_to_minterms(cube)` and did nothing (body was `pass`), wasting allocation on every call. Removed the dead code.

4. **Espresso final cost check was a no-op**: After the final expand+irredundant pass, the code had `best_cover = best_cover` (a self-assignment that does nothing). If the final pass regressed the cost, the better solution from the loop was lost. Fixed by saving the best cover from the loop and restoring it if the final pass worsens the result.

5. **Multi-output import inside nested loop**: `_generate_tagged_primes` imported `can_merge` inside a doubly-nested loop, causing redundant import lookups on every iteration. Fixed by moving the import to the top of the module.

## License

MIT