"""
Product-of-Sums (POS) minimization.

The POS form is minimized by applying the Quine–McCluskey algorithm to the
*dual* function (the zeros of the original function, treating the original
don't-cares as don't-cares), and then complementing the resulting SOP via
De Morgan's law.

If ``F`` has on-set ``M`` and don't-care set ``DC``, then:

* The off-set is ``O = U - M - DC`` (where ``U`` is the universe).
* Minimizing the SOP of the off-set gives us ``F' = SOP(O)``.
* By De Morgan: ``F = POS(complement of each product term in SOP(O))``.
* Each product term like ``AB'C`` becomes a sum clause ``A' + B + C'``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from .boolean import BooleanFunction, Implicant, var_names
from .quine_mccluskey import MinimizationResult, QuineMcCluskey


@dataclass
class POSResult:
    """Result of POS minimization."""

    pos: str
    pos_clauses: List[str]
    n_clauses: int
    n_literals: int
    dual_sop: str
    function: BooleanFunction
    method: str = "pos-via-dual"

    def __repr__(self) -> str:
        return (
            f"POSResult(pos={self.pos!r}, n_clauses={self.n_clauses}, "
            f"n_literals={self.n_literals})"
        )


class POSMinimizer:
    """Minimize a boolean function in product-of-sums form.

    Parameters
    ----------
    n_vars : int
        Number of input variables.
    use_petrick : bool
        Whether to use Petrick's method for the dual SOP cover.
    """

    def __init__(self, n_vars: int, use_petrick: bool = True) -> None:
        if n_vars <= 0:
            raise ValueError("n_vars must be positive")
        if n_vars > 32:
            raise ValueError("n_vars > 32 not supported")
        self.n_vars = n_vars
        self.use_petrick = use_petrick
        self._qm = QuineMcCluskey(n_vars, use_petrick=use_petrick)

    def minimize(self, func: BooleanFunction) -> POSResult:
        """Minimize ``func`` as a product of sums."""
        if func.n_vars != self.n_vars:
            raise ValueError(
                f"function has {func.n_vars} vars, minimizer expects {self.n_vars}"
            )
        universe = set(range(1 << self.n_vars))
        off_set = universe - func.minterms - func.dontcare
        if not off_set:
            # F is always 1 (or don't-care everywhere) → POS is empty product = 1
            return POSResult(
                pos="1",
                pos_clauses=[],
                n_clauses=0,
                n_literals=0,
                dual_sop="0",
                function=func,
            )
        if not func.minterms and not func.dontcare:
            # F is always 0 → POS is 0
            return POSResult(
                pos="0",
                pos_clauses=["0"],
                n_clauses=1,
                n_literals=0,
                dual_sop="1",
                function=func,
            )
        # Build the dual function: SOP of the off-set (don't-cares shared)
        dual = BooleanFunction(
            n_vars=self.n_vars,
            minterms=off_set,
            dontcare=func.dontcare,
            name="dual",
        )
        dual_result = self._qm.minimize(dual)
        # Convert each SOP product term → POS sum clause via De Morgan
        names = var_names(self.n_vars)
        clauses: List[str] = []
        pos_cubes: List[str] = []
        for imp in dual_result.chosen_implicants:
            clause = self._product_to_sum_clause(imp, names)
            clauses.append(clause)
            pos_cubes.append(imp.cube)
        pos_str = " · ".join(f"({c})" for c in clauses) if clauses else "1"
        n_literals = sum(
            sum(1 for ch in imp.cube if ch != "-")
            for imp in dual_result.chosen_implicants
        )
        return POSResult(
            pos=pos_str,
            pos_clauses=clauses,
            n_clauses=len(clauses),
            n_literals=n_literals,
            dual_sop=dual_result.sop,
            function=func,
        )

    @staticmethod
    def _product_to_sum_clause(imp: Implicant, names: Sequence[str]) -> str:
        """Convert a product term (cube) to a sum clause via De Morgan.

        ``AB'C`` → ``A' + B + C'``
        (complement each literal and change AND to OR)
        """
        parts = []
        for i, c in enumerate(imp.cube):
            if c == "1":
                parts.append(names[i] + "'")
            elif c == "0":
                parts.append(names[i])
        return " + ".join(parts) if parts else "0"