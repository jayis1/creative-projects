"""
Congruence closure solver for the theory of Uninterpreted Functions
with Equality (EUF).

The algorithm follows the classic union-find based approach described by
Nelson & Oppen (1980) and later refined by Nieuwenhuis & Oliveras.

Key ideas:
  - Represent each term as a node with a unique id.
  - Maintain a union-find structure over node ids.
  - When two terms are asserted equal, union them and propagate congruence
    (if f(a) and f(b) with a~b then f(a)~f(b)).
  - To check disequality a != b, see if find(a) == find(b).
"""

from __future__ import annotations

from typing import Dict, List, Tuple, Set, Optional
from dataclasses import dataclass

from .ast import Term, Var, App, BoolConst, NumConst


@dataclass
class _Node:
    """A node in the congruence-closure e-graph."""
    # Union-find parent (None => root, store own id)
    parent: int
    # The term this node represents (only meaningful for the representative)
    term: Optional[Term]
    # For function applications: (func_name, tuple_of_child_ids)
    # Used for congruence detection.
    app_sig: Optional[Tuple[str, Tuple[int, ...]]] = None
    # List of parents (function-app nodes that have this node as a child)
    parents: List[int] = None  # type: ignore

    def __post_init__(self):
        if self.parents is None:
            self.parents = []


class CongruenceClosure:
    """Incremental congruence-closure data structure."""

    def __init__(self):
        self._nodes: List[_Node] = []
        self._term_to_id: Dict[Term, int] = {}
        # Signature -> node id, for congruence propagation
        self._sig_to_rep: Dict[Tuple[str, Tuple[int, ...]], int] = {}

    # ------------------------------------------------------------------
    # Term registration
    # ------------------------------------------------------------------

    def add_term(self, term: Term) -> int:
        """Ensure *term* has a node id, creating subterm nodes as needed.

        Returns the node id for ``term``.
        """
        if term in self._term_to_id:
            return self._term_to_id[term]
        if isinstance(term, (BoolConst, NumConst)):
            nid = self._new_node(term)
            return nid
        if isinstance(term, Var):
            nid = self._new_node(term)
            return nid
        if isinstance(term, App):
            child_ids = tuple(self.add_term(c) for c in term.args)
            sig = (term.func, child_ids)
            # Check for existing congruent term
            for existing_term, existing_id in self._term_to_id.items():
                if isinstance(existing_term, App) and existing_term.func == term.func:
                    existing_child_ids = tuple(
                        self._term_to_id[c] for c in existing_term.args
                    )
                    if existing_child_ids == child_ids:
                        # Same signature — reuse node
                        self._term_to_id[term] = existing_id
                        return existing_id
            nid = self._new_node(term, app_sig=sig)
            for cid in child_ids:
                self._nodes[nid].parents.append(cid)
                # Actually parents should point back to this app node from children
                self._nodes[cid].parents.append(nid)
            return nid
        raise TypeError(f"Cannot add term of type {type(term)}")

    def _new_node(self, term: Term, app_sig=None) -> int:
        nid = len(self._nodes)
        node = _Node(parent=nid, term=term, app_sig=app_sig)
        self._nodes.append(node)
        self._term_to_id[term] = nid
        return nid

    # ------------------------------------------------------------------
    # Union-find
    # ------------------------------------------------------------------

    def _find(self, nid: int) -> int:
        """Find the representative of the class containing *nid*, with path halving."""
        root = nid
        while self._nodes[root].parent != root:
            root = self._nodes[root].parent
        # Path compression
        while self._nodes[nid].parent != root:
            nxt = self._nodes[nid].parent
            self._nodes[nid].parent = root
            nid = nxt
        return root

    def _union(self, a: int, b: int) -> bool:
        """Union classes containing *a* and *b*.  Returns True if merged."""
        ra = self._find(a)
        rb = self._find(b)
        if ra == rb:
            return False
        # Merge smaller into larger (by id — simple heuristic)
        self._nodes[rb].parent = ra
        # Reinsert signature of the new rep
        sig = self._nodes[ra].app_sig
        if sig is not None:
            self._sig_to_rep[sig] = ra
        return True

    # ------------------------------------------------------------------
    # Assert equality and check
    # ------------------------------------------------------------------

    def assert_eq(self, a: Term, b: Term) -> bool:
        """Assert ``a == b``.  Returns True if a new equality was learned,
        False if it was already known."""
        id_a = self.add_term(a)
        id_b = self.add_term(b)
        if self._find(id_a) == self._find(id_b):
            return False
        self._union(id_a, id_b)
        self._propagate()
        return True

    def assert_diseq(self, a: Term, b: Term) -> bool:
        """Assert ``a != b``.  Returns False if immediately contradictory."""
        id_a = self.add_term(a)
        id_b = self.add_term(b)
        self._propagate()  # ensure congruences are propagated
        if self._find(id_a) == self._find(id_b):
            return False  # Contradiction: a=b but we want a!=b
        return True

    def are_equal(self, a: Term, b: Term) -> bool:
        id_a = self.add_term(a)
        id_b = self.add_term(b)
        self._propagate()  # ensure congruences are propagated
        return self._find(id_a) == self._find(id_b)

    def are_disequal(self, a: Term, b: Term) -> bool:
        return not self.are_equal(a, b)

    # ------------------------------------------------------------------
    # Congruence propagation
    # ------------------------------------------------------------------

    def _propagate(self):
        """Propagate congruences after unions.

        The key insight: two function applications f(a1,...,an) and
        f(b1,...,bn) are congruent iff find(a_i) == find(b_i) for all i.
        We use signatures (func, (find(child1), find(child2), ...)) to
        detect this.
        """
        changed = True
        while changed:
            changed = False
            self._sig_to_rep.clear()
            for nid, node in enumerate(self._nodes):
                if node.app_sig is None:
                    continue
                if self._find(nid) != nid:
                    continue  # skip non-representatives
                # Compute the canonical signature using representatives of children
                func, child_ids = node.app_sig
                canon_sig = (func, tuple(self._find(cid) for cid in child_ids))
                rep = self._sig_to_rep.get(canon_sig)
                if rep is not None and self._find(rep) != nid:
                    # Congruent!  Merge.
                    self._union(nid, rep)
                    changed = True
                else:
                    self._sig_to_rep[canon_sig] = nid

    # ------------------------------------------------------------------
    # Model generation
    # ------------------------------------------------------------------

    def get_representative_value(self, term: Term) -> Optional[Term]:
        """Return a canonical representative term for the class of *term*."""
        nid = self.add_term(term)
        root = self._find(nid)
        rep = self._nodes[root].term
        return rep

    def equivalence_classes(self) -> Dict[int, List[Term]]:
        """Return mapping from root-id to list of terms in that class."""
        classes: Dict[int, List[Term]] = {}
        for term, nid in self._term_to_id.items():
            root = self._find(nid)
            classes.setdefault(root, []).append(term)
        return classes