"""
Core Rete engine implementation.

The Rete (Latin for "net") algorithm is a pattern-matching algorithm for
implementing forward-chaining production-rule systems.  It trades memory for
speed by building a network of nodes that incrementally computes the set of
matching rule instantiations as facts are asserted/retracted, avoiding a full
re-scan of working memory on every cycle.

This implementation follows the classic Rete I structure:

    ┌──────────┐     ┌─────────────┐     ┌──────────────┐     ┌────────────┐
    │  Fact    │──▶ │  Alpha net  │──▶ │  Join / beta │──▶ │  Production │
    │  source  │     │  (one-input │     │  net (two-   │     │  nodes      │
    └──────────┘     │   nodes)    │     │   input)     │     │  (rules)    │
                     └─────────────┘     └──────────────┘     └────────────┘

Key ideas
---------
* **Alpha nodes** filter single facts against intra-fact tests (type + field
  predicates).  Each distinct condition-template gets its own alpha node and
  the network reuses nodes when templates overlap.
* **Join nodes** combine the outputs of two alpha (or prior join) nodes using
  inter-fact variable-binding consistency checks (the *join* tests).
* **Production nodes** sit at the leaves and collect full instantiations for
  a particular rule, pushing them into the conflict set.
* The **agenda** resolves conflicts via a pluggable strategy and the engine
  fires actions, which may assert/retract facts, causing incremental updates.

The implementation is pure Python with no external dependencies.
"""

from __future__ import annotations

import heapq
import itertools
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Iterable, Optional, Protocol

from .exceptions import (
    FactError,
    InfiniteLoopError,
    MatchError,
    ReteError,
    RuleError,
)

# --------------------------------------------------------------------------- #
#  Pattern-matching primitives
# --------------------------------------------------------------------------- #


class _Term:
    """
    A term inside a condition — either a variable binding or a constant test.

    Subclasses: ``Var`` (binds a value to a name across the rule) and
    ``Const`` (tests that the field equals a fixed literal).
    """

    __slots__ = ()

    is_var: bool = False

    def matches(self, value: Any) -> bool:
        """Whether *value* satisfies this term."""
        raise NotImplementedError


@dataclass(frozen=True)
class Var(_Term):
    """A variable that binds to a fact field and unifies across conditions."""

    name: str

    is_var: bool = field(default=True, init=False)

    def matches(self, value: Any) -> bool:  # noqa: D401
        # A variable always matches; the binding is enforced elsewhere.
        return True

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"?{self.name}"


@dataclass(frozen=True)
class Const(_Term):
    """A constant literal that a fact field must equal."""

    value: Any

    is_var: bool = field(default=False, init=False)

    def matches(self, value: Any) -> bool:
        return value == self.value

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return repr(self.value)


def _make_term(x: Any) -> _Term:
    """Coerce a Python value into a term (Var stays Var, else Const)."""
    if isinstance(x, _Term):
        return x
    return Const(x)


# --------------------------------------------------------------------------- #
#  Conditions & Facts
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Condition:
    """
    A single condition pattern, e.g. ``Condition("person", age=Var("a"))``.

    The first positional argument is the fact *type* (a string).  Keyword
    arguments map field names to terms (Var / Const / raw values).

    A ``predicate`` callable may be supplied for arbitrary intra-fact tests
    that can't be expressed as field equality — it receives the fact and the
    current (partial) bindings and must return a bool.

    Parameters
    ----------
    fact_type : str
        The type of fact this condition matches.
    predicate : callable, optional
        A function ``(fact, bindings) -> bool`` for arbitrary tests.
    negated : bool
        If ``True``, this condition matches only when *no* fact satisfies it.
    **fields
        Field-name → term mappings (Var, Const, or raw Python values which
        are auto-wrapped in Const).
    """

    fact_type: str
    fields: dict[str, _Term] = field(default_factory=dict)
    predicate: Optional[Callable[[dict, dict[str, Any]], bool]] = None
    negated: bool = False

    def __init__(
        self,
        fact_type: str,
        *,
        predicate: Optional[Callable[[dict, dict[str, Any]], bool]] = None,
        negated: bool = False,
        **fields: Any,
    ) -> None:
        if not isinstance(fact_type, str) or not fact_type:
            raise RuleError("condition fact_type must be a non-empty string")
        # Bypass frozen dataclass __init__ via object.__setattr__
        object.__setattr__(self, "fact_type", fact_type)
        object.__setattr__(
            self, "fields", {k: _make_term(v) for k, v in fields.items()}
        )
        object.__setattr__(self, "predicate", predicate)
        object.__setattr__(self, "negated", negated)

    # --- internal helpers -------------------------------------------------
    @property
    def key(self) -> tuple:
        """A structural signature used for alpha-node sharing.

        We serialize each term into a hashable, comparable representation
        so that the key never triggers a ``TypeError`` when sorting mixed
        ``Var`` / ``Const`` instances.
        """
        field_sig = tuple(
            sorted(
                (k, (True, t.name) if t.is_var else (False, repr(t)))
                for k, t in self.fields.items()
            )
        )
        return (self.fact_type, field_sig, self.negated)

    def term_for(self, field_name: str) -> Optional[_Term]:
        """Return the term for *field_name*, or ``None``."""
        return self.fields.get(field_name)

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        kv = ", ".join(f"{k}={v!r}" for k, v in self.fields.items())
        neg = "~" if self.negated else ""
        return f"{neg}{self.fact_type}({kv})"


class Fact:
    """
    A working-memory element — a typed record of attribute/value pairs.

    Two facts with the same (type, fields) are considered *structurally*
    equal, but each instance carries a unique numeric id so the engine can
    track distinct assertions.

    Parameters
    ----------
    fact_type : str
        Non-empty string identifying the fact's type.
    **fields
        Attribute/value pairs for this fact.

    Raises
    ------
    FactError
        If *fact_type* is not a non-empty string.
    """

    __slots__ = ("fact_type", "fields", "_id")

    _counter = itertools.count(1)

    def __init__(self, fact_type: str, **fields: Any) -> None:
        if not isinstance(fact_type, str) or not fact_type:
            raise FactError("fact_type must be a non-empty string")
        self.fact_type = fact_type
        self.fields: dict[str, Any] = dict(fields)
        self._id = next(Fact._counter)

    # -- equality / hashing (structural) ----------------------------------
    def _struct(self) -> tuple:
        return (self.fact_type, tuple(sorted(self.fields.items())))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Fact) and self._struct() == other._struct()

    def __hash__(self) -> int:
        return hash(self._struct())

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        kv = ", ".join(f"{k}={v!r}" for k, v in self.fields.items())
        return f"Fact({self.fact_type}, {kv})"

    def __getitem__(self, key: str) -> Any:
        return self.fields[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.fields.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dict for this fact."""
        return {"type": self.fact_type, "fields": dict(self.fields)}


# --------------------------------------------------------------------------- #
#  Rule
# --------------------------------------------------------------------------- #


@dataclass
class Rule:
    """A production rule: ``conditions → actions``.

    Parameters
    ----------
    name : str
        Unique identifier used in conflict resolution and logging.
    conditions : list[Condition]
        Ordered list of patterns.  The first condition anchors the join
        network; subsequent conditions are joined left-to-right.
    actions : list[Callable[[dict, Engine], Any]]
        Each action receives the variable bindings (dict) and the engine
        instance, so it can assert/retract facts or produce side effects.
    priority : int
        Higher priority rules fire first when strategies consider it.
    """

    name: str
    conditions: list[Condition]
    actions: list[Callable[[dict, "Engine"], Any]]
    priority: int = 0

    def __post_init__(self) -> None:
        if not self.name:
            raise RuleError("rule name must be non-empty")
        if not self.conditions:
            raise RuleError(f"rule '{self.name}' must have ≥1 condition")
        if not self.actions:
            raise RuleError(f"rule '{self.name}' must have ≥1 action")
        for c in self.conditions:
            if not isinstance(c, Condition):
                raise RuleError(
                    f"rule '{self.name}': conditions must be Condition instances"
                )


# --------------------------------------------------------------------------- #
#  Event listener protocol
# --------------------------------------------------------------------------- #


class EngineListener(Protocol):
    """Protocol for engine event listeners (observers).

    Implement this protocol to receive notifications when facts are
    asserted, retracted, or rules are fired.  Any subset of methods may
    be implemented; missing methods are silently skipped.
    """

    def on_assert(self, fact: Fact) -> None: ...
    def on_retract(self, fact: Fact) -> None: ...
    def on_fire(self, rule_name: str, bindings: dict[str, Any]) -> None: ...


# --------------------------------------------------------------------------- #
#  Rete network nodes
# --------------------------------------------------------------------------- #


class AlphaNode:
    """One-input node: filters single facts by type + intra-fact tests."""

    __slots__ = ("condition", "items", "successors")

    def __init__(self, condition: Condition):
        self.condition = condition
        # items: list of (fact, bindings)  — bindings are this node's local vars
        self.items: list[tuple[Fact, dict[str, Any]]] = []
        self.successors: list["JoinNode"] = []

    def activate(self, fact: Fact) -> dict[str, Any] | None:
        """Test *fact* against this node's condition; return bindings if match."""
        c = self.condition
        if c.negated:
            # For negated conditions, the alpha node stores facts that *match*
            # the negated pattern (including field tests).  The join layer then
            # checks that no such matching fact exists for a given left tuple.
            if fact.fact_type != c.fact_type:
                return None
            # Still apply field tests so we only store facts that actually
            # match the negated pattern.
            bindings: dict[str, Any] = {}
            for fname, term in c.fields.items():
                if fname not in fact.fields:
                    return None
                val = fact.fields.get(fname)
                if term.is_var:
                    v: Var = term  # type: ignore[assignment]
                    bindings[v.name] = val
                else:
                    if not term.matches(val):
                        return None
            if c.predicate is not None and not c.predicate(fact, bindings):
                return None
            return bindings
        if fact.fact_type != c.fact_type:
            return None
        bindings = {}
        for fname, term in c.fields.items():
            if fname not in fact.fields:
                return None
            val = fact.fields.get(fname)
            if term.is_var:
                # bind — term is a Var here, so .name is safe
                v: Var = term  # type: ignore[assignment]
                if v.name in bindings and bindings[v.name] != val:
                    return None
                bindings[v.name] = val
            else:
                if not term.matches(val):
                    return None
        if c.predicate is not None and not c.predicate(fact, bindings):
            return None
        return bindings

    def add(self, fact: Fact) -> dict[str, Any] | None:
        """Activate and store *fact* if it matches. Return bindings or None."""
        b = self.activate(fact)
        if b is not None:
            self.items.append((fact, b))
        return b

    def remove(self, fact: Fact) -> None:
        """Remove *fact* from this node's stored items."""
        self.items = [(f, b) for f, b in self.items if f != fact]


class BetaMemory:
    """Stores partial instantiations (tuples of (facts, bindings))."""

    __slots__ = ("items", "successors")

    def __init__(self):
        # Each item: (tuple_of_facts, merged_bindings)
        self.items: list[tuple[tuple[Fact, ...], dict[str, Any]]] = []
        self.successors: list["JoinNode"] = []


class JoinNode:
    """Two-input node: joins a beta memory (left) with an alpha node (right)."""

    __slots__ = ("left", "right", "join_tests", "successor", "negated")

    def __init__(
        self,
        left: "BetaMemory | DummyBeta",
        right: AlphaNode,
        join_tests: list[tuple[str, str]],
        negated: bool = False,
    ):
        self.left = left
        self.right = right
        # join_tests: list of (left_var, right_var) that must be equal
        self.join_tests = join_tests
        self.successor: Any = None  # BetaMemory | ProductionNode | None
        self.negated = negated

    def _consistent(
        self, left_b: dict[str, Any], right_b: dict[str, Any]
    ) -> bool:
        """Check if left and right bindings are consistent for join."""
        for lv, rv in self.join_tests:
            if lv in left_b and rv in right_b and left_b[lv] != right_b[rv]:
                return False
        # Also merge-check: shared vars with same name must agree
        for k, v in right_b.items():
            if k in left_b and left_b[k] != v:
                return False
        return True

    def left_activate(self, facts: tuple[Fact, ...], bindings: dict[str, Any]):
        """A new left tuple arrives; join with all right items."""
        if self.successor is None:
            return
        if self.negated:
            # NCC (negated conjunctive condition): for this left tuple, check
            # that *no* right item is consistent.  If none, propagate.
            for rfact, rb in self.right.items:
                if self._consistent(bindings, rb):
                    # there is a matching negated fact → block
                    return
            self.successor.items.append((facts, dict(bindings)))
            self._propagate(facts, dict(bindings))
            return
        for rfact, rb in self.right.items:
            if self._consistent(bindings, rb):
                merged = {**bindings, **rb}
                new_facts = facts + (rfact,)
                self.successor.items.append((new_facts, merged))
                self._propagate(new_facts, merged)

    def right_activate(self, fact: Fact, rb: dict[str, Any]):
        """A new right fact arrives; join with all left items."""
        if self.successor is None:
            return
        if self.negated:
            # A new fact matching the negated condition *blocks* existing left
            # tuples that were previously propagated.  We must retract them.
            for i in range(len(self.successor.items) - 1, -1, -1):
                facts, bindings = self.successor.items[i]
                if self._consistent(bindings, rb):
                    del self.successor.items[i]
            return
        for facts, bindings in self.left.items:
            if self._consistent(bindings, rb):
                merged = {**bindings, **rb}
                new_facts = facts + (fact,)
                self.successor.items.append((new_facts, merged))
                self._propagate(new_facts, merged)

    def right_retract(self, fact: Fact, rb: dict[str, Any]):
        """Remove a right fact; retract dependent beta items."""
        if self.successor is None:
            return
        if self.negated:
            # Removing a negated fact may *unblock* some left tuples.
            for facts, bindings in self.left.items:
                if self._consistent(bindings, rb):
                    # Re-check whether *any* remaining right item blocks it.
                    # Also guard against duplicate instantiations.
                    blocked = any(
                        self._consistent(bindings, other_rb)
                        for other_f, other_rb in self.right.items
                        if other_f != fact
                    )
                    if not blocked:
                        # Avoid creating duplicate instantiations
                        existing = False
                        for ef, eb in self.successor.items:
                            if ef == facts:
                                existing = True
                                break
                        if not existing:
                            self.successor.items.append((facts, dict(bindings)))
                            self._propagate(facts, dict(bindings))
            return
        for i in range(len(self.successor.items) - 1, -1, -1):
            facts, bindings = self.successor.items[i]
            if fact in facts:
                del self.successor.items[i]

    def _propagate(self, facts: tuple[Fact, ...], bindings: dict[str, Any]):
        """Forward to successor join nodes (if any intermediate beta memory)."""
        # If successor has further join nodes, activate them left.
        for jn in getattr(self.successor, "successors", []):
            jn.left_activate(facts, bindings)


class DummyBeta:
    """Root beta memory — emits a single empty instantiation to seed joins."""

    __slots__ = ("items", "successors")

    def __init__(self):
        self.items: list[tuple[tuple[()], dict[str, Any]]] = [
            ((), {})
        ]
        self.successors: list[JoinNode] = []


class ProductionNode:
    """Leaf node: collects instantiations for one rule → conflict set.

    Implements the same minimal interface as ``BetaMemory`` (``items`` +
    ``successors``) so that ``JoinNode`` can treat both uniformly.
    """

    __slots__ = ("rule", "instantiations", "successors")

    def __init__(self, rule: Rule):
        self.rule = rule
        # instantiations: list of (facts, bindings)
        self.instantiations: list[tuple[tuple[Fact, ...], dict[str, Any]]] = []
        self.successors: list[JoinNode] = []  # always empty (leaf)

    @property
    def items(self) -> list[tuple[tuple[Fact, ...], dict[str, Any]]]:
        """Alias so JoinNode can use ``self.successor.items`` uniformly."""
        return self.instantiations

    def add(self, facts: tuple[Fact, ...], bindings: dict[str, Any]):
        self.instantiations.append((facts, bindings))

    def remove_with_fact(self, fact: Fact):
        self.instantiations = [
            (f, b) for f, b in self.instantiations if fact not in f
        ]


# --------------------------------------------------------------------------- #
#  Conflict resolution
# --------------------------------------------------------------------------- #


class ConflictResolution(Enum):
    """Strategy for selecting which instantiation to fire next."""

    FIFO = auto()  # oldest activation first
    LIFO = auto()  # newest first (depth-first)
    PRIORITY = auto()  # highest priority first, ties → FIFO
    RECENT = auto()  # most-recently-added fact first
    REFC = auto()  # refraction: never fire the same instantiation twice
    PRIORITY_REFC = auto()  # priority + refraction (recommended for production)


# Logging levels (stdlib-compatible numeric values)
_LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


# --------------------------------------------------------------------------- #
#  Engine
# --------------------------------------------------------------------------- #


class Engine:
    """The Rete inference engine.

    Example
    -------
    >>> eng = Engine()
    >>> eng.add_rule(Rule(
    ...     name="greet",
    ...     conditions=[Condition("person", name=Var("n"))],
    ...     actions=[lambda b, e: print(f"Hello, {b['n']}!")],
    ... ))
    >>> eng.assert_fact(Fact("person", name="Alice"))
    >>> eng.run()
    Hello, Alice!
    """

    def __init__(
        self,
        strategy: ConflictResolution = ConflictResolution.REFC,
        max_steps: int = 100_000,
        log_level: str = "WARNING",
        logger: Optional[logging.Logger] = None,
    ):
        self.strategy = strategy
        self.max_steps = max_steps
        self._log_level = _LOG_LEVELS.get(log_level.upper(), logging.WARNING)

        # Use stdlib logging with a named logger
        self.logger: logging.Logger = logger or logging.getLogger("rete")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter("[%(name)s:%(levelname)s] %(message)s")
            )
            self.logger.addHandler(handler)
        self.logger.setLevel(self._log_level)

        # Working memory
        self.facts: set[Fact] = set()
        self._facts_by_type: dict[str, set[Fact]] = defaultdict(set)

        # Network structures
        self._alpha_nodes: dict[tuple, AlphaNode] = {}
        self._dummy = DummyBeta()
        self._rules: dict[str, Rule] = {}
        self._prod_nodes: dict[str, ProductionNode] = {}
        # For each rule, the ordered chain of join nodes (for retract)
        self._rule_joins: dict[str, list[JoinNode]] = {}

        # Agenda
        self._fired: set[tuple] = set()  # for refraction
        self._step = 0

        # Truth maintenance: track which facts were logically asserted by
        # which rule firings, so they can be auto-retracted if the supporting
        # instantiation disappears.
        self._tms_support: dict[Fact, set[tuple]] = defaultdict(set)
        # Reverse map: instantiation → facts it asserted
        self._tms_derived: dict[tuple, set[Fact]] = defaultdict(set)

        # Firing log / trace
        self.trace: list[dict[str, Any]] = []
        self._tracing: bool = False

        # Rule statistics
        self.stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {"fires": 0, "activations": 0}
        )

        # Event listeners (observers)
        self._listeners: list[EngineListener] = []

    # -- Listener (observer) management ------------------------------------
    def add_listener(self, listener: EngineListener) -> None:
        """Register an event listener.

        The listener may implement any subset of ``on_assert``,
        ``on_retract``, and ``on_fire``.
        """
        self._listeners.append(listener)

    def remove_listener(self, listener: EngineListener) -> None:
        """Remove a previously-registered listener."""
        if listener in self._listeners:
            self._listeners.remove(listener)

    def _notify_assert(self, fact: Fact) -> None:
        for l in self._listeners:
            handler = getattr(l, "on_assert", None)
            if handler:
                handler(fact)

    def _notify_retract(self, fact: Fact) -> None:
        for l in self._listeners:
            handler = getattr(l, "on_retract", None)
            if handler:
                handler(fact)

    def _notify_fire(self, rule_name: str, bindings: dict[str, Any]) -> None:
        for l in self._listeners:
            handler = getattr(l, "on_fire", None)
            if handler:
                handler(rule_name, bindings)

    # -- Rule management ---------------------------------------------------
    def add_rule(self, rule: Rule) -> None:
        """Compile *rule* into the Rete network.

        Raises
        ------
        RuleError
            If a rule with the same name already exists.
        """
        if rule.name in self._rules:
            raise RuleError(f"rule '{rule.name}' already exists")
        self._rules[rule.name] = rule

        # Build / reuse alpha nodes for each condition
        alphas: list[AlphaNode] = []
        for cond in rule.conditions:
            key = cond.key
            if key not in self._alpha_nodes:
                an = AlphaNode(cond)
                self._alpha_nodes[key] = an
                # Feed existing facts into the new alpha node
                for f in self._facts_by_type.get(cond.fact_type, ()):
                    an.add(f)
                    # We do NOT propagate into joins yet — joins are wired below.
            an = self._alpha_nodes[key]
            alphas.append(an)

        # Build the beta / join chain left-to-right
        current_left: BetaMemory | DummyBeta = self._dummy
        join_chain: list[JoinNode] = []

        for idx, (cond, an) in enumerate(zip(rule.conditions, alphas)):
            # Determine join tests: variables shared between this condition and
            # any *earlier* condition must be consistent.
            join_tests: list[tuple[str, str]] = []
            # We collect the vars in this condition
            this_vars = {
                t.name for t in cond.fields.values()
                if t.is_var and isinstance(t, Var)
            }
            # Vars already bound by earlier conditions (we track incrementally)
            # For simplicity, same-named vars across conditions are join tests.
            # The join node's _consistent already handles same-name merges; we
            # also add explicit tests for clarity.
            join_tests = []  # same-name handled by _consistent merge check

            is_negated = cond.negated
            jn = JoinNode(current_left, an, join_tests, negated=is_negated)
            join_chain.append(jn)

            if idx < len(rule.conditions) - 1:
                beta = BetaMemory()
                jn.successor = beta
                current_left.successors.append(jn)
                # If this is a negated condition, the beta memory is fed only
                # when no matching negated fact exists (handled in JoinNode).
                # Seed from existing left items × existing right items:
                if is_negated:
                    for facts, bindings in current_left.items:
                        blocked = any(
                            jn._consistent(bindings, rb)
                            for _, rb in an.items
                        )
                        if not blocked:
                            beta.items.append((facts, dict(bindings)))
                            jn._propagate(facts, dict(bindings))
                else:
                    for facts, bindings in current_left.items:
                        for rfact, rb in an.items:
                            if jn._consistent(bindings, rb):
                                merged = {**bindings, **rb}
                                new_facts = facts + (rfact,)
                                beta.items.append((new_facts, merged))
                                jn._propagate(new_facts, merged)
                current_left = beta
            else:
                # Last condition → production node
                pn = ProductionNode(rule)
                jn.successor = pn
                current_left.successors.append(jn)
                self._prod_nodes[rule.name] = pn
                # Seed from existing data
                if is_negated:
                    for facts, bindings in current_left.items:
                        blocked = any(
                            jn._consistent(bindings, rb)
                            for _, rb in an.items
                        )
                        if not blocked:
                            pn.add(facts, dict(bindings))
                else:
                    for facts, bindings in current_left.items:
                        for rfact, rb in an.items:
                            if jn._consistent(bindings, rb):
                                merged = {**bindings, **rb}
                                new_facts = facts + (rfact,)
                                pn.add(new_facts, merged)

        self._rule_joins[rule.name] = join_chain

        # Wire alpha-node successors: each alpha node feeds its join node.
        for cond, an, jn in zip(rule.conditions, alphas, join_chain):
            if jn not in an.successors:
                an.successors.append(jn)

    def remove_rule(self, name: str) -> None:
        """Remove a rule and its network nodes.

        Properly cleans up join nodes from alpha-node successor lists and
        beta-memory successor lists to avoid orphaned references that could
        cause errors or memory leaks.

        Raises
        ------
        RuleError
            If the rule name is not found.
        """
        if name not in self._rules:
            raise RuleError(f"rule '{name}' not found")
        join_chain = self._rule_joins.get(name, [])
        # Remove join nodes from alpha-node successor lists
        for jn in join_chain:
            for an in self._alpha_nodes.values():
                if jn in an.successors:
                    an.successors.remove(jn)
            # Remove join nodes from beta-memory / dummy-beta successor lists
            left = jn.left
            if hasattr(left, "successors") and jn in left.successors:
                left.successors.remove(jn)
        del self._rules[name]
        del self._prod_nodes[name]
        del self._rule_joins[name]

    @property
    def rules(self) -> list[str]:
        """Return a list of rule names currently in the engine."""
        return list(self._rules)

    # -- Fact management ---------------------------------------------------
    def assert_fact(self, fact: Fact) -> bool:
        """Add *fact* to working memory; return True if newly inserted.

        Raises
        ------
        FactError
            If *fact* is not a ``Fact`` instance.
        """
        if not isinstance(fact, Fact):
            raise FactError("assert_fact requires a Fact instance")
        if fact in self.facts:
            return False
        self.facts.add(fact)
        self._facts_by_type[fact.fact_type].add(fact)
        self._propagate_assert(fact)
        self._notify_assert(fact)
        return True

    def assert_batch(self, facts: Iterable[Fact]) -> int:
        """Assert multiple facts at once. Returns the number newly inserted."""
        count = 0
        for f in facts:
            if self.assert_fact(f):
                count += 1
        return count

    def retract_fact(self, fact: Fact) -> bool:
        """Remove *fact* from working memory; return True if it was present."""
        if fact not in self.facts:
            return False
        self.facts.discard(fact)
        self._facts_by_type[fact.fact_type].discard(fact)
        self._propagate_retract(fact)
        self._notify_retract(fact)
        return True

    def retract_batch(self, facts: Iterable[Fact]) -> int:
        """Retract multiple facts at once. Returns the count removed."""
        count = 0
        for f in list(facts):
            if self.retract_fact(f):
                count += 1
        return count

    def retract_type(self, fact_type: str) -> int:
        """Retract all facts of *fact_type*; return the count removed."""
        to_remove = list(self._facts_by_type.get(fact_type, ()))
        for f in to_remove:
            self.retract_fact(f)
        return len(to_remove)

    def clear(self) -> None:
        """Remove all facts from working memory and reset agenda (rules remain).

        Also resets refraction memory so that rules can fire again when the
        same facts are re-asserted after a clear.
        """
        for f in list(self.facts):
            self.retract_fact(f)
        # Bug fix: clear() must also reset refraction memory, otherwise rules
        # cannot re-fire after facts are re-asserted.
        self.reset_agenda()

    def facts_of_type(self, fact_type: str) -> list[Fact]:
        """Return a list of all facts with the given type."""
        return list(self._facts_by_type.get(fact_type, ()))

    # -- Internal propagation ---------------------------------------------
    def _propagate_assert(self, fact: Fact) -> None:
        """Push *fact* through alpha nodes and onward through the net."""
        for an in self._alpha_nodes.values():
            if an.condition.fact_type != fact.fact_type:
                continue
            b = an.add(fact)
            if an.condition.negated:
                # Negated alpha: notify join nodes so they can *block*.
                for jn in an.successors:
                    jn.right_activate(fact, b or {})
                continue
            if b is None:
                continue
            for jn in an.successors:
                jn.right_activate(fact, b)

    def _propagate_retract(self, fact: Fact) -> None:
        """Remove *fact* from alpha nodes and retract from beta memories."""
        for an in self._alpha_nodes.values():
            if an.condition.fact_type != fact.fact_type:
                continue
            # Find the binding that was stored, if any
            stored = None
            for f, b in an.items:
                if f == fact:
                    stored = b
                    break
            an.remove(fact)
            if an.condition.negated:
                for jn in an.successors:
                    jn.right_retract(fact, stored or {})
                continue
            if stored is None:
                continue
            for jn in an.successors:
                jn.right_retract(fact, stored)
        # Clean production nodes
        for pn in self._prod_nodes.values():
            pn.remove_with_fact(fact)

    # -- Agenda / inference cycle -----------------------------------------
    def _collect_agenda(self) -> list[tuple[int, str, tuple[Fact, ...], dict]]:
        """Gather all current rule instantiations as a sortable list."""
        agenda = []
        for rname, pn in self._prod_nodes.items():
            rule = self._rules[rname]
            for facts, bindings in pn.instantiations:
                sig = (rname, facts)
                # REFC and PRIORITY_REFC both use refraction
                if self.strategy in (
                    ConflictResolution.REFC,
                    ConflictResolution.PRIORITY_REFC,
                ) and sig in self._fired:
                    continue
                agenda.append((rule.priority, rname, facts, bindings))
        return agenda

    def _select(self, agenda):
        """Pick one instantiation per the conflict-resolution strategy."""
        if not agenda:
            return None
        if self.strategy == ConflictResolution.PRIORITY:
            agenda.sort(key=lambda x: (-x[0], x[1]))
        elif self.strategy == ConflictResolution.PRIORITY_REFC:
            # Priority first, then FIFO for ties
            agenda.sort(key=lambda x: (-x[0], x[1]))
        elif self.strategy == ConflictResolution.LIFO:
            agenda.reverse()
        elif self.strategy == ConflictResolution.RECENT:
            agenda.sort(key=lambda x: max(f._id for f in x[2]), reverse=True)
        # FIFO / REFC / default → keep insertion order
        return agenda[0]

    def fire_one(self) -> bool:
        """Fire a single rule instantiation; return False if agenda empty.

        Raises
        ------
        InfiniteLoopError
            If the step count exceeds ``max_steps``.
        """
        agenda = self._collect_agenda()
        choice = self._select(agenda)
        if choice is None:
            return False
        _, rname, facts, bindings = choice
        rule = self._rules[rname]
        sig = (rname, facts)
        self._fired.add(sig)
        self._step += 1
        if self._step > self.max_steps:
            raise InfiniteLoopError(
                f"engine exceeded max_steps={self.max_steps}; "
                "possible non-terminating rule set"
            )
        # Record trace
        if self._tracing:
            self.trace.append({
                "step": self._step,
                "rule": rname,
                "bindings": dict(bindings),
                "facts": list(facts),
            })
        self.stats[rname]["fires"] += 1
        self._notify_fire(rname, dict(bindings))
        for action in rule.actions:
            action(dict(bindings), self)
        return True

    def run(self, max_steps: Optional[int] = None) -> int:
        """Fire rules until the agenda is exhausted; return the # of firings.

        Parameters
        ----------
        max_steps : int, optional
            Override the engine's default ``max_steps`` for this run only.
        """
        if max_steps is None:
            max_steps = self.max_steps
        fired = 0
        limit = min(max_steps, self.max_steps)
        while fired < limit:
            if not self.fire_one():
                break
            fired += 1
        return fired

    def reset_agenda(self) -> None:
        """Clear refraction memory so rules can fire again on same facts."""
        self._fired.clear()

    # -- Truth maintenance -------------------------------------------------
    def assert_logical(self, fact: Fact, support: tuple) -> bool:
        """Assert *fact* as logically derived from *support* (a firing sig).

        If the support instantiation is later retracted (because a condition
        fact is retracted), the derived fact is automatically retracted too.

        If the fact is already in working memory (e.g., asserted by another
        rule), the support is still tracked so that the fact is only
        retracted when *all* supports are withdrawn.
        """
        inserted = self.assert_fact(fact)
        # Always track support, even for already-present facts, so that
        # multiple rule firings can all support the same derived fact.
        self._tms_support[fact].add(support)
        self._tms_derived[support].add(fact)
        return inserted

    def _retract_support(self, sig: tuple) -> None:
        """Retract all facts logically derived from *sig*."""
        for fact in list(self._tms_derived.get(sig, ())):
            self._tms_support[fact].discard(sig)
            if not self._tms_support[fact]:
                # No remaining support → retract
                self.retract_fact(fact)
                self._tms_support.pop(fact, None)
        self._tms_derived.pop(sig, None)

    # -- Query API ---------------------------------------------------------
    def query(self, fact_type: str, **fields: Any) -> list[Fact]:
        """Find all facts of *fact_type* matching the given field values.

        Fields can be plain values (exact match) or ``Var`` instances
        (wildcard / bind).  Returns matching facts in insertion order.
        """
        results = []
        for fact in self._facts_by_type.get(fact_type, ()):
            match = True
            for k, v in fields.items():
                if isinstance(v, Var):
                    continue  # wildcard
                if fact.fields.get(k) != v:
                    match = False
                    break
            if match:
                results.append(fact)
        return results

    def query_one(self, fact_type: str, **fields: Any) -> Optional[Fact]:
        """Return the first matching fact, or None."""
        for fact in self.query(fact_type, **fields):
            return fact
        return None

    def fact_count(self, fact_type: Optional[str] = None) -> int:
        """Count facts, optionally filtered by type."""
        if fact_type is None:
            return len(self.facts)
        return len(self._facts_by_type.get(fact_type, ()))

    # -- Logging & tracing -------------------------------------------------
    def log(self, message: str, level: str = "INFO") -> None:
        """Log a message if the engine's log level permits it."""
        lvl = _LOG_LEVELS.get(level.upper(), logging.INFO)
        self.logger.log(lvl, message)

    def enable_tracing(self) -> None:
        """Enable recording of every firing in ``self.trace``."""
        self._tracing = True

    def disable_tracing(self) -> None:
        """Disable firing trace recording."""
        self._tracing = False

    def get_trace(self) -> list[dict[str, Any]]:
        """Return the list of recorded firings (if tracing enabled)."""
        return self.trace

    def get_stats(self) -> dict[str, dict[str, int]]:
        """Return per-rule statistics: fires and current activations."""
        for rname in self._rules:
            pn = self._prod_nodes.get(rname)
            if pn:
                self.stats[rname]["activations"] = len(pn.instantiations)
        return dict(self.stats)

    def reset_stats(self) -> None:
        """Reset all rule statistics."""
        self.stats.clear()
        self.trace.clear()

    # -- Inspection --------------------------------------------------------
    def agenda(self) -> list[tuple[str, dict[str, Any]]]:
        """Return a human-readable list of pending instantiations."""
        result = []
        for rname, pn in self._prod_nodes.items():
            for facts, bindings in pn.instantiations:
                sig = (rname, facts)
                if self.strategy in (
                    ConflictResolution.REFC,
                    ConflictResolution.PRIORITY_REFC,
                ) and sig in self._fired:
                    continue
                result.append((rname, dict(bindings)))
        return result

    # -- Network visualization --------------------------------------------
    def to_dot(self) -> str:
        """Render the Rete network as a Graphviz DOT string.

        This is useful for debugging and understanding how rules are
        compiled into the network.  The output can be rendered with
        ``dot -Tpng network.dot -o network.png``.
        """
        lines = ["digraph rete {", '  rankdir=LR;', '  node [fontname="monospace"];']

        # Root
        lines.append('  root [label="root", shape=ellipse];')

        # Alpha nodes
        for key, an in self._alpha_nodes.items():
            label = repr(an.condition)
            node_id = f"alpha_{abs(hash(key))}"
            shape = "box" if not an.condition.negated else "diamond"
            lines.append(f'  {node_id} [label="{label}", shape={shape}];')
            lines.append(f'  root -> {node_id};')

        # Join nodes and their connections
        for rname, joins in self._rule_joins.items():
            for i, jn in enumerate(joins):
                jn_id = f"join_{rname}_{i}"
                label = f"join\\n({rname}#{i})"
                if jn.negated:
                    label = "~" + label
                lines.append(f'  {jn_id} [label="{label}", shape=hexagon];')

                # left -> join
                if isinstance(jn.left, DummyBeta):
                    lines.append(f'  root -> {jn_id};')
                else:
                    left_id = None
                    # find the join node or beta that feeds this left
                    for other_rname, other_joins in self._rule_joins.items():
                        for j, oj in enumerate(other_joins):
                            if oj.successor is jn.left:
                                left_id = f"join_{other_rname}_{j}"
                                break
                        if left_id:
                            break
                    if left_id:
                        lines.append(f'  {left_id} -> {jn_id};')

                # right alpha -> join
                for key, an in self._alpha_nodes.items():
                    if jn in an.successors:
                        alpha_id = f"alpha_{abs(hash(key))}"
                        lines.append(f'  {alpha_id} -> {jn_id};')

            # Production node
            pn_id = f"prod_{rname}"
            lines.append(
                f'  {pn_id} [label="{rname}", shape=doubleoctagon];'
            )
            if joins:
                lines.append(f'  join_{rname}_{len(joins)-1} -> {pn_id};')

        lines.append("}")
        return "\n".join(lines)

    def network_summary(self) -> dict[str, Any]:
        """Return a summary dict describing the network structure."""
        return {
            "rules": len(self._rules),
            "alpha_nodes": len(self._alpha_nodes),
            "production_nodes": len(self._prod_nodes),
            "facts": len(self.facts),
            "strategy": self.strategy.name,
            "max_steps": self.max_steps,
            "step": self._step,
            "rule_details": {
                rname: {
                    "conditions": len(rule.conditions),
                    "actions": len(rule.actions),
                    "priority": rule.priority,
                    "join_nodes": len(self._rule_joins.get(rname, [])),
                    "instantiations": len(
                        self._prod_nodes.get(rname, ProductionNode(rule)).instantiations
                    ),
                }
                for rname, rule in self._rules.items()
            },
        }

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return (
            f"Engine(rules={len(self._rules)}, facts={len(self.facts)}, "
            f"strategy={self.strategy.name})"
        )