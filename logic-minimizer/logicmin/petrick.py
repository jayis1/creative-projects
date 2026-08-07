"""
Petrick's method — find all minimum-cost covers of a prime-implicant chart.

Given a list of clauses (each clause is a list of prime indices that cover a
particular minterm), Petrick's method computes the product-of-sums and
distributes it into a sum-of-products.  Each product term in the result
corresponds to a set of primes that covers every minterm.  We then select the
products with the fewest primes (and, as a tie-breaker, the fewest total
literals).

Implementation notes
--------------------
The naive distribution blows up exponentially.  We use an **absorption-based
incremental expansion**:

* Maintain a list of product terms (each a ``frozenset`` of prime indices).
* For each clause, multiply every existing product by every literal in the
  clause (union), then apply **absorption** to prune dominated products.
* This keeps the working set manageable for charts with up to ~20 minterms.
"""

from __future__ import annotations

from typing import FrozenSet, Iterable, List, Sequence, Set


class Term:
    """A single literal in a Petrick clause (a prime implicant index)."""

    __slots__ = ("index",)

    def __init__(self, index: int) -> None:
        self.index = index

    def __repr__(self) -> str:
        return f"P{self.index}"


class Product:
    """A product of terms — a set of prime indices that together cover minterms."""

    __slots__ = ("indices", "_hash")

    def __init__(self, indices: Iterable[int]) -> None:
        self.indices = frozenset(indices)
        self._hash = hash(self.indices)

    def __mul__(self, other: "Product") -> "Product":
        return Product(self.indices | other.indices)

    def __contains__(self, idx: int) -> bool:
        return idx in self.indices

    def __len__(self) -> int:
        return len(self.indices)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Product):
            return NotImplemented
        return self.indices == other.indices

    def __hash__(self) -> int:
        return self._hash

    def __repr__(self) -> str:
        inner = "·".join(f"P{i}" for i in sorted(self.indices))
        return f"({inner})"

    def absorbs(self, other: "Product") -> bool:
        """Return True if ``self ⊇ other`` (self is a superset → other absorbs self)."""
        return other.indices <= self.indices


class PetrickSolver:
    """Solve Petrick's product-of-sums to find minimum covers."""

    def solve(
        self,
        clauses: Sequence[Sequence[int]],
        max_products: int = 100_000,
    ) -> List[FrozenSet[int]]:
        """Return all minimum-cost solutions.

        Each solution is a ``frozenset`` of prime indices.  "Minimum cost"
        means fewest primes; ties are broken by total literal count, which
        the caller must supply separately (here we just return minimum-size
        solutions).
        """
        if not clauses:
            return [frozenset()]
        # deduplicate clauses
        seen_clause: Set[FrozenSet[int]] = set()
        clean: List[List[int]] = []
        for c in clauses:
            fc = frozenset(c)
            if fc not in seen_clause:
                seen_clause.add(fc)
                clean.append(list(fc))
        # trivial clauses (single literal) applied first shrink the search
        clean.sort(key=len)
        products: List[Product] = [Product(())]
        for clause in clean:
            new_products: List[Product] = []
            for prod in products:
                for idx in clause:
                    if idx in prod:
                        # already covered — product unchanged
                        merged = prod
                    else:
                        merged = Product(prod.indices | {idx})
                    new_products.append(merged)
            # absorption: remove products that are supersets of others
            products = self._absorb(new_products, max_products)
            if not products:
                break
        if not products:
            return []
        min_size = min(len(p) for p in products)
        best = [p.indices for p in products if len(p) == min_size]
        return best

    @staticmethod
    def _absorb(products: List[Product], max_products: int) -> List[Product]:
        """Remove absorbed (superset) products; deduplicate."""
        # deduplicate
        unique: dict[frozenset[int], Product] = {}
        for p in products:
            if p.indices not in unique:
                unique[p.indices] = p
            if len(unique) > max_products:
                raise RuntimeError(
                    f"Petrick expansion exceeded {max_products} products; "
                    "use greedy fallback"
                )
        items = list(unique.values())
        # sort by size so smaller products are checked first
        items.sort(key=len)
        kept: List[Product] = []
        for p in items:
            dominated = False
            for q in kept:
                if q.indices <= p.indices and q.indices != p.indices:
                    dominated = True
                    break
            if not dominated:
                kept.append(p)
        return kept