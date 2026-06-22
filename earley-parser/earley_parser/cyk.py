"""CYK (Cocke-Younger-Kasami) parser — an alternative parsing algorithm.

The CYK algorithm is a bottom-up dynamic programming parser that works
on **CNF (Chomsky Normal Form)** grammars. It runs in O(n³ · |G|) time
and is simpler to implement than Earley but requires grammars to be in
CNF.

This module provides:
- ``CNFGrammar``: a grammar restricted to CNF rules (A → BC or A → a).
- ``CYKParser``: the CYK parser with recognition and tree extraction.
- ``cnf_convert``: best-effort conversion of a general CFG to CNF.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple, Optional

from .grammar import Grammar, Symbol, EMPTY
from .errors import ParseError


# --------------------------------------------------------------------------- #
# CNF Grammar
# --------------------------------------------------------------------------- #

@dataclass
class CNFProduction:
    """A production in Chomsky Normal Form.

    Either a binary rule ``A → B C`` (both ``left`` and ``right`` set)
    or a terminal rule ``A → a`` (only ``terminal`` set).
    """
    lhs: str
    left: Optional[str] = None
    right: Optional[str] = None
    terminal: Optional[str] = None

    def is_binary(self) -> bool:
        return self.left is not None and self.right is not None

    def is_terminal(self) -> bool:
        return self.terminal is not None

    def __repr__(self) -> str:
        if self.is_binary():
            return f"{self.lhs} -> {self.left} {self.right}"
        return f"{self.lhs} -> {self.terminal!r}"


class CNFGrammar:
    """A grammar in Chomsky Normal Form.

    Rules must be one of:
    - ``A → B C`` (two non-terminals)
    - ``A → a`` (single terminal)

    Epsilon is only allowed for the start symbol (``S → ε``).
    """

    def __init__(self, start: str) -> None:
        self.start = start
        self.binary_rules: List[CNFProduction] = []
        self.terminal_rules: List[CNFProduction] = []
        # Indexes for fast lookup
        self._binary_index: Dict[Tuple[str, str], List[str]] = {}
        self._terminal_index: Dict[str, List[str]] = {}
        self._start_nullable: bool = False

    def add_binary(self, lhs: str, left: str, right: str) -> None:
        """Add a binary rule ``A → B C``."""
        rule = CNFProduction(lhs=lhs, left=left, right=right)
        self.binary_rules.append(rule)
        self._binary_index.setdefault((left, right), []).append(lhs)

    def add_terminal(self, lhs: str, terminal: str) -> None:
        """Add a terminal rule ``A → a``."""
        rule = CNFProduction(lhs=lhs, terminal=terminal)
        self.terminal_rules.append(rule)
        self._terminal_index.setdefault(terminal, []).append(lhs)

    def set_start_nullable(self, nullable: bool = True) -> None:
        """Mark the start symbol as nullable (S → ε allowed)."""
        self._start_nullable = nullable

    def lhs_for_terminal(self, terminal: str) -> List[str]:
        """Return all LHS non-terminals that produce *terminal*."""
        return self._terminal_index.get(terminal, [])

    def lhs_for_binary(self, left: str, right: str) -> List[str]:
        """Return all LHS non-terminals for the binary pair (left, right)."""
        return self._binary_index.get((left, right), [])

    def __repr__(self) -> str:
        return (
            f"CNFGrammar(start={self.start!r}, "
            f"binary={len(self.binary_rules)}, "
            f"terminal={len(self.terminal_rules)})"
        )


# --------------------------------------------------------------------------- #
# CYK Parser
# --------------------------------------------------------------------------- #

class CYKParser:
    """Cocke-Younger-Kasami parser for CNF grammars.

    Runs in O(n³ · |G|) time. Supports recognition, parse-tree extraction,
    and ambiguity detection.

    Parameters
    ----------
    grammar : CNFGrammar
        The CNF grammar to parse against.
    """

    def __init__(self, grammar: CNFGrammar) -> None:
        self.grammar = grammar
        # table[i][j] = set of non-terminals deriving tokens[i:i+j]
        self._table: List[List[Set[str]]] = []

    def parse(self, tokens: List[str]) -> bool:
        """Recognize *tokens*; return ``True`` iff in the language."""
        n = len(tokens)
        if n == 0:
            return self.grammar._start_nullable

        # Initialize table: table[i][j] covers tokens[i:i+j+1], j from 0 to n-i-1
        # We use table[i][l] for substring of length l+1 starting at i.
        # Standard CYK: table[i][j] = nonterminals deriving tokens[i:j+1]
        # where j = i + length - 1.
        # We'll use table[i][length] = set of NTs for tokens[i:i+length].
        self._table = [[set() for _ in range(n - i + 1)] for i in range(n + 1)]
        # Actually simpler: table[i][l] = set of NTs deriving tokens[i:i+l]
        # l ranges 1..n-i. We'll use 0-indexed lengths.
        table: List[List[Set[str]]] = [[set() for _ in range(n + 1)] for _ in range(n)]
        self._table = table

        # Fill length-1 cells
        for i in range(n):
            for lhs in self.grammar.lhs_for_terminal(tokens[i]):
                table[i][1].add(lhs)

        # Fill length-l cells for l = 2..n
        for length in range(2, n + 1):
            for i in range(n - length + 1):
                for split in range(1, length):
                    left_part = table[i][split]
                    right_part = table[i + split][length - split]
                    for b in left_part:
                        for c in right_part:
                            for lhs in self.grammar.lhs_for_binary(b, c):
                                table[i][length].add(lhs)

        return self.grammar.start in table[0][n]

    def trees(self, tokens: List[str], max_trees: int = 50) -> List:
        """Parse and return all parse trees (up to *max_trees*)."""
        from .parser import ParseNode

        n = len(tokens)
        if n == 0:
            if self.grammar._start_nullable:
                return [ParseNode(self.grammar.start, 0, 0, [])]
            raise ParseError(0, set(), None)

        # Build the table first
        if not self.parse(tokens):
            raise ParseError(n, set(), None)

        table = self._table

        def build(nt: str, i: int, length: int) -> List[ParseNode]:
            """Build all trees for *nt* deriving tokens[i:i+length]."""
            results: List[ParseNode] = []
            if length == 1:
                # Terminal rule
                for rule in self.grammar.terminal_rules:
                    if rule.lhs == nt and rule.terminal == tokens[i]:
                        results.append(
                            ParseNode(nt, i, i + 1, [
                                ParseNode(tokens[i], i, i + 1, [])
                            ])
                        )
                        break
                return results

            # Binary rules: try all splits
            for split in range(1, length):
                for rule in self.grammar.binary_rules:
                    if rule.lhs != nt:
                        continue
                    if (rule.left in table[i][split]
                            and rule.right in table[i + split][length - split]):
                        left_trees = build(rule.left, i, split)
                        right_trees = build(rule.right, i + split, length - split)
                        for lt in left_trees:
                            for rt in right_trees:
                                if len(results) >= max_trees:
                                    return results
                                results.append(
                                    ParseNode(nt, i, i + length, [lt, rt])
                                )
            return results

        return build(self.grammar.start, 0, n)

    def parse_or_error(self, tokens: List[str]) -> object:
        """Parse and return ``True`` or a :class:`ParseError`."""
        if self.parse(tokens):
            return True
        return ParseError(len(tokens), set(), None)