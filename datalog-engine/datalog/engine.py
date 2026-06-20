"""Datalog evaluation engine.

This is the core of the Datalog deductive database.  It coordinates:

* **Loading** facts and rules (from source strings, files, or JSON).
* **Stratification** — computing rule strata for stratified negation.
* **Semi-naive bottom-up evaluation** — evaluating rules to a fixpoint
  using delta relations for efficiency.
* **Joins** — hash-indexed joins via :class:`~datalog.evaluation.BodyEvaluator`.
* **Built-in predicates** — comparisons, arithmetic, string, type checks.
* **Aggregation** — count/sum/min/max/avg over grouped bindings.
* **Retraction** — removing facts or rules with automatic re-evaluation.
* **JSON I/O** — serializing and deserializing engine state.
* **Introspection** — explaining predicates, listing rules and facts.

The public API is the :class:`Engine` class.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from .aggregation import eval_aggregate_rule, is_aggregate_rule
from .ast import Atom, Constant, Fact, Literal, Query, Rule, Term, Variable
from .builtins import all_builtin_names, is_builtin
from .config import EngineConfig
from .engine_types import Binding
from .errors import DatalogError, SafetyError, StratificationError
from .evaluation import BodyEvaluator, atom_to_tuple, resolve, unify_atom
from .parser import LexError, ParseError, parse
from .relation import Relation_
from .stratification import stratify

logger = logging.getLogger("datalog")


def _to_constant(v: Any) -> Constant:
    """Convert a Python value to a Constant (pass-through if already one)."""
    if isinstance(v, Constant):
        return v
    return Constant(v)


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

    Parameters
    ----------
    config : EngineConfig, optional
        Engine configuration (log level, max iterations, etc.).
    """

    def __init__(self, config: Optional[EngineConfig] = None) -> None:
        self._edb: Dict[str, Relation_] = {}
        self._idb: Dict[str, Relation_] = {}
        self._rules: List[Rule] = []
        self._pred_arity: Dict[str, int] = {}
        self._derived: Set[str] = set()
        self._strata: Optional[List[List[Rule]]] = None
        self._dirty: bool = True
        self._config: EngineConfig = config or EngineConfig()
        self._evaluator: BodyEvaluator = BodyEvaluator(self._get_relation_eval)
        self._iteration_count: int = 0

        if self._config.log_level:
            logging.basicConfig(level=getattr(logging, self._config.log_level, logging.WARNING))

    # ------------------------------------------------------------------ #
    # Public API — loading                                               #
    # ------------------------------------------------------------------ #

    def add_source(self, src: str) -> None:
        """Parse and load a Datalog program string.

        Facts, rules, and queries in the source are loaded. Queries are
        ignored (use :meth:`query` to run queries).
        """
        logger.debug("add_source: %d chars", len(src))
        prog = parse(src)
        self._load_program(prog)

    def add_fact(self, predicate: str, *args: Any) -> None:
        """Add a single base fact programmatically."""
        consts = tuple(_to_constant(a) for a in args)
        self._get_relation(predicate, len(consts), edb=True).add(consts)
        self._dirty = True
        logger.debug("add_fact: %s/%d %s", predicate, len(consts), consts)

    def add_rule(self, rule: Rule) -> None:
        """Add a single rule to the engine.

        Raises
        ------
        SafetyError
            If the rule violates the Datalog safety condition.
        """
        builtins = all_builtin_names()
        arith_builtins = set(all_builtin_names())  # all binding builtins
        if not rule.is_safe(builtins, arith_builtins):
            raise SafetyError(f"unsafe rule: {rule}")
        self._rules.append(rule)
        self._derived.add(rule.head.predicate)
        self._pred_arity[rule.head.predicate] = rule.head.arity
        self._dirty = True
        logger.debug("add_rule: %s", rule)

    def load_file(self, path: str) -> None:
        """Load a Datalog source file."""
        with open(path, "r") as f:
            self.add_source(f.read())

    # ------------------------------------------------------------------ #
    # Public API — querying                                              #
    # ------------------------------------------------------------------ #

    def query(self, q: str) -> List[Dict[str, Any]]:
        """Evaluate a query and return a list of bindings.

        Each binding is a dict mapping variable name → Python value.

        Accepts ``?- p(X, c).`` form or a bare atom ``p(X, c)``.
        """
        q = q.strip()
        if q.startswith("?-"):
            prog = parse(q)
            if not prog.queries:
                raise DatalogError("no query found in input")
            atom = prog.queries[0].atom
        else:
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
            b = unify_atom(atom, tup, {})
            if b is None:
                continue
            key = tuple(sorted(b.items()))
            if key in seen:
                continue
            seen.add(key)
            results.append({k: v.value for k, v in b.items()})
        logger.debug("query %s → %d results", atom, len(results))
        return results

    def relation(self, predicate: str) -> List[Tuple[Any, ...]]:
        """Return the full extension of a predicate as tuples of Python values."""
        self._evaluate()
        rel = self._get_relation_eval(predicate)
        if rel is None:
            return []
        return [tuple(c.value for c in tup) for tup in rel]

    # ------------------------------------------------------------------ #
    # Public API — introspection                                         #
    # ------------------------------------------------------------------ #

    def predicates(self) -> List[str]:
        """Return sorted list of all known predicate names."""
        return sorted(set(self._edb) | set(self._idb) | self._derived)

    def arity(self, predicate: str) -> Optional[int]:
        """Return the arity of a predicate, or None if unknown."""
        return self._pred_arity.get(predicate)

    def rules(self) -> List[Rule]:
        """Return a copy of the list of loaded rules."""
        return list(self._rules)

    def facts(self, predicate: str) -> List[Tuple[Any, ...]]:
        """Return EDB (base) facts for a predicate, excluding derived tuples."""
        rel = self._edb.get(predicate)
        if rel is None:
            return []
        return [tuple(c.value for c in tup) for tup in rel]

    def explain(self, predicate: str) -> str:
        """Return a human-readable explanation of a predicate."""
        self._evaluate()
        lines: List[str] = []
        is_edb = predicate in self._edb
        is_idb = predicate in self._derived
        arity = self._pred_arity.get(predicate, "?")
        lines.append(f"Predicate: {predicate}/{arity}")
        if is_edb and is_idb:
            lines.append("  Type: EDB (base facts) + IDB (derived)")
        elif is_edb:
            lines.append("  Type: EDB (base facts only)")
        elif is_idb:
            lines.append("  Type: IDB (derived)")
        else:
            lines.append("  Type: unknown/undefined")
            return "\n".join(lines)
        if self._strata:
            for i, stratum in enumerate(self._strata):
                for r in stratum:
                    if r.head.predicate == predicate:
                        lines.append(f"  Stratum: {i}")
                        break
        pred_rules = [r for r in self._rules if r.head.predicate == predicate]
        if pred_rules:
            lines.append("  Rules:")
            for r in pred_rules:
                lines.append(f"    {r}")
        rel = self._get_relation_eval(predicate)
        if rel:
            lines.append(f"  Extension: {len(rel)} tuple(s)")
        return "\n".join(lines)

    def stats(self) -> Dict[str, Any]:
        """Return engine statistics."""
        self._evaluate()
        return {
            "predicates": len(self.predicates()),
            "edb_predicates": len(self._edb),
            "idb_predicates": len(self._idb),
            "rules": len(self._rules),
            "total_facts": sum(len(r) for r in self._edb.values()),
            "total_derived": sum(len(r) for r in self._idb.values()),
            "strata": len(self._strata) if self._strata else 0,
            "iterations": self._iteration_count,
        }

    # ------------------------------------------------------------------ #
    # Public API — retraction                                            #
    # ------------------------------------------------------------------ #

    def retract_fact(self, predicate: str, *args: Any) -> bool:
        """Remove a base fact. Returns True if it existed and was removed."""
        consts = tuple(_to_constant(a) for a in args)
        rel = self._edb.get(predicate)
        if rel is None or consts not in rel.tuples:
            return False
        rel.discard(consts)
        self._dirty = True
        logger.debug("retract_fact: %s %s", predicate, consts)
        return True

    def retract_rule(self, rule: Rule) -> bool:
        """Remove a rule. Returns True if removed."""
        if rule in self._rules:
            self._rules.remove(rule)
            head_pred = rule.head.predicate
            if not any(r.head.predicate == head_pred for r in self._rules):
                self._derived.discard(head_pred)
            self._dirty = True
            return True
        return False

    def clear(self) -> None:
        """Remove all facts and rules, resetting the engine."""
        self._edb.clear()
        self._idb.clear()
        self._rules.clear()
        self._pred_arity.clear()
        self._derived.clear()
        self._strata = None
        self._dirty = True
        self._iteration_count = 0

    # ------------------------------------------------------------------ #
    # Public API — JSON I/O                                              #
    # ------------------------------------------------------------------ #

    def to_json(self) -> str:
        """Export all base facts (EDB) and rules as a JSON string.

        Derived (IDB) facts are not exported — they can be recomputed
        from EDB + rules.
        """
        import json
        data: dict = {"facts": {}, "rules": []}
        for pred, rel in sorted(self._edb.items()):
            data["facts"][pred] = {
                "arity": rel.arity,
                "tuples": [
                    [c.value for c in tup]
                    for tup in sorted(
                        rel.tuples,
                        key=lambda t: tuple(str(c.value) for c in t),
                    )
                ],
            }
        for r in self._rules:
            data["rules"].append(str(r))
        return json.dumps(data, indent=2, default=str)

    def from_json(self, json_str: str) -> None:
        """Import facts and rules from a JSON string.

        Existing facts/rules are preserved.
        """
        import json
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise DatalogError(f"invalid JSON: {e}") from e
        if not isinstance(data, dict):
            raise DatalogError("JSON root must be an object")
        for pred, info in data.get("facts", {}).items():
            if not isinstance(info, dict) or "tuples" not in info:
                raise DatalogError(
                    f"invalid fact entry for predicate {pred!r}"
                )
            for tup in info["tuples"]:
                self.add_fact(pred, *tup)
        for rule_str in data.get("rules", []):
            try:
                prog = parse(rule_str)
            except (ParseError, LexError) as e:
                raise DatalogError(
                    f"failed to parse rule from JSON: {rule_str!r}: {e}"
                ) from e
            for rule in prog.rules:
                self.add_rule(rule)

    # ------------------------------------------------------------------ #
    # Internal — loading                                                 #
    # ------------------------------------------------------------------ #

    def _load_program(self, prog) -> None:
        for fact in prog.facts:
            consts = tuple(fact.atom.terms)
            if not all(isinstance(t, Constant) for t in consts):
                raise DatalogError(
                    f"fact {fact.atom} has non-constant terms"
                )
            self._get_relation(
                fact.atom.predicate, fact.atom.arity, edb=True
            ).add(consts)
        for rule in prog.rules:
            builtins = all_builtin_names()
            arith_builtins = set(all_builtin_names())
            if not rule.is_safe(builtins, arith_builtins):
                raise SafetyError(f"unsafe rule: {rule}")
            self._rules.append(rule)
            self._derived.add(rule.head.predicate)
            self._pred_arity[rule.head.predicate] = rule.head.arity
        self._dirty = True

    def _get_relation(
        self, pred: str, arity: int, edb: bool = False
    ) -> Relation_:
        store = self._edb if edb else self._idb
        if pred not in store:
            store[pred] = Relation_(arity)
            self._pred_arity[pred] = arity
        rel = store[pred]
        if rel.arity != arity:
            raise DatalogError(
                f"predicate {pred} used with arity {arity} but already "
                f"declared with arity {rel.arity}"
            )
        return rel

    def _get_relation_eval(self, pred: str) -> Optional[Relation_]:
        if pred in self._idb:
            return self._idb[pred]
        if pred in self._edb:
            return self._edb[pred]
        return None

    # ------------------------------------------------------------------ #
    # Internal — evaluation                                              #
    # ------------------------------------------------------------------ #

    def _evaluate(self) -> None:
        if not self._dirty:
            return
        logger.debug("evaluating (dirty=True)")
        self._strata = self._stratify()
        # Reset IDB relations
        for pred in self._derived:
            arity = self._pred_arity[pred]
            self._idb[pred] = Relation_(arity)
        self._iteration_count = 0
        for stratum in self._strata:
            self._eval_stratum(stratum)
        self._dirty = False
        logger.debug(
            "evaluation complete: %d iterations", self._iteration_count
        )

    def _stratify(self) -> List[List[Rule]]:
        return stratify(self._rules, set(self._edb), self._derived)

    def _eval_stratum(self, rules: List[Rule]) -> None:
        """Evaluate one stratum using semi-naive evaluation."""
        if not rules:
            return

        # Separate aggregate rules from regular rules
        agg_rules = [r for r in rules if is_aggregate_rule(r)]
        regular_rules = [r for r in rules if not is_aggregate_rule(r)]

        stratum_preds = {r.head.predicate for r in rules}

        # Initialize IDB relations for stratum preds.
        # Seed with EDB facts so rules can build on them.
        deltas: Dict[str, Relation_] = {
            pred: Relation_(self._pred_arity[pred]) for pred in stratum_preds
        }
        for pred in stratum_preds:
            rel = Relation_(self._pred_arity[pred])
            self._idb[pred] = rel
            edb_rel = self._edb.get(pred)
            if edb_rel is not None:
                for tup in edb_rel.tuples:
                    rel.add(tup)
                    deltas[pred].add(tup)

        # First pass: naive bootstrap
        changed = False
        for pred in stratum_preds:
            new_tuples = self._eval_rules_for_pred(
                pred, regular_rules, {}
            )
            rel = self._idb[pred]
            for tup in new_tuples:
                if rel.add(tup):
                    deltas[pred].add(tup)
                    changed = True

        has_seeded_deltas = any(len(d) > 0 for d in deltas.values())
        if not changed and not has_seeded_deltas:
            # Still need to evaluate aggregate rules
            if agg_rules:
                self._eval_aggregates(agg_rules)
            return

        # Semi-naive: iterate until fixpoint
        max_iter = self._config.max_iterations
        while True:
            self._iteration_count += 1
            if self._iteration_count > max_iter:
                raise DatalogError(
                    f"exceeded max iterations ({max_iter}); "
                    f"possible non-termination"
                )
            new_deltas: Dict[str, Relation_] = {
                pred: Relation_(self._pred_arity[pred])
                for pred in stratum_preds
            }
            any_new = False
            for pred in stratum_preds:
                for rule in regular_rules:
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

        # Evaluate aggregate rules after the regular rules reach fixpoint
        if agg_rules:
            self._eval_aggregates(agg_rules)

    def _eval_aggregates(self, agg_rules: List[Rule]) -> None:
        """Evaluate aggregate rules against fully-derived relations."""
        for rule in agg_rules:
            new_tuples = eval_aggregate_rule(
                rule, self._evaluator, self._get_relation_eval
            )
            rel = self._idb.get(rule.head.predicate)
            if rel is None:
                rel = Relation_(rule.head.arity)
                self._idb[rule.head.predicate] = rel
                self._pred_arity[rule.head.predicate] = rule.head.arity
            for tup in new_tuples:
                rel.add(tup)

    def _eval_rules_for_pred(
        self,
        pred: str,
        rules: List[Rule],
        deltas: Dict[str, Relation_],
    ) -> Set[Tuple[Constant, ...]]:
        """Naive evaluation: evaluate all rules with head pred."""
        out: Set[Tuple[Constant, ...]] = set()
        for rule in rules:
            if rule.head.predicate != pred:
                continue
            for binding in self._evaluator.eval_body(rule.body, {}, deltas):
                tup = atom_to_tuple(rule.head, binding)
                if tup is not None:
                    out.add(tup)
        return out

    def _eval_rule_seminaive(
        self, rule: Rule, deltas: Dict[str, Relation_]
    ) -> Set[Tuple[Constant, ...]]:
        """Evaluate a rule in semi-naive style."""
        out: Set[Tuple[Constant, ...]] = set()
        stratum_preds = set(deltas)

        delta_positions = [
            i
            for i, lit in enumerate(rule.body)
            if lit.positive
            and lit.atom.predicate in stratum_preds
            and not is_builtin(lit.atom.predicate)
        ]

        if not delta_positions:
            for binding in self._evaluator.eval_body(rule.body, {}, deltas):
                tup = atom_to_tuple(rule.head, binding)
                if tup is not None:
                    out.add(tup)
            return out

        for di in delta_positions:
            delta = deltas[rule.body[di].atom.predicate]
            if len(delta) == 0:
                continue
            for binding in self._evaluator.eval_body(
                rule.body, {}, deltas, force_delta_idx=di, delta_rel=delta
            ):
                tup = atom_to_tuple(rule.head, binding)
                if tup is not None:
                    out.add(tup)
        return out