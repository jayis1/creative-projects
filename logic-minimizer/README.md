# logic-minimizer — Boolean Logic Minimization Toolkit

A from-scratch boolean logic minimization toolkit implementing the **Quine–McCluskey** exact algorithm, **Petrick's method** for minimum cover selection, an **Espresso-style** heuristic minimizer, **multi-output** minimization with shared implicants, and **multi-level factorization** — all in pure Python with zero dependencies.

## Features

| Algorithm | Description |
|-----------|-------------|
| **Quine–McCluskey** | Exact two-level SOP minimization via the tabular method |
| **Petrick's Method** | Exact minimum-cost cover of the cyclic core (absorption-pruned product-of-sums expansion) |
| **Espresso Heuristic** | Expand → Irredundant → Reduce loop for scalable heuristic minimization |
| **Multi-Output** | Output-tagged prime implicant generation with shared implicant detection |
| **Factorizer** | Greedy algebraic extraction for multi-level factored forms |

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

## Installation

```bash
cd logic-minimizer
pip install -e .
```

Or use directly with `PYTHONPATH=.`.

## Quick Start

```python
from logicmin import QuineMcCluskey, BooleanFunction, Espresso

# F(A,B,C,D) = Σm(4,8,10,11,12,15) + d(9,14)
f = BooleanFunction(n_vars=4, minterms=[4, 8, 10, 11, 12, 15], dontcare=[9, 14])

# Exact minimization
qm = QuineMcCluskey(n_vars=4)
result = qm.minimize(f)
print(result.sop)       # "BC'D' + AD' + AC"
print(result.n_terms)   # 3
print(result.n_literals)# 7

# Heuristic minimization (scales better for many vars)
esp = Espresso(n_vars=4)
result = esp.minimize(f)
print(result.sop)       # "BC'D' + AD' + AC"
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
# Exact minimization
logicmin minimize -n 4 -m "4 8 10 11 12 15 d: 9 14"

# With prime implicant listing
logicmin minimize -n 4 -m "4 8 10 11 12 15 d: 9 14" --show-primes

# JSON output
logicmin minimize -n 4 -m "4 8 10 11 12 15 d: 9 14" --json

# Espresso heuristic
logicmin espresso -n 6 -m "0 1 2 5 6 7 8 9 10 14" --max-iter 100

# Multi-output from PLA file
logicmin multi circuit.pla

# Factorize a SOP expression
logicmin factor "AB'C + AC + BC'"

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
Exact minimizer. `minimize(func)` returns `MinimizationResult` with `.sop`, `.n_terms`, `.n_literals`, `.prime_implicants`, `.essential_implicants`.

### `Espresso(n_vars, max_iter=50, expand_strategy='guarded')`
Heuristic minimizer. Same `minimize(func)` interface.

### `MultiOutputMinimizer(n_vars, use_petrick=True)`
Multi-output minimizer. `minimize(functions)` returns `MultiOutputResult` with `.per_output`, `.shared_implicants`, `.sop`, `.total_literals`.

### `Factorizer(n_vars, max_rounds=20)`
Multi-level factorizer. `factorize(cubes)` or `factorize_sop(sop_string)` returns `FactoredForm` with `.to_string(names)` and `.literal_count()`.

### `PetrickSolver`
Standalone Petrick's method solver. `solve(clauses)` returns minimum-cost covers as lists of frozensets.

## Examples

### 2-bit Adder (multi-output)

```python
from logicmin import MultiOutputMinimizer, BooleanFunction

# Sum and Carry outputs of a 2-bit adder
# A B C_in → Sum Carry
sum_out = BooleanFunction(3, [1,2,4,7], name="sum")    # XOR
carry   = BooleanFunction(3, [3,5,6,7], name="carry")  # majority

mom = MultiOutputMinimizer(3)
result = mom.minimize([sum_out, carry])
print(result.sop)  # ["A'B'C + A'BC' + AB'C' + ABC", "AB + AC + BC"]
```

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
print(qm.minimize(seg_a).sop)  # minimal SOP for segment a
```

## Testing

```bash
pytest tests/ -v
```

## License

MIT