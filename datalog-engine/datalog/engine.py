"""Datalog evaluation engine.

Implements:
* Bottom-up evaluation with the **semi-naive** delta strategy for
  efficiency on recursive rules.
* **Stratified negation** — rules with ``not`` are evaluated in a
  later stratum once all the predicates they negate have been fully
  derived.
* **Join evaluation** using hash-table indexing on shared variables.
* Built-in comparison/relational predicates (``<``, ``>``, ``<=``,
  ``>=``, ``!=``) and a small standard library of built-ins.
* Cycle detection in rule dependency graph → raises on non-stratifiable
  programs.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from .ast import Atom, Constant, Fact, Literal, Query, Rule, Term, Variable
from .parser import parse


# A binding is a mapping from variable name → Constant value.
Binding = Dict[str, Constant]

# A relation is a set of tuples (each tuple is a tuple of Constants).
Relation = Set[Tuple[Constant, ...]]


class DatalogError(Exception):
    pass


class StratificationError(DatalogError):
    pass


class SafetyError(DatalogError):
    pass


# ---------------------------------------------------------------------------
# Index helpers
# ---------------------------------------------------------------------------


def _index_key(arity: int, tuple_: Tuple[Constant, ...], positions: Tuple[int, ...]) -> Tuple[Constant, ...]:
    return tuple(tuple_[p] for p in positions)


class Relation_:
    """A stored relation with optional hash indexes for fast joins."""

    __slots__ = ("arity", "tuples", "_indexes")

    def __init__(self, arity: int) -> None:
        self.arity = arity
        self.tuples: Relation = set()
        self._indexes: Dict[Tuple[int, ...], Dict[Tuple[Constant, ...], List[Tuple[Constant, ...]]]] = {}

    def add(self, tup: Tuple[Constant, ...]) -> bool:
        if len(tup) != self.arity:
            raise DatalogError(f"arity mismatch: expected {self.arity}, got {len(tup)}")
        if tup in self.tuples:
            return False
        self.tuples.add(tup)
        for positions, idx in self._indexes.items():
            idx.setdefault(_index_key(self.arity, tup, positions), []).append(tup)
        return True

    def ensure_index(self, positions: Tuple[int, ...]) -> None:
        if positions in self._indexes:
            return
        idx: Dict[Tuple[Constant, ...], List[Tuple[Constant, ...]]] = defaultdict(list)
        for tup in self.tuples:
            idx[_index_key(self.arity, tup, positions)].append(tup)
        self._indexes[positions] = idx

    def lookup(self, positions: Tuple[int, ...], key: Tuple[Constant, ...]) -> List[Tuple[Constant, ...]]:
        self.ensure_index(positions)
        return self._indexes[positions].get(key, [])

    def __len__(self) -> int:
        return len(self.tuples)

    def __contains__(self, tup: Tuple[Constant, ...]) -> bool:
        return tup in self.tuples

    def __iter__(self):
        return iter(self.tuples)


# ---------------------------------------------------------------------------
# Built-in predicates
# ---------------------------------------------------------------------------


_BUILTIN_BINARY = {
    "<": lambda a, b: a < b,
    ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b,
    ">=": lambda a, b: a >= b,
    "!=": lambda a, b: a != b,
    "==": lambda a, b: a == b,
}


def _is_builtin(pred: str) -> bool:
    return pred in _BUILTIN_BINARY


def _eval_builtin(pred: str, terms: Tuple[Term, ...], binding: Binding) -> bool:
    """Evaluate a built-in binary comparison. Both terms must be bound
    constants at evaluation time."""
    if pred not in _BUILTIN_BINARY:
        return False
    if len(terms) != 2:
        raise DatalogError(f"builtin {pred} requires 2 arguments, got {len(terms)}")
    vals: List[Any] = []
    for t in terms:
        if isinstance(t, Constant):
            vals.append(t.value)
        elif isinstance(t, Variable):
            if t.name not in binding:
                return False  # not yet bound → cannot evaluate; treat as fail
            vals.append(binding[t.name].value)
        else:
            return False
    try:
        return _BUILTIN_BINARY[pred](vals[0], vals[1])
    except TypeError:
        return False


# ---------------------------------------------------------------------------
# Unification & join helpers
# ---------------------------------------------------------------------------


def _resolve(term: Term, binding: Binding) -> Optional[Constant]:
    """Resolve a term to a constant given a binding, or None if it's a
    variable not yet bound."""
    if isinstance(term, Constant):
        return term
    if isinstance(term, Variable):
        return binding.get(term.name)
    return None


def _unify_atom(atom: Atom, tup: Tuple[Constant, ...], binding: Binding) -> Optional[Binding]:
    """Try to unify an atom's terms with a concrete tuple under the
    current binding. Returns a new binding (extended) or None on
    failure."""
    if atom.arity != len(tup):
        return None
    b: Binding = dict(binding)
    for term, val in zip(atom.terms, tup):
        if isinstance(term, Constant):
            if term != val:
                return None
        elif isinstance(term, Variable):
            if term.name in b:
                if b[term.name] != val:
                    return None
            else:
                b[term.name] = val
        else:
            return None
    return b


def _atom_to_tuple(atom: Atom, binding: Binding) -> Optional[Tuple[Constant, ...]]:
    """Ground an atom using a binding → tuple of constants, or None if
    any variable is unbound."""
    out: List[Constant] = []
    for term in atom.terms:
        c = _resolve(term, binding)
        if c is None:
            return None
        out.append(c)
    return tuple(out)


def _var_positions(atom: Atom, vars_of_interest: Iterable[str]) -> Tuple[int, ...]:
    vs = set(vars_of_interest)
    return tuple(i for i, t in enumerate(atom.terms) if isinstance(t, Variable) and t.name in vs)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class Engine:
    """A Datalog deductive database.

    Typical usage::

        e = Engine()
        e.add_source('''
            edge(a, b). edge(b, c). edge(c, d).
            path(X, Y) :- edge(X, Y).
            path(X, Y) :- edge(X, Z), path(Z, Y).
        ''')
        result = e.query('path(a, Y)')
        for r in result:
            print(r)
    """

    def __init__(self) -> None:
        # predicate name → Relation_
        self._edb: Dict[str, Relation_] = {}
        self._idb: Dict[str, Relation_] = {}
        self._rules: List[Rule] = []
        self._pred_arity: Dict[str, int] = {}
        self._derived: Set[str] = set()  # predicates that have rules
        self._strata: Optional[List[List[Rule]]] = None
        self._dirty = True  # need to re-evaluate

    # -- public API --

    def add_source(self, src: str) -> None:
        """Parse and load a Datalog program string (facts, rules, queries).
        Queries in the source are ignored (use :meth:`query`)."""
        prog = parse(src)
        self._load_program(prog)

    def add_fact(self, predicate: str, *args: Any) -> None:
        """Add a single fact programmatically."""
        consts = tuple(_to_constant(a) for a in args)
        self._get_relation(predicate, len(consts), edb=True).add(consts)
        self._dirty = True

    def add_rule(self, rule: Rule) -> None:
        if not rule.is_safe():
            raise SafetyError(f"unsafe rule: {rule}")
        self._rules.append(rule)
        self._derived.add(rule.head.predicate)
        self._pred_arity[rule.head.predicate] = rule.head.arity
        self._dirty = True

    def query(self, q: str) -> List[Dict[str, Any]]:
        """Evaluate a query and return a list of bindings (dicts mapping
        variable name → Python value).

        Accepts either ``?- p(X, c).`` form or a bare atom ``p(X, c)``."""
        q = q.strip()
        if q.startswith("?-"):
            prog = parse(q)
            if not prog.queries:
                raise DatalogError("no query found in input")
            atom = prog.queries[0].atom
        else:
            # Parse as a bare atom: wrap in ?- ... so the parser treats it
            # as a query.
            prog = parse("?- " + q)
            if not prog.queries:
                raise DatalogError("no query found in input")
            atom = prog.queries[0].atom
        return self.query_atom(atom)

    def query_atom(self, atom: Atom) -> List[Dict[str, Any]]:
        """Evaluate a query given as an :class:`Atom`."""
        self._evaluate()
        rel = self._get_relation_eval(atom.predicate)
        if rel is None or rel.arity != atom.arity:
            return []
        results: List[Dict[str, Any]] = []
        seen: Set[Tuple] = set()
        for tup in rel:
            b = _unify_atom(atom, tup, {})
            if b is None:
                continue
            key = tuple(sorted(b.items()))
            if key in seen:
                continue
            seen.add(key)
            results.append({k: v.value for k, v in b.items()})
        return results

    def relation(self, predicate: str) -> List[Tuple[Any, ...]]:
        """Return the current extension of a predicate as a list of
        tuples of Python values (fully evaluated)."""
        self._evaluate()
        rel = self._get_relation_eval(predicate)
        if rel is None:
            return []
        return [tuple(c.value for c in tup) for tup in rel]

    def predicates(self) -> List[str]:
        return sorted(set(self._edb) | set(self._idb) | self._derived)

    # -- internal: loading --

    def _load_program(self, prog) -> None:
        for fact in prog.facts:
            consts = tuple(t for t in fact.atom.terms if isinstance(t, Constant))
            if len(consts) != fact.atom.arity:
                raise DatalogError(f"fact {fact.atom} has non-constant terms")
            self._get_relation(fact.atom.predicate, fact.atom.arity, edb=True).add(consts)
        for rule in prog.rules:
            if not rule.is_safe():
                raise SafetyError(f"unsafe rule: {rule}")
            self._rules.append(rule)
            self._derived.add(rule.head.predicate)
            self._pred_arity[rule.head.predicate] = rule.head.arity
        self._dirty = True

    def _get_relation(self, pred: str, arity: int, edb: bool = False) -> Relation_:
        store = self._edb if edb else self._idb
        if pred not in store:
            store[pred] = Relation_(arity)
            self._pred_arity[pred] = arity
        rel = store[pred]
        if rel.arity != arity:
            raise DatalogError(f"predicate {pred} used with arity {arity} but already declared with arity {rel.arity}")
        return rel

    def _get_relation_eval(self, pred: str) -> Optional[Relation_]:
        if pred in self._idb:
            return self._idb[pred]
        if pred in self._edb:
            return self._edb[pred]
        return None

    # -- internal: stratification --

    def _stratify(self) -> List[List[Rule]]:
        """Compute rule strata for stratified negation.

        A rule head(H) :- ... not B ... means B must be in a strictly
        lower stratum than H. Build a dependency graph with positive
        and negative edges, then compute SCCs and topologically sort;
        if a negative edge lies within an SCC, the program is not
        stratifiable.
        """
        # Build predicate → set of rules with that head
        head_to_rules: Dict[str, List[Rule]] = defaultdict(list)
        for r in self._rules:
            head_to_rules[r.head.predicate].append(r)

        predicates = set(self._derived) | set(self._edb)
        # dependency edges: (dependent_pred, depends_on_pred, is_negative)
        pos_edges: Dict[str, Set[str]] = defaultdict(set)
        neg_edges: Dict[str, Set[str]] = defaultdict(set)
        for r in self._rules:
            h = r.head.predicate
            for lit in r.body:
                if _is_builtin(lit.atom.predicate):
                    continue
                if lit.positive:
                    pos_edges[h].add(lit.atom.predicate)
                else:
                    neg_edges[h].add(lit.atom.predicate)

        # Tarjan's SCC
        sccs = _tarjan_scc(predicates, pos_edges, neg_edges)

        # Check: no negative edge within an SCC
        for scc in sccs:
            scc_set = set(scc)
            for p in scc_set:
                for neg_dep in neg_edges.get(p, ()):
                    if neg_dep in scc_set:
                        raise StratificationError(
                            f"program is not stratifiable: negative edge {p} -> {neg_dep} within same SCC {scc_set}"
                        )

        # Assign stratum = position in topological order of SCC DAG
        # Build SCC DAG (positive edges only for ordering — negative edges
        # already guaranteed to be cross-SCC)
        scc_of: Dict[str, int] = {}
        for i, scc in enumerate(sccs):
            for p in scc:
                scc_of[p] = i
        # edges between SCCs — reversed so that dependencies get lower
        # stratum numbers than their dependents.
        scc_adj: Dict[int, Set[int]] = defaultdict(set)
        for p in predicates:
            for dep in pos_edges.get(p, ()):
                if scc_of[dep] != scc_of[p]:
                    scc_adj[scc_of[dep]].add(scc_of[p])
            for dep in neg_edges.get(p, ()):
                if scc_of[dep] != scc_of[p]:
                    scc_adj[scc_of[dep]].add(scc_of[p])

        # Topological order: a stratum must come after all its dependencies.
        # We want stratum index = longest path from a leaf.
        order = _topo_sort_sccs(len(sccs), scc_adj)

        # Map predicate → stratum number
        pred_stratum: Dict[str, int] = {}
        for i, scc in enumerate(sccs):
            for p in scc:
                pred_stratum[p] = order[i]

        # Group rules by stratum
        max_s = max(order.values()) if order else 0
        strata: List[List[Rule]] = [[] for _ in range(max_s + 1)]
        for r in self._rules:
            s = pred_stratum[r.head.predicate]
            strata[s].append(r)
        return strata

    # -- internal: evaluation --

    def _evaluate(self) -> None:
        if not self._dirty:
            return
        self._strata = self._stratify()
        # Reset IDB relations
        for pred in self._derived:
            arity = self._pred_arity[pred]
            self._idb[pred] = Relation_(arity)
        for stratum in self._strata:
            self._eval_stratum(stratum)
        self._dirty = False

    def _eval_stratum(self, rules: List[Rule]) -> None:
        """Evaluate one stratum using semi-naive evaluation.

        Since within a stratum there's no negation, we can iterate to
        fixpoint using delta relations."""
        if not rules:
            return
        # Separate rules into those that only use EDB/already-computed
        # predicates (non-recursive in this stratum) and those that are
        # recursive. Semi-naive handles both uniformly.

        # Predicates defined in this stratum
        stratum_preds = {r.head.predicate for r in rules}

        # Initialize IDB relations for stratum preds as empty
        for pred in stratum_preds:
            if pred not in self._idb:
                self._idb[pred] = Relation_(self._pred_arity[pred])
            else:
                # clear
                self._idb[pred] = Relation_(self._pred_arity[pred])

        # Delta relations: pred → Relation_ of tuples added in last iteration
        deltas: Dict[str, Relation_] = {
            pred: Relation_(self._pred_arity[pred]) for pred in stratum_preds
        }

        # First pass: naive evaluation to bootstrap
        changed = False
        for pred in stratum_preds:
            new_tuples = self._eval_rules_for_pred(pred, rules, {})
            rel = self._idb[pred]
            for tup in new_tuples:
                if rel.add(tup):
                    deltas[pred].add(tup)
                    changed = True

        if not changed:
            return

        # Semi-naive: iterate until no new tuples
        while True:
            new_deltas: Dict[str, Relation_] = {
                pred: Relation_(self._pred_arity[pred]) for pred in stratum_preds
            }
            any_new = False
            for pred in stratum_preds:
                # For each rule with head pred, evaluate using at least
                # one delta body literal.
                for rule in rules:
                    if rule.head.predicate != pred:
                        continue
                    new_tuples = self._eval_rule_seminaive(rule, deltas)
                    rel = self._idb[pred]
                    for tup in new_tuples:
                        if rel.add(tup):
                            new_deltas[pred].add(tup)
                            any_new = True
            deltas = new_deltas
            if not any_new:
                break

    def _eval_rules_for_pred(self, pred: str, rules: List[Rule], deltas: Dict[str, Relation_]) -> Set[Tuple[Constant, ...]]:
        """Naive evaluation: evaluate all rules with head pred using
        current full relations."""
        out: Set[Tuple[Constant, ...]] = set()
        for rule in rules:
            if rule.head.predicate != pred:
                continue
            for binding in self._eval_body(rule.body, {}, deltas):
                tup = _atom_to_tuple(rule.head, binding)
                if tup is not None:
                    out.add(tup)
        return out

    def _eval_rule_seminaive(self, rule: Rule, deltas: Dict[str, Relation_]) -> Set[Tuple[Constant, ...]]:
        """Evaluate a rule in semi-naive style: for each positive body
        literal that refers to a stratum predicate, substitute the delta
        of that predicate in turn; evaluate other literals against full
        relations."""
        out: Set[Tuple[Constant, ...]] = set()
        stratum_preds = set(deltas)

        # Find positive body literals whose predicate is in the current stratum
        delta_positions = [
            i for i, lit in enumerate(rule.body)
            if lit.positive and lit.atom.predicate in stratum_preds
        ]

        if not delta_positions:
            # Rule doesn't depend on stratum preds (shouldn't happen if
            # stratified correctly, but handle gracefully): full eval
            for binding in self._eval_body(rule.body, {}, deltas):
                tup = _atom_to_tuple(rule.head, binding)
                if tup is not None:
                    out.add(tup)
            return out

        for di in delta_positions:
            delta = deltas[rule.body[di].atom.predicate]
            if len(delta) == 0:
                continue
            # Evaluate body with literal di restricted to delta tuples
            for binding in self._eval_body(rule.body, {}, deltas, force_delta_idx=di, delta_rel=delta):
                tup = _atom_to_tuple(rule.head, binding)
                if tup is not None:
                    out.add(tup)
        return out

    def _eval_body(
        self,
        body: List[Literal],
        binding: Binding,
        deltas: Dict[str, Relation_],
        force_delta_idx: Optional[int] = None,
        delta_rel: Optional[Relation_] = None,
    ) -> List[Binding]:
        """Evaluate a rule body (list of literals) returning all
        satisfying bindings.

        If ``force_delta_idx`` is set, the literal at that index is
        evaluated against ``delta_rel`` instead of the full relation
        (semi-naive)."""
        return self._eval_body_from(body, 0, [binding], deltas, force_delta_idx, delta_rel)

    def _eval_body_from(
        self,
        body: List[Literal],
        idx: int,
        bindings: List[Binding],
        deltas: Dict[str, Relation_],
        force_delta_idx: Optional[int],
        delta_rel: Optional[Relation_],
    ) -> List[Binding]:
        if idx >= len(body):
            return bindings
        lit = body[idx]
        results: List[Binding] = []
        use_delta = (force_delta_idx == idx)
        for b in bindings:
            results.extend(self._eval_literal(lit, b, deltas, use_delta, delta_rel))
        return self._eval_body_from(body, idx + 1, results, deltas, force_delta_idx, delta_rel)

    def _eval_literal(
        self,
        lit: Literal,
        binding: Binding,
        deltas: Dict[str, Relation_],
        use_delta: bool,
        delta_rel: Optional[Relation_],
    ) -> List[Binding]:
        pred = lit.atom.predicate

        # Built-in predicates
        if _is_builtin(pred):
            if lit.positive:
                if _eval_builtin(pred, lit.atom.terms, binding):
                    return [binding]
                return []
            else:
                # Negation of a built-in comparison
                if not _eval_builtin(pred, lit.atom.terms, binding):
                    return [binding]
                return []

        # Select relation source
        if use_delta and delta_rel is not None:
            rel = delta_rel
        else:
            rel = self._get_relation_eval(pred)
        if rel is None:
            if lit.positive:
                return []
            else:
                # not (empty relation) → succeeds with current binding
                return [binding]

        if lit.positive:
            return self._eval_positive(lit.atom, rel, binding)
        else:
            # Negated literal: check that no tuple matches under binding.
            # All variables in the negated atom must be bound (safety).
            matches = self._eval_positive(lit.atom, rel, binding)
            if matches:
                return []
            return [binding]

    def _eval_positive(self, atom: Atom, rel: Relation_, binding: Binding) -> List[Binding]:
        """Evaluate a positive atom against a relation, returning
        extended bindings. Uses index joins when possible."""
        # If the atom is ground, just check membership.
        if atom.is_ground():
            tup = tuple(t for t in atom.terms if isinstance(t, Constant))
            if tup in rel:
                return [binding]
            return []

        # Find bound variables (in binding) and their positions in atom
        bound_positions: List[int] = []
        bound_vals: List[Constant] = []
        unbound_var_positions: List[int] = []
        for i, term in enumerate(atom.terms):
            if isinstance(term, Constant):
                bound_positions.append(i)
                bound_vals.append(term)
            elif isinstance(term, Variable):
                if term.name in binding:
                    bound_positions.append(i)
                    bound_vals.append(binding[term.name])
                else:
                    unbound_var_positions.append(i)

        candidates: Iterable[Tuple[Constant, ...]]
        if bound_positions:
            # Use index on bound positions
            positions = tuple(bound_positions)
            key = tuple(bound_vals)
            candidates = rel.lookup(positions, key)
        else:
            candidates = rel.tuples

        results: List[Binding] = []
        for tup in candidates:
            b = _unify_atom(atom, tup, binding)
            if b is not None:
                results.append(b)
        return results


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_constant(v: Any) -> Constant:
    if isinstance(v, Constant):
        return v
    return Constant(v)


def _tarjan_scc(nodes: Set[str], pos_edges, neg_edges) -> List[List[str]]:
    """Tarjan's strongly-connected-components algorithm."""
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

    def strongconnect(v: str) -> None:
        index[v] = index_counter[0]
        lowlink[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack.add(v)
        for w in all_neighbors(v):
            if w not in index:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], index[w])
        if lowlink[v] == index[v]:
            scc: List[str] = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                scc.append(w)
                if w == v:
                    break
            result.append(scc)

    for v in sorted(nodes):
        if v not in index:
            strongconnect(v)
    return result


def _topo_sort_sccs(n_sccs: int, adj: Dict[int, Set[int]]) -> Dict[int, int]:
    """Return mapping scc_index → stratum_number (0 = lowest).

    Stratum = longest path from a source SCC in the DAG."""
    # reverse adjacency for longest-path
    in_deg = [0] * n_sccs
    for u in range(n_sccs):
        for v in adj.get(u, ()):
            in_deg[v] += 1
    # Kahn-like with levels
    level = [0] * n_sccs
    queue = [i for i in range(n_sccs) if in_deg[i] == 0]
    processed = 0
    # We need longest path: process in topological order, relax.
    # Use Kahn's algorithm tracking levels.
    q = list(queue)
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
        raise StratificationError("cycle in positive dependency graph (non-terminating recursion)")
    return {i: level[i] for i in range(n_sccs)}