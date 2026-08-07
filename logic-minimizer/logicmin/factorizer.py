"""
Multi-level logic factorization.

Given a sum-of-products (SOP) expression, this module extracts common algebraic
factors to produce a multi-level (factored) form with fewer total literals.

A *factored form* (Brayton) is defined recursively as:
    F = (F1)(F2)... + (F3)(F4)... + ...
where each Fi is either a literal or another factored form.

The core operation is **algebraic extraction**: find a cube (divisor) that
appears in two or more SOP cubes, factor it out, and replace those cubes with
the quotient.  This is a greedy, divide-and-conquer approach.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Set, Tuple


# ---------------------------------------------------------------------------
# Cube helpers (cubes are strings over {'0','1','-'} here too)
# ---------------------------------------------------------------------------

def cube_literals(cube: str) -> Set[Tuple[int, str]]:
    """Return the set of (position, value) literals in a cube."""
    return {(i, c) for i, c in enumerate(cube) if c != "-"}


def cubes_intersect_literal_set(cube: str, lits: Set[Tuple[int, str]]) -> bool:
    """True if ``cube`` contains every literal in ``lits``."""
    for pos, val in lits:
        if cube[pos] != val:
            return False
    return True


def remove_literals(cube: str, lits: Set[Tuple[int, str]]) -> str:
    """Return ``cube`` with the given literals replaced by '-'."""
    result = list(cube)
    for pos, _ in lits:
        result[pos] = "-"
    return "".join(result)


# ---------------------------------------------------------------------------
# FactoredForm
# ---------------------------------------------------------------------------

@dataclass
class FactoredForm:
    """A node in a factored expression tree.

    type : 'sum' | 'product' | 'literal'
    children : list of FactoredForm (for sum/product)
    literal : (position, value) for literal nodes
    """

    node_type: str
    children: List["FactoredForm"] = field(default_factory=list)
    literal: Optional[Tuple[int, str]] = None

    def literal_count(self) -> int:
        """Count total literals (leaf occurrences) in this factored form."""
        if self.node_type == "literal":
            return 1
        return sum(c.literal_count() for c in self.children)

    def to_string(self, names: Sequence[str]) -> str:
        if self.node_type == "literal":
            pos, val = self.literal  # type: ignore[misc]
            name = names[pos]
            return name if val == "1" else name + "'"
        if self.node_type == "product":
            parts = [c.to_string(names) for c in self.children]
            if len(parts) == 1:
                return parts[0]
            return "(" + "".join(parts) + ")"
        # sum
        parts = [c.to_string(names) for c in self.children]
        return " + ".join(parts)

    def __repr__(self) -> str:
        if self.node_type == "literal":
            return f"Lit({self.literal})"
        return f"{self.node_type}({self.children})"


# ---------------------------------------------------------------------------
# Factorizer
# ---------------------------------------------------------------------------

class Factorizer:
    """Greedy algebraic factorizer for SOP covers.

    Parameters
    ----------
    n_vars : int
        Number of input variables.
    max_rounds : int
        Maximum number of factor extraction rounds.
    """

    def __init__(self, n_vars: int, max_rounds: int = 20) -> None:
        if n_vars <= 0:
            raise ValueError("n_vars must be positive")
        self.n_vars = n_vars
        self.max_rounds = max_rounds

    def factorize(self, cubes: Sequence[str]) -> FactoredForm:
        """Factor a list of SOP cubes into a :class:`FactoredForm`."""
        if not cubes:
            return FactoredForm("sum", [])
        # Work on a list of cubes; iteratively extract common sub-cubes.
        nodes = [self._cube_to_factored(c) for c in cubes]
        for _ in range(self.max_rounds):
            new_nodes, changed = self._extract_once(nodes)
            nodes = new_nodes
            if not changed:
                break
        if len(nodes) == 1:
            return nodes[0]
        return FactoredForm("sum", nodes)

    def factorize_sop(self, sop: str) -> FactoredForm:
        """Parse and factorize a SOP string."""
        from .boolean import BooleanFunction
        func = BooleanFunction.from_sop(sop)
        # Recover cubes from the function's minterms — but that loses the
        # original product-term structure.  Instead parse directly.
        cubes = self._parse_sop_cubes(sop)
        return self.factorize(cubes)

    # -- internals ----------------------------------------------------------

    def _cube_to_factored(self, cube: str) -> FactoredForm:
        lits = cube_literals(cube)
        if not lits:
            # constant 1
            return FactoredForm("literal", literal=(0, "1"))  # placeholder
        if len(lits) == 1:
            return FactoredForm("literal", literal=next(iter(lits)))
        return FactoredForm(
            "product",
            [FactoredForm("literal", literal=l) for l in sorted(lits)],
        )

    def _extract_once(
        self, nodes: List[FactoredForm]
    ) -> Tuple[List[FactoredForm], bool]:
        """Try one round of common-cube extraction.

        We look for a set of literals that appears in ≥2 product nodes
        (flattening sums first).
        """
        # Flatten: collect all top-level product terms
        terms: List[Tuple[Set[Tuple[int, str]], int]] = []  # (literals, node_idx)
        for i, node in enumerate(nodes):
            lits = self._collect_product_literals(node)
            terms.append((lits, i))
        # Find the best common divisor: the literal-set that appears in the
        # most terms (with tie-break: larger set = more factoring).
        best_divisor: Optional[Set[Tuple[int, str]]] = None
        best_count = 1  # need at least 2
        best_size = 0
        # generate candidate divisors from pairwise intersections
        for i in range(len(terms)):
            for j in range(i + 1, len(terms)):
                common = terms[i][0] & terms[j][0]
                if len(common) < 1:
                    continue
                # count how many terms contain this divisor
                count = sum(
                    1 for t in terms if common <= t[0]
                )
                if count > best_count or (
                    count == best_count and len(common) > best_size
                ):
                    best_count = count
                    best_size = len(common)
                    best_divisor = common
        if best_divisor is None or best_count < 2:
            return nodes, False
        # Extract: for each node, divide by the divisor.
        # If a node's literals ⊇ divisor, replace it with (divisor)(quotient).
        divisor = best_divisor
        new_nodes: List[FactoredForm] = []
        extracted_quotients: List[FactoredForm] = []
        for node in nodes:
            lits = self._collect_product_literals(node)
            if divisor <= lits:
                quotient_lits = lits - divisor
                if quotient_lits:
                    quotient = self._build_product(quotient_lits)
                else:
                    quotient = FactoredForm("literal", literal=(0, "1"))
                extracted_quotients.append(quotient)
            else:
                new_nodes.append(node)
        divisor_node = self._build_product(divisor)
        quotient_sum = FactoredForm("sum", extracted_quotients)
        factored = FactoredForm("product", [divisor_node, quotient_sum])
        new_nodes.append(factored)
        return new_nodes, True

    def _collect_product_literals(self, node: FactoredForm) -> Set[Tuple[int, str]]:
        """Flatten a product node into its literal set; sums yield empty."""
        if node.node_type == "literal":
            return {node.literal}  # type: ignore[arg-type]
        if node.node_type == "product":
            result: Set[Tuple[int, str]] = set()
            for c in node.children:
                result |= self._collect_product_literals(c)
            return result
        return set()  # sum nodes can't be trivially collected

    @staticmethod
    def _build_product(lits: Set[Tuple[int, str]]) -> FactoredForm:
        if not lits:
            return FactoredForm("literal", literal=(0, "1"))
        if len(lits) == 1:
            return FactoredForm("literal", literal=next(iter(lits)))
        return FactoredForm(
            "product",
            sorted(
                (FactoredForm("literal", literal=l) for l in lits),
                key=lambda n: n.literal,  # type: ignore[misc]
            ),
        )

    def _parse_sop_cubes(self, sop: str) -> List[str]:
        """Parse a SOP string into cubes (for factorization)."""
        from .boolean import var_names
        terms = [t.strip() for t in sop.split("+") if t.strip()]
        if not terms:
            return []
        letters: Set[str] = set()
        for t in terms:
            for ch in t:
                if ch.isalpha():
                    letters.add(ch.upper())
        n = len(letters)
        names = var_names(n)
        var_idx = {name: i for i, name in enumerate(names)}
        cubes: List[str] = []
        for term in terms:
            cube = ["-"] * n
            i = 0
            while i < len(term):
                ch = term[i].upper()
                if ch.isalpha():
                    pos = var_idx[ch]
                    val = "1"
                    i += 1
                    if i < len(term) and term[i] == "'":
                        val = "0"
                        i += 1
                    cube[pos] = val
                else:
                    i += 1
            cubes.append("".join(cube))
        return cubes