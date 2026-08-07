"""
Quine–McCluskey exact two-level minimizer.

Algorithm
---------
1. **Prime implicant generation** — group minterms by number of 1-bits, then
   repeatedly merge adjacent groups whose cubes differ in exactly one
   position.  Unmerged cubes are prime implicants.
2. **Cyclic cover** — build the prime implicant chart, extract essential
   PIs, then solve the remaining cyclic core with Petrick's method
   (see :mod:`logicmin.petrick`) to obtain a *minimum* cover.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Set, Tuple

from .boolean import (
    BooleanFunction,
    Implicant,
    can_merge,
    cube_to_minterms,
    minterm_to_cube,
    var_names,
)
from .petrick import PetrickSolver


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class MinimizationResult:
    """Result of a minimization run."""

    prime_implicants: List[Implicant]
    essential_implicants: List[Implicant]
    chosen_implicants: List[Implicant]
    sop: str
    sop_cubes: List[str]
    n_literals: int
    n_terms: int
    minterms_covered: List[int]
    function: BooleanFunction
    method: str = "quine-mccluskey"
    iterations: int = 0

    def __repr__(self) -> str:
        return (
            f"MinimizationResult(sop={self.sop!r}, "
            f"n_terms={self.n_terms}, n_literals={self.n_literals}, "
            f"method={self.method})"
        )

    @property
    def cost(self) -> int:
        """Literal cost (sum of literals across product terms)."""
        return self.n_literals


# ---------------------------------------------------------------------------
# Quine–McCluskey
# ---------------------------------------------------------------------------

class QuineMcCluskey:
    """Exact two-level SOP minimizer.

    Parameters
    ----------
    n_vars : int
        Number of input variables.
    use_petrick : bool
        If True (default) use Petrick's method for the cyclic core; otherwise
        use a greedy cover heuristic (faster but not guaranteed minimal).
    """

    def __init__(self, n_vars: int, use_petrick: bool = True) -> None:
        if n_vars <= 0:
            raise ValueError("n_vars must be positive")
        if n_vars > 32:
            raise ValueError("n_vars > 32 not supported (memory)")
        self.n_vars = n_vars
        self.use_petrick = use_petrick

    # -- public API ---------------------------------------------------------

    def minimize(self, func: BooleanFunction) -> MinimizationResult:
        """Minimize ``func`` and return a :class:`MinimizationResult`."""
        if func.n_vars != self.n_vars:
            raise ValueError(
                f"function has {func.n_vars} vars, minimizer expects {self.n_vars}"
            )
        primes, iters = self._generate_primes(func)
        chosen, essentials = self._select_cover(primes, func)
        chosen.sort()
        sop_cubes = [imp.cube for imp in chosen]
        sop_str = self._format_sop(chosen, func.var_names)
        covered = sorted({m for imp in chosen for m in imp.minterms if m in func.minterms})
        n_literals = sum(imp.n_literals for imp in chosen)
        return MinimizationResult(
            prime_implicants=sorted(primes),
            essential_implicants=sorted(essentials),
            chosen_implicants=chosen,
            sop=sop_str,
            sop_cubes=sop_cubes,
            n_literals=n_literals,
            n_terms=len(chosen),
            minterms_covered=covered,
            function=func,
            iterations=iters,
        )

    # -- step 1: prime implicant generation ---------------------------------

    def _generate_primes(self, func: BooleanFunction) -> Tuple[List[Implicant], int]:
        """Generate all prime implicants via the tabular method."""
        all_mins = func.all_minterms
        if not all_mins:
            return [], 0
        # Build initial cubes from minterms + dontcares
        cubes: Set[str] = {minterm_to_cube(m, self.n_vars) for m in all_mins}
        primes: List[Implicant] = []
        iters = 0
        current = list(cubes)
        while current:
            iters += 1
            used: Set[str] = set()
            next_level: Set[str] = set()
            # Group by number of 1s
            groups: Dict[int, List[str]] = {}
            for cube in current:
                ones = cube.count("1")
                groups.setdefault(ones, []).append(cube)
            sorted_keys = sorted(groups.keys())
            for ki in range(len(sorted_keys) - 1):
                g1 = groups[sorted_keys[ki]]
                g2 = groups[sorted_keys[ki + 1]]
                if sorted_keys[ki + 1] != sorted_keys[ki] + 1:
                    continue
                for a in g1:
                    for b in g2:
                        merged = can_merge(a, b)
                        if merged is not None:
                            next_level.add(merged)
                            used.add(a)
                            used.add(b)
            # anything not used is prime
            for cube in current:
                if cube not in used:
                    primes.append(Implicant(cube))
            current = list(next_level)
        # deduplicate primes by cube
        seen: Set[str] = set()
        unique: List[Implicant] = []
        for p in primes:
            if p.cube not in seen:
                seen.add(p.cube)
                unique.append(p)
        return unique, iters

    # -- step 2: cover selection --------------------------------------------

    def _select_cover(
        self, primes: List[Implicant], func: BooleanFunction
    ) -> Tuple[List[Implicant], List[Implicant]]:
        """Select a minimum-cost cover of the on-set minterms."""
        target = func.minterms
        if not target:
            return [], []
        # Build coverage map: minterm -> list of prime indices
        coverage: Dict[int, List[int]] = {m: [] for m in target}
        for idx, p in enumerate(primes):
            for m in p.minterms:
                if m in coverage:
                    coverage[m].append(idx)
        # Detect uncovered minterms (shouldn't happen if primes are correct)
        uncovered = [m for m, lst in coverage.items() if not lst]
        if uncovered:
            raise RuntimeError(
                f"internal error: minterms {uncovered} not covered by any prime"
            )
        # --- essential PIs ---
        essential_idx: Set[int] = set()
        covered_minterms: Set[int] = set()
        for m, lst in coverage.items():
            if len(lst) == 1:
                essential_idx.add(lst[0])
        for idx in essential_idx:
            covered_minterms |= (primes[idx].minterms & target)
        # --- remaining cyclic core ---
        remaining: Set[int] = target - covered_minterms
        if not remaining:
            return [primes[i] for i in essential_idx], [primes[i] for i in essential_idx]
        # restrict primes to those that cover at least one remaining minterm
        candidate_idx = [
            i for i, p in enumerate(primes)
            if (p.minterms & remaining) and i not in essential_idx
        ]
        if self.use_petrick and len(remaining) <= 22:
            chosen = self._petrick_cover(
                primes, candidate_idx, remaining, essential_idx
            )
        else:
            chosen = self._greedy_cover(
                primes, candidate_idx, remaining, essential_idx
            )
        essentials = [primes[i] for i in essential_idx]
        return chosen, essentials

    def _petrick_cover(
        self,
        primes: List[Implicant],
        candidates: List[int],
        remaining: Set[int],
        essential_idx: Set[int],
    ) -> List[Implicant]:
        """Solve the cyclic core with Petrick's method."""
        solver = PetrickSolver()
        # For each remaining minterm, build a sum-of-products clause
        # over the prime indices that cover it.
        clauses: List[List[int]] = []
        for m in sorted(remaining):
            clause = [
                idx for idx in candidates if m in primes[idx].minterms
            ]
            clauses.append(clause)
        solution = solver.solve(clauses)
        best = solution[0] if solution else set(candidates)
        result_idx = set(best) | essential_idx
        return [primes[i] for i in sorted(result_idx)]

    def _greedy_cover(
        self,
        primes: List[Implicant],
        candidates: List[int],
        remaining: Set[int],
        essential_idx: Set[int],
    ) -> List[Implicant]:
        """Greedy heuristic cover (fallback for large cores)."""
        chosen: List[int] = list(essential_idx)
        to_cover: Set[int] = set(remaining)
        avail = list(candidates)
        while to_cover:
            best_idx = -1
            best_gain = -1
            best_literals = 10 ** 9
            for idx in avail:
                gain = len(primes[idx].minterms & to_cover)
                lits = primes[idx].n_literals
                if gain > best_gain or (
                    gain == best_gain and lits < best_literals
                ):
                    best_gain = gain
                    best_literals = lits
                    best_idx = idx
            if best_idx == -1 or best_gain == 0:
                break
            chosen.append(best_idx)
            to_cover -= primes[best_idx].minterms
            avail.remove(best_idx)
        return [primes[i] for i in chosen]

    # -- formatting ----------------------------------------------------------

    @staticmethod
    def _format_sop(implicants: List[Implicant], names: Sequence[str]) -> str:
        terms = [imp.sop_term(names) for imp in implicants]
        if not terms:
            return "0"
        return " + ".join(terms)