"""Grammar representation for the LALR(1) parser generator.

A grammar is defined by a set of productions, a start symbol, and an
augmented production S' -> S that marks successful end-of-input with $.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

EPSILON = ""  # empty string sentinel


@dataclass(frozen=True)
class Production:
    """A single production rule:  head -> body...

    Attributes:
        head: non-terminal LHS.
        body: tuple of symbols (terminals or non-terminals).
        index: numeric index used for table building / debugging.
    """

    head: str
    body: Tuple[str, ...]
    index: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "body", tuple(self.body))

    def __str__(self) -> str:
        rhs = " ".join(self.body) if self.body else "ε"
        return f"{self.head} -> {rhs}"

    def __repr__(self) -> str:  # pragma: no cover - convenience
        return f"Production({self.head} -> {' '.join(self.body) or 'ε'})"


class Grammar:
    """Context-free grammar with augmented start production.

    Parameters:
        productions: list of (head, [body...]) tuples.  The first production's
            head is used as the start symbol.
        start: optional explicit start symbol.  Defaults to the head of the
            first production.

    The grammar automatically inserts the augmented production ``S' -> S``
    as production index 0 so that acceptance is explicit ($ lookahead).
    """

    AUGMENTED_START = "$accept"

    def __init__(
        self,
        productions: List[Tuple[str, List[str]]],
        start: Optional[str] = None,
    ) -> None:
        if not productions:
            raise ValueError("Grammar must contain at least one production")
        self._original = list(productions)
        self.user_start = start if start is not None else productions[0][0]

        # Build internal production list with augmented start first.
        self.productions: List[Production] = []
        self.productions.append(
            Production(self.AUGMENTED_START, (self.user_start,), 0)
        )
        idx = 1
        for head, body in productions:
            self.productions.append(Production(head, tuple(body), idx))
            idx += 1

        # Collect terminal / non-terminal sets.
        nonterminals: Set[str] = set()
        for p in self.productions:
            nonterminals.add(p.head)
        self.nonterminals: Set[str] = nonterminals

        all_symbols: Set[str] = set()
        for p in self.productions:
            all_symbols.add(p.head)
            all_symbols.update(p.body)
        self.symbols: List[str] = sorted(all_symbols)
        self.terminals: Set[str] = all_symbols - nonterminals
        # EOF marker
        self.terminals.add("$")
        self.nonterminals.add(self.AUGMENTED_START)

        # Production lookup by head.
        self._by_head: Dict[str, List[Production]] = {}
        for p in self.productions:
            self._by_head.setdefault(p.head, []).append(p)

        # Nullable non-terminals (epsilon in some body).
        self.nullable: Set[str] = self._compute_nullable()

        # FIRST sets.
        self.first: Dict[str, Set[str]] = self._compute_first()

        # FOLLOW sets (needed for SLR(1)).
        self.follow: Dict[str, Set[str]] = self._compute_follow()

    # ------------------------------------------------------------------ #
    # Public helpers
    # ------------------------------------------------------------------ #
    def productions_for(self, head: str) -> List[Production]:
        return self._by_head.get(head, [])

    def is_terminal(self, sym: str) -> bool:
        return sym in self.terminals

    def is_nonterminal(self, sym: str) -> bool:
        return sym in self.nonterminals

    def start_production(self) -> Production:
        return self.productions[0]

    def production_by_index(self, idx: int) -> Production:
        return self.productions[idx]

    def first_of_string(self, symbols: Tuple[str, ...]) -> Set[str]:
        """FIRST(α) for a string of symbols."""
        result: Set[str] = set()
        for sym in symbols:
            if self.is_terminal(sym):
                result.add(sym)
                return result
            # non-terminal
            result |= self.first[sym]
            if sym not in self.nullable:
                return result
        # all nullable → add epsilon sentinel via empty string marker
        result.add(EPSILON)
        return result

    # ------------------------------------------------------------------ #
    # Nullable / FIRST / FOLLOW computation
    # ------------------------------------------------------------------ #
    def _compute_nullable(self) -> Set[str]:
        nullable: Set[str] = set()
        changed = True
        while changed:
            changed = False
            for p in self.productions:
                if p.head in nullable:
                    continue
                if not p.body:  # epsilon
                    nullable.add(p.head)
                    changed = True
                    continue
                if all(s in nullable for s in p.body):
                    nullable.add(p.head)
                    changed = True
        return nullable

    def _compute_first(self) -> Dict[str, Set[str]]:
        first: Dict[str, Set[str]] = {s: set() for s in self.symbols}
        for t in self.terminals:
            first[t] = {t}
        changed = True
        while changed:
            changed = False
            for p in self.productions:
                if not p.body:
                    # Epsilon production: FIRST includes epsilon.
                    before = len(first[p.head])
                    first[p.head].add(EPSILON)
                    if len(first[p.head]) != before:
                        changed = True
                    continue
                before = len(first[p.head])
                for sym in p.body:
                    first[p.head] |= first[sym]
                    if sym not in self.nullable:
                        break
                else:
                    # all nullable
                    first[p.head].add(EPSILON)
                if len(first[p.head]) != before:
                    changed = True
        return first

    def _compute_follow(self) -> Dict[str, Set[str]]:
        follow: Dict[str, Set[str]] = {nt: set() for nt in self.nonterminals}
        # $ is in FOLLOW(start)
        follow[self.AUGMENTED_START].add("$")
        follow[self.user_start].add("$")

        changed = True
        while changed:
            changed = False
            for p in self.productions:
                for i, sym in enumerate(p.body):
                    if sym not in self.nonterminals:
                        continue
                    rest = p.body[i + 1:]
                    first_rest = self.first_of_string(rest)
                    before = len(follow[sym])
                    follow[sym] |= (first_rest - {EPSILON})
                    if EPSILON in first_rest or not rest:
                        follow[sym] |= follow[p.head]
                    if len(follow[sym]) != before:
                        changed = True
        return follow

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #
    def validate(self) -> List[str]:
        """Return a list of warning messages for grammar issues."""
        warnings: List[str] = []
        # Undefined symbols: a symbol on the RHS that is never a production
        # head and was not declared as a terminal.  Since we infer terminals
        # as "any symbol that's not a non-terminal", truly undefined symbols
        # are those that appear only on the RHS and look like they should be
        # non-terminals (uppercase by convention) but have no productions.
        # We instead check: any RHS symbol not defined as a non-terminal AND
        # not explicitly listed as a terminal is flagged.
        defined_nonterminals = self.nonterminals
        # Re-derive terminals: symbols that appear only on RHS
        rhs_symbols: Set[str] = set()
        for p in self.productions:
            rhs_symbols.update(p.body)
        # A symbol is "undefined" if it's in RHS, not a non-terminal, and
        # there's no production defining it — but since our inference makes
        # every non-nonterminal a terminal, we check for symbols that look
        # like non-terminals (appear in some RHS, never as head) but are
        # treated as terminals.  This is not necessarily an error.
        # Better: check for symbols referenced but never defined anywhere.
        all_defined = defined_nonterminals | self.terminals
        for p in self.productions:
            for s in p.body:
                if s not in all_defined:
                    warnings.append(
                        f"Symbol '{s}' in production {p} is undefined."
                    )
        # Unreachable non-terminals
        reachable: Set[str] = set()
        stack = [self.user_start]
        while stack:
            s = stack.pop()
            if s in reachable:
                continue
            reachable.add(s)
            for p in self.productions_for(s):
                for sym in p.body:
                    if sym in self.nonterminals and sym not in reachable:
                        stack.append(sym)
        for nt in self.nonterminals:
            if nt not in reachable and nt != self.AUGMENTED_START:
                warnings.append(f"Non-terminal '{nt}' is unreachable from start.")
        return warnings

    def __repr__(self) -> str:  # pragma: no cover
        lines = [f"Grammar(start={self.user_start}, {len(self.productions)} prods)"]
        for p in self.productions:
            lines.append(f"  {p.index}: {p}")
        return "\n".join(lines)