"""
Reduced Ordered Binary Decision Diagrams (ROBDDs).

A BDD is a rooted, directed acyclic graph that compactly represents a boolean
function.  At each internal node, a decision variable is tested; the two
outgoing edges (low = 0, high = 1) lead to child nodes.  Terminal nodes are
**0** (false) and **1** (true).

This module provides:

* ``BDDNode`` — internal/terminal nodes with a unique table (hash-consing).
* ``BDDManager`` — variable ordering, ITE (if-then-else) construction,
  reduction, memoization, and standard boolean operations (AND, OR, XOR, NOT,
  IMPLIES).
* ``from_function`` / ``from_sop_cubes`` — build a BDD from a
  :class:`~logicmin.boolean.BooleanFunction` or a list of SOP cubes.
* ``to_sop`` — extract an irredundant SOP cover from a BDD (one path per
  on-set minterm group).
* ``count_satisfying`` — count the number of satisfying assignments in O(|nodes|).
* ``render_ascii`` — render the BDD as a layered ASCII diagram.

ROBDDs share sub-graphs, so functions with many minterms can be represented
in very few nodes.  Variable ordering is fixed at construction time (the
default A-first ordering is usually adequate for up to ~10 variables).
"""

from __future__ import annotations

from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple

from .boolean import BooleanFunction, var_names, cube_to_minterms


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

class BDDNode:
    """A node in a ROBDD.

    Internal nodes have ``var`` (variable index), ``low`` and ``high`` children.
    Terminal nodes have ``var = -1`` and ``value`` in {0, 1}.
    """

    __slots__ = ("var", "low", "high", "value", "_hash")

    def __init__(
        self,
        var: int,
        low: Optional["BDDNode"] = None,
        high: Optional["BDDNode"] = None,
        value: Optional[int] = None,
    ) -> None:
        self.var = var
        self.low = low
        self.high = high
        self.value = value
        if var < 0:
            # terminal
            self._hash = hash(("terminal", value))
        else:
            self._hash = hash(("internal", var, low, high))

    @property
    def is_terminal(self) -> bool:
        return self.var < 0

    @property
    def is_one(self) -> bool:
        return self.is_terminal and self.value == 1

    @property
    def is_zero(self) -> bool:
        return self.is_terminal and self.value == 0

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BDDNode):
            return NotImplemented
        if self.is_terminal and other.is_terminal:
            return self.value == other.value
        if self.is_terminal != other.is_terminal:
            return False
        return self.var == other.var and self.low is other.low and self.high is other.high

    def __hash__(self) -> int:
        return self._hash

    def __repr__(self) -> str:
        if self.is_terminal:
            return f"BDD({self.value})"
        return f"BDD(var={self.var}, low={self.low!r}, high={self.high!r})"


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class BDDManager:
    """Manage a Reduced Ordered BDD with hash-consing and memoized ITE.

    Parameters
    ----------
    n_vars : int
        Number of boolean variables (ordering is 0, 1, 2, ..., n-1).
    """

    def __init__(self, n_vars: int) -> None:
        if n_vars <= 0:
            raise ValueError("n_vars must be positive")
        if n_vars > 32:
            raise ValueError("n_vars > 32 not supported")
        self.n_vars = n_vars
        # Unique table: (var, low_id, high_id) → BDDNode
        self._unique: Dict[Tuple, BDDNode] = {}
        # Memo for ITE
        self._ite_cache: Dict[Tuple, BDDNode] = {}
        # Terminal nodes
        self.zero = BDDNode(-1, value=0)
        self.one = BDDNode(-1, value=1)
        self._unique[("terminal", 0)] = self.zero
        self._unique[("terminal", 1)] = self.one
        # Variable nodes cache
        self._var_nodes: Dict[int, BDDNode] = {}

    # -- node management ----------------------------------------------------

    def _mk(self, var: int, low: BDDNode, high: BDDNode) -> BDDNode:
        """Create or retrieve a unique node for (var, low, high)."""
        # Reduction rules
        if low is high:
            return low
        key = (var, id(low), id(high))
        node = self._unique.get(key)
        if node is not None:
            return node
        node = BDDNode(var, low, high)
        self._unique[key] = node
        return node

    def var_node(self, var: int) -> BDDNode:
        """Return the BDD for a single variable: ``high=1, low=0``."""
        if var in self._var_nodes:
            return self._var_nodes[var]
        node = self._mk(var, self.zero, self.one)
        self._var_nodes[var] = node
        return node

    # -- ITE (if-then-else) -------------------------------------------------

    def ite(self, f: BDDNode, g: BDDNode, h: BDDNode) -> BDDNode:
        """If f then g else h.  The core operation for all boolean functions."""
        # Terminal cases
        if f is self.one:
            return g
        if f is self.zero:
            return h
        if g is h:
            return g
        if g is self.one and h is self.zero:
            return f
        if g is self.zero and h is self.one:
            return self.negate(f)
        key = (id(f), id(g), id(h))
        cached = self._ite_cache.get(key)
        if cached is not None:
            return cached
        # Determine top variable
        top = self._top_var(f, g, h)
        f_low, f_high = self._cofactor(f, top)
        g_low, g_high = self._cofactor(g, top)
        h_low, h_high = self._cofactor(h, top)
        low = self.ite(f_low, g_low, h_low)
        high = self.ite(f_high, g_high, h_high)
        result = self._mk(top, low, high)
        self._ite_cache[key] = result
        return result

    @staticmethod
    def _top_var(*nodes: BDDNode) -> int:
        """Return the smallest variable index among the nodes."""
        best = 10**9
        for n in nodes:
            if not n.is_terminal and n.var < best:
                best = n.var
        return best

    def _cofactor(self, node: BDDNode, var: int) -> Tuple[BDDNode, BDDNode]:
        """Return (low_cofactor, high_cofactor) of node w.r.t. var."""
        if node.is_terminal or node.var > var:
            return node, node
        if node.var == var:
            return node.low, node.high
        # node.var < var: recurse (shouldn't happen in ordered BDD but safe)
        low_l, low_h = self._cofactor(node.low, var)
        high_l, high_h = self._cofactor(node.high, var)
        return self._mk(node.var, low_l, low_h), self._mk(node.var, high_l, high_h)

    # -- boolean operations -------------------------------------------------

    def negate(self, f: BDDNode) -> BDDNode:
        """Logical NOT: swap 0 and 1 terminals."""
        if f is self.one:
            return self.zero
        if f is self.zero:
            return self.one
        # Directly swap terminals instead of using ITE (avoids recursion)
        return self._swap_terminals(f)

    def _swap_terminals(self, node: BDDNode) -> BDDNode:
        """Recursively swap 0 and 1 terminals in the sub-BDD rooted at node."""
        if node is self.one:
            return self.zero
        if node is self.zero:
            return self.one
        # Use memoization to avoid recomputation
        key = ("negate", id(node))
        cached = self._ite_cache.get(key)
        if cached is not None:
            return cached
        low = self._swap_terminals(node.low)
        high = self._swap_terminals(node.high)
        result = self._mk(node.var, low, high)
        self._ite_cache[key] = result
        return result

    def and_(self, f: BDDNode, g: BDDNode) -> BDDNode:
        return self.ite(f, g, self.zero)

    def or_(self, f: BDDNode, g: BDDNode) -> BDDNode:
        return self.ite(f, self.one, g)

    def xor(self, f: BDDNode, g: BDDNode) -> BDDNode:
        return self.ite(f, self.negate(g), g)

    def implies(self, f: BDDNode, g: BDDNode) -> BDDNode:
        return self.ite(f, g, self.one)

    def nand(self, f: BDDNode, g: BDDNode) -> BDDNode:
        return self.negate(self.and_(f, g))

    def nor(self, f: BDDNode, g: BDDNode) -> BDDNode:
        return self.negate(self.or_(f, g))

    # -- construction from functions ----------------------------------------

    def from_function(self, func: BooleanFunction) -> BDDNode:
        """Build a BDD from a :class:`BooleanFunction`.

        Uses Shannon expansion: for each variable in order, build the
        cofactors recursively.
        """
        return self._build_from_minterms(func.minterms | func.dontcare, 0)

    def _build_from_minterms(self, minterms: FrozenSet[int], var: int) -> BDDNode:
        """Recursively build a BDD from a set of minterms via Shannon expansion."""
        if var >= self.n_vars:
            # Leaf: is the (empty) assignment a minterm?
            return self.one if minterms else self.zero
        # Split into cofactors
        mask = 1 << (self.n_vars - 1 - var)
        low_mins = frozenset(m for m in minterms if not (m & mask))
        high_mins = frozenset(m for m in minterms if (m & mask))
        low = self._build_from_minterms(low_mins, var + 1)
        high = self._build_from_minterms(high_mins, var + 1)
        return self._mk(var, low, high)

    def from_sop_cubes(self, cubes: Sequence[str]) -> BDDNode:
        """Build a BDD from a list of SOP cubes (OR of product terms)."""
        result: BDDNode = self.zero
        for cube in cubes:
            term = self._build_from_cube(cube, 0)
            result = self.or_(result, term)
        return result

    def _build_from_cube(self, cube: str, var: int) -> BDDNode:
        """Build a BDD for a single product term (cube)."""
        if var >= self.n_vars:
            return self.one
        c = cube[var]
        if c == "-":
            low = self._build_from_cube(cube, var + 1)
            high = low  # same for both branches
            return self._mk(var, low, high)
        if c == "0":
            low = self._build_from_cube(cube, var + 1)
            return self._mk(var, low, self.zero)
        # c == "1"
        high = self._build_from_cube(cube, var + 1)
        return self._mk(var, self.zero, high)

    # -- queries ------------------------------------------------------------

    def count_satisfying(self, node: BDDNode) -> int:
        """Count the number of satisfying assignments."""
        return self._count_sat(node, 0)

    def _count_sat(self, node: BDDNode, var: int) -> int:
        if node is self.zero:
            return 0
        if node is self.one:
            return 1 << (self.n_vars - var)
        if node.is_terminal:
            return 1 << (self.n_vars - var) if node.is_one else 0
        # If node skips variables, account for the skipped levels
        # Each skipped variable doubles the count (both 0 and 1 are possible)
        if node.var > var:
            skip = node.var - var
            return (1 << skip) * self._count_sat(node, node.var)
        # node.var == var
        low_count = self._count_sat(node.low, var + 1)
        high_count = self._count_sat(node.high, var + 1)
        return low_count + high_count

    def to_sop(self, node: BDDNode) -> List[str]:
        """Extract an SOP cover (list of cubes) from the BDD.

        Each path from root to the **1** terminal is a cube.
        """
        cubes: List[str] = []
        self._extract_paths(node, ["-"] * self.n_vars, 0, cubes)
        return cubes

    def _extract_paths(
        self,
        node: BDDNode,
        assignment: List[str],
        var: int,
        cubes: List[str],
    ) -> None:
        if node is self.zero:
            return
        if node is self.one:
            cubes.append("".join(assignment))
            return
        # Skip vars that don't appear in this sub-BDD
        while var < self.n_vars and (node.is_terminal or node.var > var):
            var += 1
        if node.is_terminal:
            if node.is_one:
                cubes.append("".join(assignment))
            return
        if node.var == var:
            # Low branch (var = 0)
            assignment[var] = "0"
            self._extract_paths(node.low, assignment, var + 1, cubes)
            # High branch (var = 1)
            assignment[var] = "1"
            self._extract_paths(node.high, assignment, var + 1, cubes)
            assignment[var] = "-"

    def node_count(self, node: BDDNode) -> int:
        """Count the number of unique internal nodes in the BDD rooted at node."""
        visited: set = set()
        self._count_nodes(node, visited)
        return len(visited)

    def _count_nodes(self, node: BDDNode, visited: set) -> None:
        if node in visited or node.is_terminal:
            return
        visited.add(node)
        self._count_nodes(node.low, visited)
        self._count_nodes(node.high, visited)

    # -- rendering ----------------------------------------------------------

    def render_ascii(self, node: BDDNode) -> str:
        """Render the BDD as a layered ASCII diagram."""
        names = var_names(self.n_vars)
        # Collect nodes by level
        levels: Dict[int, List[BDDNode]] = {}
        visited: set = set()
        self._collect_levels(node, 0, levels, visited)
        lines: List[str] = []
        for var in sorted(levels.keys()):
            if var >= self.n_vars:
                # terminals
                label = "0/1"
            else:
                label = names[var]
            nodes_at_level = levels[var]
            node_strs = []
            for n in nodes_at_level:
                if n.is_terminal:
                    node_strs.append(str(n.value))
                else:
                    node_strs.append(f"[{names[n.var]}]")
            lines.append(f"  {label}: {'  '.join(node_strs)}")
        # Add edges
        lines.append("")
        lines.append("Edges (low=0 dashed, high=1 solid):")
        edges: List[str] = []
        self._collect_edges(node, edges, names, set())
        lines.extend(edges)
        return "\n".join(lines)

    def _collect_levels(
        self, node: BDDNode, depth: int, levels: Dict[int, List[BDDNode]], visited: set
    ) -> None:
        if node in visited:
            return
        visited.add(node)
        if node.is_terminal:
            level_key = self.n_vars
            levels.setdefault(level_key, []).append(node)
            return
        levels.setdefault(node.var, []).append(node)
        self._collect_levels(node.low, depth + 1, levels, visited)
        self._collect_levels(node.high, depth + 1, levels, visited)

    def _collect_edges(
        self, node: BDDNode, edges: List[str], names: Sequence[str], visited: set
    ) -> None:
        if node in visited or node.is_terminal:
            return
        visited.add(node)
        src = names[node.var]
        if node.low.is_terminal:
            edges.append(f"  {src} --0--> {node.low.value}")
        else:
            edges.append(f"  {src} --0--> {names[node.low.var]}")
            self._collect_edges(node.low, edges, names, visited)
        if node.high.is_terminal:
            edges.append(f"  {src} ==1==> {node.high.value}")
        else:
            edges.append(f"  {src} ==1==> {names[node.high.var]}")
            self._collect_edges(node.high, edges, names, visited)

    # -- equality check -----------------------------------------------------

    def equivalent(self, f: BDDNode, g: BDDNode) -> bool:
        """Check if two BDDs represent the same function."""
        return f is g


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def build_bdd(func: BooleanFunction) -> Tuple[BDDManager, BDDNode]:
    """Build a ROBDD from a :class:`BooleanFunction`.

    Returns ``(manager, root_node)``.
    """
    mgr = BDDManager(func.n_vars)
    root = mgr.from_function(func)
    return mgr, root


def bdd_sop(func: BooleanFunction) -> List[str]:
    """Build a BDD from func and extract the SOP cover.

    This gives an alternative SOP that may differ from QM/Espresso but is
    guaranteed to cover exactly the on-set (+ dont-cares).
    """
    mgr, root = build_bdd(func)
    return mgr.to_sop(root)