"""
Espresso-style heuristic two-level minimizer.

This is a simplified, self-contained implementation of the classic Espresso
loop:

    expand  →  irredundant  →  reduce  →  (repeat)

Unlike :class:`QuineMcCluskey` (which is exact but exponential), Espresso
scales to functions with many variables by using heuristics.

* **Expand** — grow each cube to its maximal size (cover as many minterms
  and don't-cares as possible without covering any off-set minterm).
* **Irredundant** — remove cubes that are redundant (fully covered by other
  cubes).
* **Reduce** — shrink each cube to the smallest size that still covers its
  uniquely-covered minterms, so the next expand can find a different shape.
"""

from __future__ import annotations

from typing import FrozenSet, Iterable, List, Optional, Sequence, Set

from .boolean import (
    BooleanFunction,
    Implicant,
    can_merge,
    cube_covers,
    cube_to_minterms,
    minterm_to_cube,
    var_names,
)
from .quine_mccluskey import MinimizationResult


class Espresso:
    """Heuristic two-level SOP minimizer."""

    def __init__(
        self,
        n_vars: int,
        max_iter: int = 50,
        expand_strategy: str = "guarded",
    ) -> None:
        if n_vars <= 0:
            raise ValueError("n_vars must be positive")
        if n_vars > 32:
            raise ValueError("n_vars > 32 not supported")
        if expand_strategy not in ("guarded", "aggressive"):
            raise ValueError("expand_strategy must be 'guarded' or 'aggressive'")
        self.n_vars = n_vars
        self.max_iter = max_iter
        self.expand_strategy = expand_strategy

    # -- public API ---------------------------------------------------------

    def minimize(self, func: BooleanFunction) -> MinimizationResult:
        if func.n_vars != self.n_vars:
            raise ValueError(
                f"function has {func.n_vars} vars, minimizer expects {self.n_vars}"
            )
        onset = func.minterms
        if not onset:
            return MinimizationResult(
                prime_implicants=[], essential_implicants=[],
                chosen_implicants=[], sop="0", sop_cubes=[],
                n_literals=0, n_terms=0, minterms_covered=[],
                function=func, method="espresso",
            )
        # Check for tautology (all minterms + dc cover the universe)
        if self._is_tautology(func):
            return MinimizationResult(
                prime_implicants=[Implicant("-" * self.n_vars)],
                essential_implicants=[Implicant("-" * self.n_vars)],
                chosen_implicants=[Implicant("-" * self.n_vars)],
                sop="1", sop_cubes=["-" * self.n_vars],
                n_literals=0, n_terms=1,
                minterms_covered=sorted(onset),
                function=func, method="espresso",
            )
        # initial cover: singleton minterms
        cover = [minterm_to_cube(m, self.n_vars) for m in sorted(onset)]
        best_cover = list(cover)
        best_cost = self._cost(cover)
        best_cover_loop = list(cover)  # save best from loop iterations
        for _ in range(self.max_iter):
            cover = self._expand_all(cover, func)
            cover = self._irredundant(cover, func)
            current_cost = self._cost(cover)
            if current_cost < best_cost:
                best_cost = current_cost
                best_cover_loop = list(cover)
            cover = self._reduce_all(cover, func)
        # Use the best cover found during the loop
        best_cover = best_cover_loop
        # final expand + irredundant to clean up
        best_cover = self._expand_all(best_cover, func)
        best_cover = self._irredundant(best_cover, func)
        # Bug fix: the original code had `best_cover = best_cover` (a no-op)
        # here.  After the final expand+irredundant, if the cost got worse
        # than the best found during the loop, we should keep the loop's best.
        final_cost = self._cost(best_cover)
        if final_cost > best_cost:
            # restore the best cover from the loop
            best_cover = self._expand_all(best_cover_loop, func)
            best_cover = self._irredundant(best_cover, func)
        imps = [Implicant(c) for c in best_cover]
        imps.sort()
        sop_str = " + ".join(imp.sop_term(func.var_names) for imp in imps) or "0"
        covered = sorted({m for imp in imps for m in imp.minterms if m in onset})
        n_literals = sum(imp.n_literals for imp in imps)
        return MinimizationResult(
            prime_implicants=imps,
            essential_implicants=[],
            chosen_implicants=imps,
            sop=sop_str,
            sop_cubes=[imp.cube for imp in imps],
            n_literals=n_literals,
            n_terms=len(imps),
            minterms_covered=covered,
            function=func,
            method="espresso",
        )

    # -- helpers ------------------------------------------------------------

    def _is_tautology(self, func: BooleanFunction) -> bool:
        """True if every input combination is either on-set or don't-care."""
        universe = set(range(1 << self.n_vars))
        return (func.minterms | func.dontcare) == universe

    def _cost(self, cover: Sequence[str]) -> int:
        """Literal cost of a cover."""
        return sum(sum(1 for c in cube if c != "-") for cube in cover)

    def _off_set(self, func: BooleanFunction) -> FrozenSet[int]:
        universe = set(range(1 << self.n_vars))
        return frozenset(universe - func.minterms - func.dontcare)

    # -- expand -------------------------------------------------------------

    def _expand_all(self, cover: List[str], func: BooleanFunction) -> List[str]:
        """Expand each cube to maximal size."""
        off = self._off_set(func)
        off_cubes = [minterm_to_cube(m, self.n_vars) for m in off]
        expanded: List[str] = []
        # sort cubes by size (largest first) to keep big implicants stable
        cover_sorted = sorted(cover, key=lambda c: c.count("-"), reverse=True)
        for cube in cover_sorted:
            new_cube = self._expand_cube(cube, off_cubes)
            if new_cube not in expanded:
                expanded.append(new_cube)
        return expanded

    def _expand_cube(self, cube: str, off_cubes: List[str]) -> str:
        """Expand a single cube as much as possible without covering any off-set minterm.

        Try to turn each '0'/'1' position into a '-' one at a time.
        """
        result = list(cube)
        # order positions by least-significant first (arbitrary but stable)
        positions = list(range(self.n_vars))
        if self.expand_strategy == "aggressive":
            positions.sort(key=lambda i: result[i] == "-")
        for i in positions:
            if result[i] == "-":
                continue
            trial = result[:i] + ["-"] + result[i + 1:]
            trial_str = "".join(trial)
            if not self._intersects_off(trial_str, off_cubes):
                result[i] = "-"
        return "".join(result)

    def _intersects_off(self, cube: str, off_cubes: List[str]) -> bool:
        """Check if ``cube`` covers any off-set minterm.

        ``off_cubes`` is a list of pure 0/1 cubes (no dashes) representing
        the off-set minterms.  We check if ``cube`` intersects any of them
        via cube-cube intersection.
        """
        # Bug fix: removed dead code — a for-loop that called
        # cube_to_minterms(cube) and did nothing (body was `pass`).
        # This wasted allocation on every call and was confusing.
        for oc in off_cubes:
            if self._cubes_intersect(cube, oc):
                return True
        return False

    @staticmethod
    def _cubes_intersect(a: str, b: str) -> bool:
        for ca, cb in zip(a, b):
            if ca == "-" or cb == "-":
                continue
            if ca != cb:
                return False
        return True

    # -- irredundant --------------------------------------------------------

    def _irredundant(self, cover: List[str], func: BooleanFunction) -> List[str]:
        """Remove redundant cubes from the cover."""
        onset = func.minterms
        # Build coverage: which minterms each cube covers
        covered_by: dict[int, list[int]] = {}
        for i, cube in enumerate(cover):
            for m in cube_to_minterms(cube):
                if m in onset:
                    covered_by.setdefault(m, []).append(i)
        # A cube is redundant if every minterm it covers is also covered
        # by at least one *other* cube.
        redundant: Set[int] = set()
        for i, cube in enumerate(cover):
            is_redundant = True
            for m in cube_to_minterms(cube):
                if m not in onset:
                    continue
                covers = covered_by.get(m, [])
                others = [j for j in covers if j != i and j not in redundant]
                if not others:
                    is_redundant = False
                    break
            if is_redundant:
                redundant.add(i)
        # remove redundant cubes one at a time (greedy: remove the one that
        # frees the most literals first)
        result = [c for i, c in enumerate(cover) if i not in redundant]
        if not result and cover:
            # safety: never return empty cover for a non-zero function
            result = [min(cover, key=lambda c: sum(1 for ch in c if ch != "-"))]
        return result

    # -- reduce -------------------------------------------------------------

    def _reduce_all(self, cover: List[str], func: BooleanFunction) -> List[str]:
        """Reduce each cube to minimal size while still covering its unique minterms."""
        onset = func.minterms
        # Build coverage map
        covered_by: dict[int, list[int]] = {}
        for i, cube in enumerate(cover):
            for m in cube_to_minterms(cube):
                if m in onset:
                    covered_by.setdefault(m, []).append(i)
        reduced: List[str] = []
        for i, cube in enumerate(cover):
            # minterms uniquely covered by this cube
            unique = [
                m for m in cube_to_minterms(cube)
                if m in onset and len(covered_by.get(m, [])) == 1
            ]
            shared = [
                m for m in cube_to_minterms(cube)
                if m in onset and len(covered_by.get(m, [])) > 1
            ]
            if not unique:
                # can't reduce (would lose coverage); keep as-is but maybe
                # shrink to cover only shared minterms
                if shared:
                    reduced_cube = self._minimal_supercube(shared)
                    reduced.append(reduced_cube)
                else:
                    reduced.append(cube)
                continue
            # supercube of uniquely-covered minterms
            min_cube = self._minimal_supercube(unique)
            # ensure we don't cover off-set
            off = self._off_set(func)
            off_cubes = [minterm_to_cube(m, self.n_vars) for m in off]
            if self._intersects_off(min_cube, off_cubes):
                # can't safely reduce; restore original
                reduced.append(cube)
            else:
                reduced.append(min_cube)
        return reduced

    def _minimal_supercube(self, minterms: Sequence[int]) -> str:
        """Return the smallest cube covering exactly the given minterms."""
        if not minterms:
            raise ValueError("need at least one minterm")
        bits = [format(m, f"0{self.n_vars}b") for m in minterms]
        result = list(bits[0])
        for b in bits[1:]:
            for i, ch in enumerate(b):
                if result[i] != ch:
                    result[i] = "-"
        return "".join(result)