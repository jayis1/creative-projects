"""Stratification — computing rule strata for stratified negation.

Before evaluation the engine builds a *predicate dependency graph* with
positive and negative edges (from rule-body predicates to rule-head
predicates).  It computes strongly-connected components (SCCs) using
Tarjan's algorithm.  If a negative edge lies within an SCC, the program
is rejected as non-stratifiable.  SCCs are then topologically sorted
into strata, with each stratum assigned a level equal to the longest
path from a source SCC.  Rules are grouped by their head predicate's
stratum.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Set

from .ast import Rule
from .builtins import is_builtin
from .errors import StratificationError


def _tarjan_scc(
    nodes: Set[str],
    pos_edges: Dict[str, Set[str]],
    neg_edges: Dict[str, Set[str]],
) -> List[List[str]]:
    """Tarjan's strongly-connected-components algorithm (iterative).

    An iterative implementation is used instead of the simpler recursive
    one to avoid Python's recursion limit on large dependency graphs.
    """
    index_counter = [0]
    stack: List[str] = []
    lowlink: Dict[str, int] = {}
    index: Dict[str, int] = {}
    on_stack: Set[str] = set()
    result: List[List[str]] = []

    def all_neighbors(n: str):
        for nb in pos_edges.get(n, ()):
            yield nb
        for nb in neg_edges.get(n, ()):
            yield nb

    # Iterative Tarjan using an explicit work stack.
    # Each frame: (node, iterator_over_neighbors)
    for start in sorted(nodes):
        if start in index:
            continue
        work: List = [(start, None)]
        while work:
            v, it = work[-1]
            if it is None:
                # First visit to v
                index[v] = index_counter[0]
                lowlink[v] = index_counter[0]
                index_counter[0] += 1
                stack.append(v)
                on_stack.add(v)
                it = iter(all_neighbors(v))
                work[-1] = (v, it)
            advanced = False
            for w in it:
                if w not in index:
                    work.append((w, None))
                    advanced = True
                    break
                elif w in on_stack:
                    lowlink[v] = min(lowlink[v], index[w])
            if advanced:
                continue
            # All neighbors processed
            if lowlink[v] == index[v]:
                scc: List[str] = []
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    scc.append(w)
                    if w == v:
                        break
                result.append(scc)
            work.pop()
            if work:
                parent = work[-1][0]
                lowlink[parent] = min(lowlink[parent], lowlink[v])
    return result


def _topo_sort_sccs(
    n_sccs: int, adj: Dict[int, Set[int]]
) -> Dict[int, int]:
    """Return mapping scc_index → stratum_number (0 = lowest).

    Uses Kahn's algorithm with level tracking to compute the longest path
    from a source SCC in the DAG (which gives the minimum stratum that
    satisfies all dependencies).
    """
    in_deg = [0] * n_sccs
    for u in range(n_sccs):
        for v in adj.get(u, ()):
            in_deg[v] += 1
    level = [0] * n_sccs
    q = [i for i in range(n_sccs) if in_deg[i] == 0]
    processed = 0
    while q:
        u = q.pop(0)
        processed += 1
        for v in adj.get(u, ()):
            if level[v] < level[u] + 1:
                level[v] = level[u] + 1
            in_deg[v] -= 1
            if in_deg[v] == 0:
                q.append(v)
    if processed != n_sccs:
        raise StratificationError(
            "cycle in positive dependency graph (non-terminating recursion)"
        )
    return {i: level[i] for i in range(n_sccs)}


def stratify(
    rules: List[Rule],
    edb_predicates: Set[str],
    derived_predicates: Set[str],
) -> List[List[Rule]]:
    """Compute rule strata for stratified negation.

    Parameters
    ----------
    rules : list of Rule
        All rules in the program.
    edb_predicates : set of str
        Predicates that have base facts (extensional database).
    derived_predicates : set of str
        Predicates that have at least one defining rule (intensional DB).

    Returns
    -------
    list of list of Rule
        A list of strata (index 0 = lowest), each containing the rules
        whose head predicate belongs to that stratum.

    Raises
    ------
    StratificationError
        If the program is not stratifiable (negative edge within an SCC)
        or if there's a cycle in the positive dependency graph.
    """
    # Build dependency edges: head_predicate → {body_predicates}
    pos_edges: Dict[str, Set[str]] = defaultdict(set)
    neg_edges: Dict[str, Set[str]] = defaultdict(set)
    for r in rules:
        h = r.head.predicate
        for lit in r.body:
            pred = lit.atom.predicate
            if is_builtin(pred):
                continue
            if lit.positive:
                pos_edges[h].add(pred)
            else:
                neg_edges[h].add(pred)

    predicates = derived_predicates | edb_predicates
    sccs = _tarjan_scc(predicates, pos_edges, neg_edges)

    # Check: no negative edge within an SCC
    for scc in sccs:
        scc_set = set(scc)
        for p in scc_set:
            for neg_dep in neg_edges.get(p, ()):
                if neg_dep in scc_set:
                    raise StratificationError(
                        f"program is not stratifiable: negative edge "
                        f"{p} -> {neg_dep} within same SCC {scc_set}"
                    )

    # Assign stratum = position in topological order of SCC DAG
    scc_of: Dict[str, int] = {}
    for i, scc in enumerate(sccs):
        for p in scc:
            scc_of[p] = i

    scc_adj: Dict[int, Set[int]] = defaultdict(set)
    for p in predicates:
        for dep in pos_edges.get(p, ()):
            if scc_of[dep] != scc_of[p]:
                scc_adj[scc_of[dep]].add(scc_of[p])
        for dep in neg_edges.get(p, ()):
            if scc_of[dep] != scc_of[p]:
                scc_adj[scc_of[dep]].add(scc_of[p])

    order = _topo_sort_sccs(len(sccs), scc_adj)

    pred_stratum: Dict[str, int] = {}
    for i, scc in enumerate(sccs):
        for p in scc:
            pred_stratum[p] = order[i]

    max_s = max(order.values()) if order else 0
    strata: List[List[Rule]] = [[] for _ in range(max_s + 1)]
    for r in rules:
        s = pred_stratum[r.head.predicate]
        strata[s].append(r)
    return strata