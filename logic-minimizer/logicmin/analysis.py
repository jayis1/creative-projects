"""
Sensitivity analysis and boolean difference computation.

The *boolean difference* (or boolean derivative) of f with respect to variable
x_i is:

    ∂f/∂x_i = f(x_i=0) ⊕ f(x_i=1)

It measures whether the function's output depends on x_i at all.  This module
provides:

* ``boolean_difference(func, var)`` — compute ∂f/∂x_i as a new BooleanFunction.
* ``sensitivity(func, var)`` — fraction of inputs where flipping x_i changes
  the output (a scalar in [0, 1]).
* ``all_sensitivities(func)`` — sensitivity for every variable.
* ``is_unate(func, var)`` — check if f is unate (monotone) in variable x_i
  (positive-unate or negative-unate).
* ``unate_profile(func)`` — classify each variable as positive-unate,
  negative-unate, or binate.
* ``on_set_size(func)`` / ``off_set_size(func)`` — cardinality helpers.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from .boolean import BooleanFunction


def _cofactor(func: BooleanFunction, var: int, value: int) -> set:
    """Return the set of projected minterms where x_var = value.

    The minterms are projected to n_vars-1 dimensions by removing the bit
    for ``var`` and compressing the remaining bits.
    """
    n = func.n_vars
    mask = 1 << (n - 1 - var)
    high_bits_mask = (1 << (n - 1 - var)) - 1  # bits below var's position
    result: set = set()
    for m in func.all_minterms:
        if (m & mask) != 0:
            if value == 1:
                # Project: remove bit at var's position, compress
                lower = m & high_bits_mask
                upper = (m >> (n - var)) << (n - 1 - var)
                result.add(upper | lower)
        else:
            if value == 0:
                lower = m & high_bits_mask
                upper = (m >> (n - var)) << (n - 1 - var)
                result.add(upper | lower)
    return result


def boolean_difference(func: BooleanFunction, var: int) -> BooleanFunction:
    """Compute the boolean difference ∂f/∂x_var.

    Returns a new :class:`BooleanFunction` with one fewer variable (var is
    projected out).  The result is 1 exactly where f depends on var.

    Raises ``ValueError`` if ``var`` is out of range or ``func`` has only 1
    variable (the result would have 0 variables).
    """
    if not 0 <= var < func.n_vars:
        raise ValueError(f"var {var} out of range for {func.n_vars} vars")
    if func.n_vars <= 1:
        raise ValueError("boolean difference requires at least 2 variables")
    f0 = _cofactor(func, var, 0)  # minterms with var=0, projected
    f1 = _cofactor(func, var, 1)  # minterms with var=1, projected
    # XOR: symmetric difference
    diff = f0.symmetric_difference(f1)
    # Don't-cares: XOR of dc cofactors (projected)
    dc_func = BooleanFunction(
        n_vars=func.n_vars, minterms=set(), dontcare=func.dontcare, name="dc"
    )
    dc0 = _cofactor(dc_func, var, 0)
    dc1 = _cofactor(dc_func, var, 1)
    diff_dc = dc0.symmetric_difference(dc1)
    # Remove overlap between diff and diff_dc
    diff -= diff_dc
    return BooleanFunction(
        n_vars=func.n_vars - 1, minterms=diff, dontcare=diff_dc, name=f"df/dx{var}"
    )


def sensitivity(func: BooleanFunction, var: int) -> float:
    """Compute the sensitivity of f to variable x_var.

    Sensitivity is the fraction of input assignments where flipping x_var
    changes f's output (ignoring don't-cares).

    Returns a float in [0, 1].
    """
    if not 0 <= var < func.n_vars:
        raise ValueError(f"var {var} out of range for {func.n_vars} vars")
    n = func.n_vars
    mask = 1 << (n - 1 - var)
    count = 0
    total = 0
    for m in range(1 << n):
        if m in func.dontcare or (m ^ mask) in func.dontcare:
            continue
        val_m = 1 if m in func.minterms else 0
        val_flip = 1 if (m ^ mask) in func.minterms else 0
        if val_m != val_flip:
            count += 1
        total += 1
    return count / total if total > 0 else 0.0


def all_sensitivities(func: BooleanFunction) -> Dict[int, float]:
    """Return sensitivity for every variable: {var_index: sensitivity_value}."""
    return {i: sensitivity(func, i) for i in range(func.n_vars)}


def _cofactor_raw(func: BooleanFunction, var: int, value: int) -> set:
    """Return the set of projected minterms where x_var = value.

    Used by is_unate/unate_profile.  Projects the minterm by removing
    var's bit so that cofactor comparison is meaningful.
    """
    return _cofactor(func, var, value)


def is_unate(func: BooleanFunction, var: int) -> bool:
    """Check if f is unate (monotone) in variable x_var.

    A function is *positive unate* in x_i if f(x_i=1) ⊇ f(x_i=0) (cofactor
    containment).  It is *negative unate* if f(x_i=0) ⊇ f(x_i=1).

    Returns True if either condition holds (the function is unate in var,
    either positive or negative).  Returns False if the function is *binate*
    (neither monotone direction).

    Don't-cares are ignored for this check.
    """
    if not 0 <= var < func.n_vars:
        raise ValueError(f"var {var} out of range for {func.n_vars} vars")
    f0 = _cofactor_raw(func, var, 0)
    f1 = _cofactor_raw(func, var, 1)
    # Positive unate: f1 ⊇ f0  →  f0 - f1 is empty
    pos = f0 - f1
    if not pos:
        return True
    # Negative unate: f0 ⊇ f1  →  f1 - f0 is empty
    neg = f1 - f0
    if not neg:
        return True
    return False


def unate_profile(func: BooleanFunction) -> Dict[int, str]:
    """Classify each variable as 'positive', 'negative', or 'binate'.

    Returns a dict mapping variable index → unate classification.
    """
    result: Dict[int, str] = {}
    for var in range(func.n_vars):
        f0 = _cofactor_raw(func, var, 0)
        f1 = _cofactor_raw(func, var, 1)
        if not (f0 - f1):
            result[var] = "positive"
        elif not (f1 - f0):
            result[var] = "negative"
        else:
            result[var] = "binate"
    return result


def on_set_size(func: BooleanFunction) -> int:
    """Number of on-set minterms (excluding don't-cares)."""
    return len(func.minterms)


def off_set_size(func: BooleanFunction) -> int:
    """Number of off-set minterms (excluding don't-cares)."""
    universe = set(range(1 << func.n_vars))
    return len(universe - func.minterms - func.dontcare)


def hamming_distance_matrix(func: BooleanFunction) -> List[List[int]]:
    """Return a matrix where entry [i][j] is the Hamming distance between
    minterm i and minterm j in the on-set.

    Useful for understanding the adjacency structure of the function.
    """
    mins = sorted(func.minterms)
    n = len(mins)
    matrix: List[List[int]] = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = bin(mins[i] ^ mins[j]).count("1")
            matrix[i][j] = d
            matrix[j][i] = d
    return matrix


def minterm_adjacency(func: BooleanFunction) -> List[Tuple[int, int]]:
    """Return pairs of on-set minterms that are Hamming-adjacent (differ by 1 bit).

    These are the edges of the *minterm hypercube graph* restricted to the
    on-set.
    """
    mins = sorted(func.minterms)
    edges: List[Tuple[int, int]] = []
    for i in range(len(mins)):
        for j in range(i + 1, len(mins)):
            if bin(mins[i] ^ mins[j]).count("1") == 1:
                edges.append((mins[i], mins[j]))
    return edges