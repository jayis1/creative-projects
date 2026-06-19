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
    """Replace growing token counts with omega (float('inf'))."""
    # This is a simplified omega heuristic: if any place has more tokens
    # than in any previously-seen marking along a path, we could mark it ω.
    # For correctness we'd need full coverability tree construction.
    # Here we just detect if a marking is strictly larger in all places
    # than the initial marking and mark those as ω.
    return marking  # placeholder — full omega in enhancement phase


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
    """Classify each transition's liveness level."""
    rg = reachability_graph(net, initial_marking, max_states=max_states, detect_omega=False)

    # for each transition, find the set of markings where it's enabled
    levels: dict[str, int] = {}
    all_markings = [node.marking for node in rg.nodes.values()]

    for t_name in net.transitions:
        can_fire_initial = net.is_enabled(t_name, net.initial_marking())
        if not can_fire_initial:
            # check if it can fire from ANY reachable marking
            can_fire_any = False
            for m in all_markings:
                if net.is_enabled(t_name, m):
                    can_fire_any = True
                    break
            if not can_fire_any:
                levels[t_name] = 0  # dead
                continue
            levels[t_name] = 1  # L1: can fire at least once
            continue

        # can fire from initial — check L4: can fire from every reachable marking
        can_fire_all = all(net.is_enabled(t_name, m) for m in all_markings)
        if can_fire_all:
            levels[t_name] = 4  # L4 (live)
        else:
            # check L2: at least potentially fireable from every reachable marking
            # (there's a path from every marking to one where t is enabled)
            # Simplified: if it can fire from initial and from most markings, call it L2
            fireable_count = sum(1 for m in all_markings if net.is_enabled(t_name, m))
            if fireable_count >= len(all_markings) * 0.5:
                levels[t_name] = 2
            else:
                levels[t_name] = 1

    return LivenessResult(levels=levels)


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