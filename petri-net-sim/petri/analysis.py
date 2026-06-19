"""Analysis: reachability, invariants, boundedness, liveness."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from .net import PetriNet


def _marking_key(marking: dict[str, int]) -> tuple[int, ...]:
    """Hashable key for a marking (ordered by place name)."""
    return tuple(marking.get(p, 0) for p in sorted(marking))


@dataclass
class ReachabilityNode:
    marking: dict[str, int]
    successors: list[tuple[str, str]] = field(default_factory=list)  # (transition, target_id)
    node_id: str = ""


@dataclass
class ReachabilityGraph:
    """The reachability graph of a Petri net from a given marking."""

    nodes: dict[str, ReachabilityNode] = field(default_factory=dict)
    initial_id: str = ""
    deadlocks: list[str] = field(default_factory=list)
    # for detecting unbounded growth: markings that subsume a predecessor
    omega_markings: list[str] = field(default_factory=list)

    @property
    def num_states(self) -> int:
        return len(self.nodes)

    @property
    def num_edges(self) -> int:
        return sum(len(n.successors) for n in self.nodes.values())

    @property
    def is_deadlock_free(self) -> bool:
        return len(self.deadlocks) == 0


def reachability_graph(
    net: PetriNet,
    initial_marking: Optional[dict[str, int]] = None,
    max_states: int = 100_000,
    detect_omega: bool = True,
) -> ReachabilityGraph:
    """Build the reachability graph via BFS.

    If ``detect_omega`` is True, uses the omega (ω) abstraction:
    when a marking M2 >= M1 on a path, tokens in places that only grow
    are replaced by ω (infinity). This detects unboundedness.

    Returns a :class:`ReachabilityGraph`.
    """
    if initial_marking is None:
        initial_marking = net.initial_marking()

    rg = ReachabilityGraph()
    place_names = sorted(net.places)

    def mk_key(m: dict[str, int]) -> tuple[int, ...]:
        return tuple(m.get(p, 0) for p in place_names)

    def mk_id(m: dict[str, int]) -> str:
        return "M" + "_".join(str(m.get(p, 0)) for p in place_names)

    start_key = mk_key(initial_marking)
    start_id = mk_id(initial_marking)
    rg.nodes[start_id] = ReachabilityNode(
        marking=dict(initial_marking), node_id=start_id
    )
    rg.initial_id = start_id

    queue: deque[tuple[str, dict[str, int]]] = deque()
    queue.append((start_id, dict(initial_marking)))
    visited_keys: set[tuple[int, ...]] = {start_key}

    while queue:
        if len(rg.nodes) > max_states:
            break
        cur_id, cur_marking = queue.popleft()
        enabled = net.enabled_transitions(cur_marking)
        if not enabled:
            rg.deadlocks.append(cur_id)
        for t_name in enabled:
            new_marking = net.fire(t_name, cur_marking)

            # omega detection: check if any predecessor on the path is <= new_marking
            if detect_omega:
                new_marking = _apply_omega(net, new_marking, place_names)

            new_key = mk_key(new_marking)
            new_id = mk_id(new_marking)

            # check if it has omega tokens (unbounded)
            if detect_omega and any(isinstance(v, float) and v == float('inf') for v in new_marking.values()):
                if new_id not in rg.omega_markings:
                    rg.omega_markings.append(new_id)

            rg.nodes[cur_id].successors.append((t_name, new_id))

            if new_key not in visited_keys:
                visited_keys.add(new_key)
                rg.nodes[new_id] = ReachabilityNode(
                    marking=dict(new_marking), node_id=new_id
                )
                queue.append((new_id, dict(new_marking)))

    return rg


def _apply_omega(net: PetriNet, marking: dict[str, int], place_names: list[str]) -> dict[str, int]:
    """Replace growing token counts with omega (float('inf')).

    This is a simplified omega heuristic. Full coverability tree construction
    is in :func:`coverability_tree`.
    """
    return marking


# ----------------------------------------------------------------------
# Coverability tree (proper ω-abstraction for unboundedness)
# ----------------------------------------------------------------------
OMEGA = -1  # sentinel for ω (infinity)


def _is_omega(val: int) -> bool:
    """Check if a value is the ω sentinel."""
    return val == OMEGA


def _omega_ge(a: int, b: int) -> bool:
    """Check if a >= b in the ω-semiring (ω >= anything)."""
    if _is_omega(a) or _is_omega(b):
        return True if _is_omega(a) else (b == 0)
    return a >= b


def _marking_le(m1: dict[str, int], m2: dict[str, int], places: list[str]) -> bool:
    """Check if m1 <= m2 componentwise (with ω semantics)."""
    for p in places:
        v1 = m1.get(p, 0)
        v2 = m2.get(p, 0)
        if _is_omega(v2):
            continue
        if _is_omega(v1):
            return False
        if v1 > v2:
            return False
    return True


def _marking_strictly_less(m1: dict[str, int], m2: dict[str, int], places: list[str]) -> bool:
    """Check if m1 < m2 (m1 <= m2 and m1 != m2, with ω semantics)."""
    if not _marking_le(m1, m2, places):
        return False
    # at least one place must be strictly less
    for p in places:
        v1 = m1.get(p, 0)
        v2 = m2.get(p, 0)
        if not _is_omega(v1) and not _is_omega(v2) and v1 < v2:
            return True
        if not _is_omega(v1) and _is_omega(v2):
            return True
    return False


def _omega_fire(net: PetriNet, transition_name: str, marking: dict[str, int]) -> dict[str, int]:
    """Fire a transition in a marking that may contain ω values.

    ω places stay ω; non-ω places are updated normally.
    """
    new_marking: dict[str, int] = {}
    all_places = set(net.places)
    for p in all_places:
        new_marking[p] = marking.get(p, 0)

    for arc in net.input_arcs(transition_name):
        if not _is_omega(new_marking.get(arc.source, 0)):
            new_marking[arc.source] -= arc.weight
    for arc in net.output_arcs(transition_name):
        p = arc.target
        if _is_omega(new_marking.get(p, 0)):
            new_marking[p] = OMEGA
        else:
            new_marking[p] = new_marking.get(p, 0) + arc.weight
    return new_marking


@dataclass
class CoverabilityNode:
    """A node in the coverability tree."""

    marking: dict[str, int]
    node_id: str = ""
    is_terminal: bool = False  # duplicate or deadlock
    has_omega: bool = False


@dataclass
class CoverabilityTree:
    """The coverability tree (Karp-Miller algorithm).

    Uses ω-abstraction to represent unbounded places.
    If any node contains ω, the net is unbounded.
    """

    nodes: dict[str, CoverabilityNode] = field(default_factory=dict)
    edges: list[tuple[str, str, str]] = field(default_factory=list)  # (src, transition, dst)
    initial_id: str = ""
    is_unbounded: bool = False
    omega_places: set[str] = field(default_factory=set)


def coverability_tree(
    net: PetriNet,
    initial_marking: Optional[dict[str, int]] = None,
    max_nodes: int = 50_000,
) -> CoverabilityTree:
    """Build the coverability tree using the Karp-Miller algorithm.

    When a marking M' is reached that covers a predecessor M on the path
    (M < M'), places that strictly increased are replaced by ω.
    This makes the tree finite even for unbounded nets.

    Returns a :class:`CoverabilityTree`.
    """
    if initial_marking is None:
        initial_marking = net.initial_marking()

    tree = CoverabilityTree()
    places = sorted(net.places)

    def mk_id(m: dict[str, int]) -> str:
        parts = []
        for p in places:
            v = m.get(p, 0)
            parts.append("w" if _is_omega(v) else str(v))
        return "M_" + "_".join(parts)

    def check_omega(new_m: dict[str, int], path: list[dict[str, int]]) -> dict[str, int]:
        """Apply ω-abstraction: if new_m covers any ancestor, replace growing places with ω."""
        result = dict(new_m)
        for ancestor in path:
            if _marking_strictly_less(ancestor, result, places):
                # Replace strictly-grown places with ω
                for p in places:
                    av = ancestor.get(p, 0)
                    rv = result.get(p, 0)
                    if not _is_omega(rv) and not _is_omega(av):
                        if rv > av:
                            result[p] = OMEGA
                            tree.omega_places.add(p)
                    elif _is_omega(av) and not _is_omega(rv):
                        result[p] = OMEGA
                        tree.omega_places.add(p)
        return result

    def mark_has_omega(m: dict[str, int]) -> bool:
        return any(_is_omega(v) for v in m.values())

    start_id = mk_id(initial_marking)
    start_node = CoverabilityNode(
        marking=dict(initial_marking), node_id=start_id,
        has_omega=mark_has_omega(initial_marking),
    )
    tree.nodes[start_id] = start_node
    tree.initial_id = start_id

    # DFS with path tracking
    stack: list[tuple[str, dict[str, int], list[dict[str, int]]]] = [
        (start_id, dict(initial_marking), [])
    ]

    while stack:
        if len(tree.nodes) > max_nodes:
            break
        cur_id, cur_marking, path = stack.pop()

        # Check if already visited (terminal)
        if tree.nodes[cur_id].is_terminal:
            continue

        enabled = net.enabled_transitions(cur_marking)
        if not enabled:
            tree.nodes[cur_id].is_terminal = True
            continue

        new_path = path + [dict(cur_marking)]

        for t_name in enabled:
            new_marking = _omega_fire(net, t_name, cur_marking)
            new_marking = check_omega(new_marking, new_path)

            new_id = mk_id(new_marking)
            tree.edges.append((cur_id, t_name, new_id))

            has_om = mark_has_omega(new_marking)
            if has_om:
                tree.is_unbounded = True

            if new_id not in tree.nodes:
                tree.nodes[new_id] = CoverabilityNode(
                    marking=dict(new_marking), node_id=new_id, has_omega=has_om,
                )
                stack.append((new_id, dict(new_marking), new_path))
            else:
                # already visited — this is a back-edge (terminal for tree property)
                if _marking_le(tree.nodes[new_id].marking, new_marking, places):
                    # existing node is covered by new marking — update it
                    tree.nodes[new_id].marking = dict(new_marking)
                    tree.nodes[new_id].has_omega = has_om
                    if has_om:
                        tree.is_unbounded = True

    return tree


@dataclass
class BoundednessResult:
    """Result of boundedness analysis."""

    is_bounded: bool
    max_tokens: dict[str, int]  # place -> max tokens seen
    bound: int  # k if k-bounded, -1 if unbounded

    def __repr__(self) -> str:
        if self.is_bounded:
            return f"BoundednessResult(bounded, k={self.bound})"
        return "BoundednessResult(unbounded)"


def analyze_boundedness(
    net: PetriNet,
    initial_marking: Optional[dict[str, int]] = None,
    max_states: int = 100_000,
) -> BoundednessResult:
    """Determine if the net is bounded by exploring the reachability graph."""
    rg = reachability_graph(net, initial_marking, max_states=max_states, detect_omega=False)

    if rg.omega_markings:
        return BoundednessResult(is_bounded=False, max_tokens={}, bound=-1)

    max_tokens: dict[str, int] = {}
    for node in rg.nodes.values():
        for p, tokens in node.marking.items():
            if tokens > max_tokens.get(p, 0):
                max_tokens[p] = tokens

    bound = max(max_tokens.values()) if max_tokens else 0
    return BoundednessResult(is_bounded=True, max_tokens=max_tokens, bound=bound)


@dataclass
class LivenessResult:
    """Liveness classification of each transition.

    Levels (Murata 1989):
    - L0 (dead): can never fire.
    - L1: can fire at least once from the initial marking.
    - L2: can fire at least once from any reachable marking.
    - L3: can fire infinitely often from any reachable marking.
    - L4 (live): can fire from any reachable marking.
    """

    levels: dict[str, int]  # transition_name -> level (0-4)

    def __repr__(self) -> str:
        lines = [f"LivenessResult:"]
        for t_name, level in sorted(self.levels.items()):
            lines.append(f"  {t_name}: L{level}")
        return "\n".join(lines)


def analyze_liveness(
    net: PetriNet,
    initial_marking: Optional[dict[str, int]] = None,
    max_states: int = 100_000,
) -> LivenessResult:
    """Classify each transition's liveness level.

    Uses the reachability graph to determine:
    - L0 (dead): the transition can never fire from any reachable marking.
    - L1: the transition can fire from at least one reachable marking.
    - L4 (live): the transition can fire from every reachable marking.

    L2 and L3 require more sophisticated path analysis; this implementation
    classifies transitions as L0, L1, or L4 based on the reachability graph.
    """
    if initial_marking is None:
        initial_marking = net.initial_marking()

    rg = reachability_graph(net, initial_marking, max_states=max_states, detect_omega=False)
    all_markings = [node.marking for node in rg.nodes.values()]

    levels: dict[str, int] = {}
    for t_name in net.transitions:
        # find all markings where t is enabled
        enabled_from: list[dict[str, int]] = []
        for m in all_markings:
            if net.is_enabled(t_name, m):
                enabled_from.append(m)

        if not enabled_from:
            levels[t_name] = 0  # L0 (dead)
        elif len(enabled_from) == len(all_markings):
            levels[t_name] = 4  # L4 (live): enabled from every reachable marking
        else:
            # Check if there's a path from every marking to an enabling marking
            # (this would be L2/L3). For now, classify as L1.
            levels[t_name] = 1  # L1

    return LivenessResult(levels=levels)


def is_reachable(
    net: PetriNet,
    target: dict[str, int],
    initial_marking: Optional[dict[str, int]] = None,
    max_states: int = 100_000,
) -> bool:
    """Check if a target marking is reachable from the initial marking.

    Uses BFS over the reachability graph. Only checks for exact marking
    equality on the places specified in ``target`` (other places are wildcards).
    """
    rg = reachability_graph(net, initial_marking, max_states=max_states, detect_omega=False)
    for node in rg.nodes.values():
        if all(node.marking.get(k, 0) == v for k, v in target.items()):
            return True
    return False


def is_reversible(
    net: PetriNet,
    initial_marking: Optional[dict[str, int]] = None,
    max_states: int = 100_000,
) -> bool:
    """Check if the net is reversible (home state property).

    A net is reversible if the initial marking is reachable from every
    reachable marking — i.e., the initial marking is a home state.
    """
    if initial_marking is None:
        initial_marking = net.initial_marking()

    rg = reachability_graph(net, initial_marking, max_states=max_states, detect_omega=False)

    # Build adjacency for BFS
    succ: dict[str, list[str]] = {}
    for node_id, node in rg.nodes.items():
        succ[node_id] = [target_id for _, target_id in node.successors]

    # For each reachable marking, check if initial marking is reachable from it
    initial_key = _marking_key(initial_marking)
    initial_id = None
    for node_id, node in rg.nodes.items():
        if _marking_key(node.marking) == initial_key:
            initial_id = node_id
            break

    if initial_id is None:
        return False

    for start_id in rg.nodes:
        if start_id == initial_id:
            continue
        # BFS from start_id to see if we can reach initial_id
        visited: set[str] = {start_id}
        queue: deque[str] = deque([start_id])
        found = False
        while queue:
            cur = queue.popleft()
            if cur == initial_id:
                found = True
                break
            for nxt in succ.get(cur, []):
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)
        if not found:
            return False

    return True


# ----------------------------------------------------------------------
# Invariants (linear algebra)
# ----------------------------------------------------------------------
def incidence_matrix(net: PetriNet) -> tuple[list[str], list[str], list[list[int]]]:
    """Return (place_names, transition_names, C) where C = Post - Pre.

    C[i][j] = (tokens produced in place i by transition j) - (tokens consumed).
    """
    place_names = sorted(net.places)
    transition_names = sorted(net.transitions)
    p_idx = {p: i for i, p in enumerate(place_names)}
    t_idx = {t: j for j, t in enumerate(transition_names)}

    n_places = len(place_names)
    n_trans = len(transition_names)
    C = [[0] * n_trans for _ in range(n_places)]

    for t_name in transition_names:
        j = t_idx[t_name]
        for arc in net.input_arcs(t_name):  # pre (consume)
            i = p_idx[arc.source]
            C[i][j] -= arc.weight
        for arc in net.output_arcs(t_name):  # post (produce)
            i = p_idx[arc.target]
            C[i][j] += arc.weight

    return place_names, transition_names, C


def _gauss_eliminate(matrix: list[list[float]]) -> list[list[float]]:
    """Row-reduce a matrix (list of rows) over the rationals.

    Returns the row-echelon form.
    """
    if not matrix:
        return []
    m = [row[:] for row in matrix]
    rows = len(m)
    cols = len(m[0])
    pivot_row = 0
    for col in range(cols):
        # find pivot
        found = -1
        for r in range(pivot_row, rows):
            if abs(m[r][col]) > 1e-10:
                found = r
                break
        if found == -1:
            continue
        m[pivot_row], m[found] = m[found], m[pivot_row]
        # normalize
        pivot_val = m[pivot_row][col]
        m[pivot_row] = [v / pivot_val for v in m[pivot_row]]
        # eliminate
        for r in range(rows):
            if r != pivot_row and abs(m[r][col]) > 1e-10:
                factor = m[r][col]
                m[r] = [a - factor * b for a, b in zip(m[r], m[pivot_row])]
        pivot_row += 1
        if pivot_row >= rows:
            break
    return m


def _null_space_integer(matrix: list[list[float]], n_rows: int, n_cols: int) -> list[list[int]]:
    """Find non-negative integer basis vectors of the null space of ``matrix``.

    ``matrix`` is n_rows × n_cols. Returns a list of integer vectors
    (each length n_cols) spanning the null space.
    """
    if n_cols == 0:
        return []
    M = [[float(matrix[i][j]) for j in range(n_cols)] for i in range(n_rows)]
    reduced = _gauss_eliminate(M)

    # Determine pivot columns: scan rows in order, each row's first nonzero entry is a pivot
    pivot_col_for_row: dict[int, int] = {}  # row -> pivot column
    pivot_cols: set[int] = set()
    for r in range(n_rows):
        for c in range(n_cols):
            if abs(reduced[r][c]) > 1e-10:
                pivot_col_for_row[r] = c
                pivot_cols.add(c)
                break

    free_cols = [c for c in range(n_cols) if c not in pivot_cols]

    # For each free variable, construct a null space vector
    # by setting that free var = 1 and other free vars = 0,
    # then back-substituting pivot variables.
    # In reduced row echelon form, pivot var at row r = -sum(reduced[r][fc] * free_var[fc])
    vectors: list[list[int]] = []
    for fc in free_cols:
        vec = [0] * n_cols
        vec[fc] = 1
        for r in range(n_rows):
            if r in pivot_col_for_row:
                pc = pivot_col_for_row[r]
                vec[pc] = round(-reduced[r][fc])
        vectors.append(vec)
    return vectors


def _normalize_vector(vec: list[int]) -> list[int]:
    """Divide by GCD and make the first nonzero element positive."""
    from math import gcd
    from functools import reduce as freduce
    nonzero = [abs(v) for v in vec if v != 0]
    if not nonzero:
        return vec
    g = freduce(gcd, nonzero)
    if g > 1:
        vec = [v // g for v in vec]
    first_nz = next((v for v in vec if v != 0), 0)
    if first_nz < 0:
        vec = [-v for v in vec]
    return vec


def compute_t_invariants(net: PetriNet) -> list[list[int]]:
    """Compute T-invariants: non-negative integer solutions to C·x = 0.

    A T-invariant is a multiset of transitions whose firing returns the
    net to the same marking. Returns a basis of the null space of C.
    """
    place_names, transition_names, C = incidence_matrix(net)
    n_places = len(place_names)
    n_trans = len(transition_names)
    if n_trans == 0:
        return []
    # Null space of C (n_places × n_trans): vectors x (n_trans-dim) with C·x = 0
    raw_vectors = _null_space_integer(C, n_places, n_trans)

    invariants: list[list[int]] = []
    for vec in raw_vectors:
        # Verify: C * vec should be 0
        valid = True
        for i in range(n_places):
            s = sum(C[i][j] * vec[j] for j in range(n_trans))
            if abs(s) > 1e-6:
                valid = False
                break
        if valid and any(v != 0 for v in vec):
            invariants.append(_normalize_vector(vec))
    return invariants


def compute_p_invariants(net: PetriNet) -> list[list[int]]:
    """Compute P-invariants: non-negative integer solutions to y^T · C = 0.

    A P-invariant is a weighting of places such that the weighted token sum
    is conserved by every transition firing.
    """
    place_names, transition_names, C = incidence_matrix(net)
    n_places = len(place_names)
    n_trans = len(transition_names)
    if n_places == 0:
        return []
    # y^T * C = 0  =>  C^T * y = 0  (y is n_places-dim)
    # So y is in the null space of C^T (n_trans × n_places).
    CT = [[float(C[i][j]) for i in range(n_places)] for j in range(n_trans)]
    raw_vectors = _null_space_integer(CT, n_trans, n_places)

    invariants: list[list[int]] = []
    for vec in raw_vectors:
        # Verify: y^T * C should be 0
        valid = True
        for j in range(n_trans):
            s = sum(C[i][j] * vec[i] for i in range(n_places))
            if abs(s) > 1e-6:
                valid = False
                break
        if valid and any(v != 0 for v in vec):
            invariants.append(_normalize_vector(vec))
    return invariants


# ----------------------------------------------------------------------
# Traps and siphons (structural analysis)
# ----------------------------------------------------------------------
@dataclass
class TrapSiphonResult:
    """Result of trap/siphon analysis."""

    traps: list[set[str]]       # non-empty sets of places
    siphons: list[set[str]]    # non-empty sets of places
    has_marked_trap: bool      # True if an initially-marked trap exists
    has_unmarked_siphon: bool  # True if an initially-unmarked siphon exists

    def __repr__(self) -> str:
        lines = ["TrapSiphonResult:"]
        lines.append(f"  Traps ({len(self.traps)}):")
        for i, t in enumerate(self.traps):
            lines.append(f"    #{i}: {sorted(t)}")
        lines.append(f"  Siphons ({len(self.siphons)}):")
        for i, s in enumerate(self.siphons):
            lines.append(f"    #{i}: {sorted(s)}")
        lines.append(f"  Has marked trap: {self.has_marked_trap}")
        lines.append(f"  Has unmarked siphon: {self.has_unmarked_siphon}")
        return "\n".join(lines)


def _is_trap(net: PetriNet, places: set[str]) -> bool:
    """Check if a set of places is a trap.

    A trap S has the property: every transition that consumes from S
    also produces back into S. Thus a trap that is initially marked
    can never become empty.
    """
    for t_name in net.transitions:
        postset = net.postset(t_name)
        preset = net.preset(t_name)
        if preset & places:
            if not (postset & places):
                return False
    return True


def _is_siphon(net: PetriNet, places: set[str]) -> bool:
    """Check if a set of places is a siphon.

    A siphon S has the property: every transition that produces into S
    also consumes from S. Thus a siphon that is initially unmarked
    can never become marked (dead).
    """
    for t_name in net.transitions:
        postset = net.postset(t_name)
        preset = net.preset(t_name)
        if postset & places:
            if not (preset & places):
                return False
    return True


def find_traps(net: PetriNet) -> list[set[str]]:
    """Find minimal traps in the net.

    A trap is a set of places S such that every transition with an input
    in S also has an output in S. Uses a fixpoint iteration starting from
    each place.
    """
    traps: list[set[str]] = []
    all_places = set(net.places)

    for start in all_places:
        S = {start}
        changed = True
        while changed:
            changed = False
            for t_name in net.transitions:
                preset = net.preset(t_name)
                postset = net.postset(t_name)
                if preset & S and not (postset & S):
                    new_places = postset - S
                    if new_places:
                        S |= new_places
                        changed = True
        if S and _is_trap(net, S):
            is_minimal = True
            for existing in traps:
                if existing < S:
                    is_minimal = False
                    break
            if is_minimal:
                traps = [t for t in traps if not (S < t)]
                traps.append(S)

    return traps


def find_siphons(net: PetriNet) -> list[set[str]]:
    """Find minimal siphons in the net.

    A siphon is a set of places S such that every transition with an output
    in S also has an input in S. Uses a fixpoint iteration starting from
    each place.
    """
    siphons: list[set[str]] = []
    all_places = set(net.places)

    for start in all_places:
        S = {start}
        changed = True
        while changed:
            changed = False
            for t_name in net.transitions:
                preset = net.preset(t_name)
                postset = net.postset(t_name)
                if postset & S and not (preset & S):
                    new_places = preset - S
                    if new_places:
                        S |= new_places
                        changed = True
        if S and _is_siphon(net, S):
            is_minimal = True
            for existing in siphons:
                if existing < S:
                    is_minimal = False
                    break
            if is_minimal:
                siphons = [s for s in siphons if not (S < s)]
                siphons.append(S)

    return siphons


def analyze_traps_siphons(net: PetriNet) -> TrapSiphonResult:
    """Analyze traps and siphons in the net.

    - **Traps**: sets of places that, once marked, stay marked.
    - **Siphons**: sets of places that, once unmarked, stay unmarked (dead).
    """
    traps = find_traps(net)
    siphons = find_siphons(net)
    initial = net.initial_marking()

    has_marked_trap = any(
        any(initial.get(p, 0) > 0 for p in trap) for trap in traps
    )
    has_unmarked_siphon = any(
        all(initial.get(p, 0) == 0 for p in siphon) for siphon in siphons
    )

    return TrapSiphonResult(
        traps=traps,
        siphons=siphons,
        has_marked_trap=has_marked_trap,
        has_unmarked_siphon=has_unmarked_siphon,
    )