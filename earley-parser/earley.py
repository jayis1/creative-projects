#!/usr/bin/env python3
"""A clean Earley parser engine implementing a basic Earley recognizer and parser."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional, Iterator
from collections import defaultdict


Symbol = str  # non-terminal or terminal token string

EMPTY = ""  # epsilon/empty


# --------------------------------------------------------------------------- #
# Grammar
# --------------------------------------------------------------------------- #

@dataclass
class Grammar:
    """A context-free grammar.

    Productions are stored as a dict: non-terminal -> list of RHS sequences.
    Each RHS is a tuple of symbols (terminals or non-terminals).
    An empty tuple `()` represents epsilon.
    """

    start: str
    productions: Dict[str, List[Tuple[Symbol, ...]]]
    # Terminal set inferred lazily; explicitly listing helps ambiguity.
    terminals: Set[str] = field(default_factory=set)

    def __post_init__(self):
        self._nullable_cache: Optional[Set[str]] = None

    # -- construction ------------------------------------------------------- #

    @classmethod
    def from_rules(
        cls,
        start: str,
        rules: List[Tuple[str, Tuple[Symbol, ...]]],
    ) -> "Grammar":
        """Build from a list of (lhs, rhs) tuples. Repeated LHS accumulate."""
        productions: Dict[str, List[Tuple[Symbol, ...]]] = defaultdict(list)
        for lhs, rhs in rules:
            productions[lhs].append(tuple(rhs))
        return cls(start=start, productions=dict(productions))

    def add_rule(self, lhs: str, rhs: Tuple[Symbol, ...]):
        self.productions.setdefault(lhs, []).append(tuple(rhs))
        self._nullable_cache = None

    # -- queries ------------------------------------------------------------ #

    def is_terminal(self, sym: str) -> bool:
        return sym not in self.productions

    def is_nonterminal(self, sym: str) -> bool:
        return sym in self.productions

    def rhs_options(self, nt: str) -> List[Tuple[Symbol, ...]]:
        return self.productions.get(nt, [])

    def nullable(self) -> Set[str]:
        """Compute nullable non-terminals via fixed-point iteration."""
        if self._nullable_cache is not None:
            return self._nullable_cache
        nullable: Set[str] = set()
        changed = True
        while changed:
            changed = False
            for nt, rhss in self.productions.items():
                if nt in nullable:
                    continue
                for rhs in rhss:
                    if all(s == EMPTY or (s in self.productions and s in nullable) for s in rhs):
                        nullable.add(nt)
                        changed = True
        self._nullable_cache = nullable
        return nullable


# --------------------------------------------------------------------------- #
# Earley items & chart
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Item:
    """A dotted Earley item: (rule_lhs -> α • β, origin)."""
    lhs: str
    rhs: Tuple[Symbol, ...]
    dot: int
    origin: int

    def next_symbol(self) -> Optional[Symbol]:
        if self.dot < len(self.rhs):
            return self.rhs[self.dot]
        return None

    def is_complete(self) -> bool:
        return self.dot >= len(self.rhs)

    def advanced(self) -> "Item":
        return Item(self.lhs, self.rhs, self.dot + 1, self.origin)


class Chart:
    """One chart per input position; items stored in an ordered set."""

    def __init__(self):
        self._items: List[Item] = []
        self._seen: Set[Item] = set()

    def add(self, item: Item) -> bool:
        if item in self._seen:
            return False
        self._seen.add(item)
        self._items.append(item)
        return True

    def __iter__(self) -> Iterator[Item]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #

class EarleyParser:
    """Earley recognizer/parses an input string against a Grammar.

    This core implementation recognizes and builds a list of completed
    items for later extraction. Tree extraction is added in Phase 2.
    """

    def __init__(self, grammar: Grammar):
        self.grammar = grammar
        self.nullable = grammar.nullable()
        self.charts: List[Chart] = []

    def _predict(self, item: Item, chart_idx: int) -> None:
        sym = item.next_symbol()
        if sym is None:
            return
        if self.grammar.is_nonterminal(sym):
            chart = self.charts[chart_idx]
            for rhs in self.grammar.rhs_options(sym):
                chart.add(Item(sym, rhs, 0, chart_idx))
            # nullable completion
            if sym in self.nullable:
                chart.add(item.advanced())

    def _scan(self, item: Item, chart_idx: int, token: str) -> None:
        sym = item.next_symbol()
        if sym is None:
            return
        if sym == token:
            self.charts[chart_idx + 1].add(item.advanced())

    def _complete(self, item: Item, chart_idx: int) -> None:
        chart = self.charts[chart_idx]
        if not item.is_complete():
            return
        target = self.charts[item.origin]
        for existing in list(target):
            if existing.next_symbol() == item.lhs:
                chart.add(existing.advanced())

    def parse(self, tokens: List[str]) -> bool:
        """Recognize input; return True iff parse succeeds."""
        n = len(tokens)
        self.charts = [Chart() for _ in range(n + 1)]
        # seed: all productions for start symbol, origin 0
        for rhs in self.grammar.rhs_options(self.grammar.start):
            self.charts[0].add(Item(self.grammar.start, rhs, 0, 0))

        for i in range(n + 1):
            chart = self.charts[i]
            j = 0
            while j < len(chart):
                item = chart._items[j]
                j += 1
                if item.is_complete():
                    self._complete(item, i)
                else:
                    sym = item.next_symbol()
                    if sym is not None and self.grammar.is_terminal(sym):
                        if i < n:
                            self._scan(item, i, tokens[i])
                    else:
                        self._predict(item, i)
        # check for complete start item spanning [0, n]
        for item in self.charts[n]:
            if (item.is_complete() and item.lhs == self.grammar.start
                    and item.origin == 0):
                return True
        return False


# --------------------------------------------------------------------------- #
# CLI / demo
# --------------------------------------------------------------------------- #

def _demo():
    g = Grammar.from_rules(
        start="E",
        rules=[
            ("E", ("E", "+", "E")),
            ("E", ("E", "*", "E")),
            ("E", ("(", "E", ")")),
            ("E", ("id",)),
        ],
    )
    p = EarleyParser(g)
    inputs = [
        ["id"],
        ["id", "+", "id"],
        ["id", "+", "id", "*", "id"],
        ["(", "id", "+", "id", ")", "*", "id"],
        ["id", "+"],
        ["+", "id"],
    ]
    for tokens in inputs:
        ok = p.parse(tokens)
        print(f"{'✓' if ok else '✗'}  {' '.join(tokens)}")


if __name__ == "__main__":
    _demo()