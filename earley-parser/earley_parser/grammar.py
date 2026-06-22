"""Grammar representation and BNF grammar file loader.

This module provides:
- ``Grammar``: a context-free grammar with nullable/FIRST/FOLLOW/FOLLOW
  set computation, productivity analysis, and validation.
- ``GrammarLoader``: a parser for BNF-like grammar definition files.
- ``GrammarStats``: statistics about a grammar (production count, depth, etc.)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import (
    Dict, List, Set, Tuple, Optional, Iterable,
)

from .errors import GrammarError

Symbol = str
EMPTY = ""  # epsilon sentinel


# --------------------------------------------------------------------------- #
# Grammar
# --------------------------------------------------------------------------- #

@dataclass
class Grammar:
    """A context-free grammar.

    ``productions`` maps each non-terminal to a list of RHS tuples. Each tuple
    element is a terminal or non-terminal symbol. An empty tuple ``()``
    represents epsilon. Terminals are any symbols that never appear as a LHS.

    The optional ``terminals`` set lets users mark symbols that should be
    treated as terminals even if they never appear in a rule (useful for
    external tokenizers).

    Attributes
    ----------
    start : str
        The start (axiom) non-terminal.
    productions : dict[str, list[tuple[str, ...]]]
        Mapping from non-terminal → list of RHS alternatives.
    terminals : set[str]
        Explicitly-declared terminals.
    name : str
        Optional human-readable name for the grammar.
    """

    start: str
    productions: Dict[str, List[Tuple[Symbol, ...]]]
    terminals: Set[str] = field(default_factory=set)
    name: str = ""

    def __post_init__(self) -> None:
        self._nullable_cache: Optional[Set[str]] = None
        self._first_cache: Optional[Dict[str, Set[str]]] = None
        self._follow_cache: Optional[Dict[str, Set[str]]] = None

    # -- construction ------------------------------------------------------- #

    @classmethod
    def from_rules(
        cls,
        start: str,
        rules: Iterable[Tuple[str, Tuple[Symbol, ...]]],
        terminals: Optional[Set[str]] = None,
        name: str = "",
    ) -> "Grammar":
        """Build from an iterable of ``(lhs, rhs)`` pairs.

        Repeated LHS entries accumulate into alternatives.
        """
        productions: Dict[str, List[Tuple[Symbol, ...]]] = field(default_factory=dict)
        prod: Dict[str, List[Tuple[Symbol, ...]]] = {}
        for lhs, rhs in rules:
            prod.setdefault(lhs, []).append(tuple(rhs))
        return cls(
            start=start,
            productions=prod,
            terminals=set(terminals) if terminals else set(),
            name=name,
        )

    def add_rule(self, lhs: str, rhs: Tuple[Symbol, ...]) -> None:
        """Add a single production. Resets derived caches."""
        self.productions.setdefault(lhs, []).append(tuple(rhs))
        self._nullable_cache = None
        self._first_cache = None
        self._follow_cache = None

    # -- queries ------------------------------------------------------------ #

    def is_terminal(self, sym: str) -> bool:
        """Return ``True`` if *sym* is a terminal symbol."""
        if sym in self.terminals:
            return True
        return sym not in self.productions

    def is_nonterminal(self, sym: str) -> bool:
        """Return ``True`` if *sym* is a non-terminal symbol."""
        return sym in self.productions

    def rhs_options(self, nt: str) -> List[Tuple[Symbol, ...]]:
        """Return all RHS alternatives for non-terminal *nt*."""
        return self.productions.get(nt, [])

    def nonterminals(self) -> Set[str]:
        """Return the set of all non-terminals."""
        return set(self.productions)

    def all_symbols(self) -> Set[str]:
        """Return the set of all symbols (terminals + non-terminals)."""
        syms: Set[str] = set(self.productions)
        for rhss in self.productions.values():
            for rhs in rhss:
                syms.update(rhs)
        return syms

    def terminal_set(self) -> Set[str]:
        """Return all symbols that are terminals."""
        return {s for s in self.all_symbols() if self.is_terminal(s) and s != EMPTY}

    # -- nullable ----------------------------------------------------------- #

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
                    if all(
                        s == EMPTY
                        or (s in self.productions and s in nullable)
                        for s in rhs
                    ):
                        nullable.add(nt)
                        changed = True
        self._nullable_cache = nullable
        return nullable

    def is_nullable_symbol(self, sym: str) -> bool:
        """Check if a single symbol is nullable."""
        if sym == EMPTY:
            return True
        if self.is_terminal(sym):
            return False
        return sym in self.nullable()

    def is_nullable_sequence(self, rhs: Tuple[Symbol, ...]) -> bool:
        """Check if an entire RHS sequence can derive epsilon."""
        return all(self.is_nullable_symbol(s) for s in rhs)

    # -- FIRST sets --------------------------------------------------------- #

    def first(self) -> Dict[str, Set[str]]:
        """Compute FIRST sets for all symbols.

        Terminals map to ``{themselves}``; epsilon maps to ``{EMPTY}``.
        Non-terminals get the union of FIRST sets of their alternatives,
        including EMPTY if any alternative is nullable.
        """
        if self._first_cache is not None:
            return self._first_cache
        first_sets: Dict[str, Set[str]] = {}
        nullable = self.nullable()
        for sym in self.all_symbols():
            if sym == EMPTY:
                first_sets[sym] = {EMPTY}
            elif self.is_terminal(sym):
                first_sets[sym] = {sym}
        changed = True
        while changed:
            changed = False
            for nt in self.productions:
                fs = first_sets.setdefault(nt, set())
                for rhs in self.productions[nt]:
                    for sym in rhs:
                        if sym == EMPTY:
                            continue
                        sym_first = first_sets.setdefault(sym, set())
                        before = len(fs)
                        fs |= sym_first - {EMPTY}
                        if len(fs) > before:
                            changed = True
                        if sym not in nullable:
                            break
                    else:
                        # all symbols nullable => nt can derive epsilon
                        before = len(fs)
                        fs.add(EMPTY)
                        if len(fs) > before:
                            changed = True
        self._first_cache = first_sets
        return first_sets

    def first_of_sequence(self, rhs: Tuple[Symbol, ...]) -> Set[str]:
        """Compute FIRST(α) for a sequence α = (s₁, s₂, …, sₙ).

        Includes EMPTY if the entire sequence is nullable.
        """
        result: Set[str] = set()
        first_sets = self.first()
        for sym in rhs:
            if sym == EMPTY:
                continue
            sym_first = first_sets.get(sym, {sym} if self.is_terminal(sym) else set())
            result |= sym_first - {EMPTY}
            if sym not in self.nullable() and sym != EMPTY:
                return result
        else:
            # All symbols are nullable
            result.add(EMPTY)
        return result

    # -- FOLLOW sets -------------------------------------------------------- #

    def follow(self) -> Dict[str, Set[str]]:
        """Compute FOLLOW sets for all non-terminals.

        FOLLOW(A) is the set of terminals that can appear immediately
        after A in some derivation from the start symbol. The start
        symbol's FOLLOW set always contains the special endmarker ``$``.
        """
        if self._follow_cache is not None:
            return self._follow_cache
        first_sets = self.first()
        nullable = self.nullable()
        follow_sets: Dict[str, Set[str]] = {nt: set() for nt in self.productions}
        follow_sets[self.start].add("$")
        changed = True
        while changed:
            changed = False
            for nt, rhss in self.productions.items():
                for rhs in rhss:
                    for i, sym in enumerate(rhs):
                        if sym == EMPTY or self.is_terminal(sym):
                            continue
                        # FIRST of the rest (after sym)
                        rest = rhs[i + 1:]
                        rest_first = self.first_of_sequence(rest)
                        before = len(follow_sets[sym])
                        follow_sets[sym] |= rest_first - {EMPTY}
                        if len(follow_sets[sym]) > before:
                            changed = True
                        # If rest is nullable, add FOLLOW(nt)
                        if EMPTY in rest_first or len(rest) == 0:
                            before2 = len(follow_sets[sym])
                            follow_sets[sym] |= follow_sets[nt]
                            if len(follow_sets[sym]) > before2:
                                changed = True
        self._follow_cache = follow_sets
        return follow_sets

    # -- productivity ------------------------------------------------------- #

    def productive(self) -> Set[str]:
        """Return the set of productive non-terminals.

        A non-terminal is productive if it can derive a terminal string.
        """
        prod_set: Set[str] = set()
        changed = True
        while changed:
            changed = False
            for nt, rhss in self.productions.items():
                if nt in prod_set:
                    continue
                for rhs in rhss:
                    if all(
                        s == EMPTY
                        or self.is_terminal(s)
                        or s in prod_set
                        for s in rhs
                    ):
                        prod_set.add(nt)
                        changed = True
        return prod_set

    # -- reachability ------------------------------------------------------- #

    def reachable(self) -> Set[str]:
        """Return the set of non-terminals reachable from the start symbol."""
        reach: Set[str] = set()
        queue: List[str] = [self.start]
        while queue:
            nt = queue.pop()
            if nt in reach:
                continue
            reach.add(nt)
            for rhs in self.productions.get(nt, []):
                for sym in rhs:
                    if sym in self.productions and sym not in reach:
                        queue.append(sym)
        return reach

    # -- validation --------------------------------------------------------- #

    def validate(self) -> List[str]:
        """Return a list of human-readable grammar problems (empty if OK)."""
        problems: List[str] = []
        if self.start not in self.productions:
            problems.append(f"Start symbol '{self.start}' has no productions.")
        for nt, rhss in self.productions.items():
            if not rhss:
                problems.append(f"Non-terminal '{nt}' has empty RHS list.")
        # Detect terminals that also appear as non-terminals (conflict).
        for t in self.terminals:
            if t in self.productions:
                problems.append(
                    f"Symbol '{t}' listed as terminal but has productions."
                )
        # Productive non-terminals
        prod = self.productive()
        for nt in self.productions:
            if nt not in prod:
                problems.append(
                    f"Non-terminal '{nt}' is unproductive "
                    f"(cannot derive a terminal string)."
                )
        # Reachability
        reach = self.reachable()
        for nt in self.productions:
            if nt not in reach:
                problems.append(
                    f"Non-terminal '{nt}' is unreachable from start symbol "
                    f"'{self.start}'."
                )
        return problems

    def is_valid(self) -> bool:
        """Return ``True`` if the grammar has no validation problems."""
        return len(self.validate()) == 0

    # -- stats -------------------------------------------------------------- #

    def stats(self) -> "GrammarStats":
        """Return a :class:`GrammarStats` summary for this grammar."""
        return GrammarStats(self)

    def to_dict(self) -> dict:
        """Serialize grammar to a dictionary."""
        return {
            "name": self.name,
            "start": self.start,
            "productions": {
                nt: [list(rhs) for rhs in rhss]
                for nt, rhss in self.productions.items()
            },
            "terminals": sorted(self.terminals),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Grammar":
        """Deserialize a grammar from a dictionary (inverse of :meth:`to_dict`)."""
        rules = []
        for nt, rhss in data["productions"].items():
            for rhs in rhss:
                rules.append((nt, tuple(rhs)))
        return cls(
            start=data["start"],
            productions={},
            terminals=set(data.get("terminals", [])),
            name=data.get("name", ""),
        ) if False else cls.from_rules(
            start=data["start"],
            rules=rules,
            terminals=set(data.get("terminals", [])),
            name=data.get("name", ""),
        )

    def __repr__(self) -> str:
        pcount = sum(len(v) for v in self.productions.values())
        return (
            f"Grammar(start={self.start!r}, "
            f"nonterminals={len(self.productions)}, "
            f"productions={pcount})"
        )


# --------------------------------------------------------------------------- #
# Grammar Stats
# --------------------------------------------------------------------------- #

class GrammarStats:
    """Summary statistics about a :class:`Grammar`.

    Provides useful metrics for analysis and display:

    - ``nonterminal_count``: number of distinct non-terminals
    - ``terminal_count``: number of distinct terminals
    - ``production_count``: total number of productions
    - ``nullable_count``: number of nullable non-terminals
    - ``max_rhs_length``: length of the longest RHS
    - ``avg_rhs_length``: average RHS length across all productions
    - ``unreachable``: set of unreachable non-terminals
    - ``unproductive``: set of unproductive non-terminals
    """

    def __init__(self, grammar: Grammar) -> None:
        self.grammar = grammar
        self.nonterminal_count: int = len(grammar.productions)
        self.terminal_count: int = len(grammar.terminal_set())
        self.production_count: int = sum(
            len(v) for v in grammar.productions.values()
        )
        self.nullable_count: int = len(grammar.nullable())
        self.max_rhs_length: int = max(
            (len(rhs) for rhss in grammar.productions.values() for rhs in rhss),
            default=0,
        )
        total_len = sum(
            len(rhs) for rhss in grammar.productions.values() for rhs in rhss
        )
        self.avg_rhs_length: float = (
            total_len / self.production_count if self.production_count else 0.0
        )
        self.unreachable: Set[str] = (
            set(grammar.productions) - grammar.reachable()
        )
        self.unproductive: Set[str] = (
            set(grammar.productions) - grammar.productive()
        )

    def to_dict(self) -> dict:
        return {
            "nonterminal_count": self.nonterminal_count,
            "terminal_count": self.terminal_count,
            "production_count": self.production_count,
            "nullable_count": self.nullable_count,
            "max_rhs_length": self.max_rhs_length,
            "avg_rhs_length": round(self.avg_rhs_length, 2),
            "unreachable": sorted(self.unreachable),
            "unproductive": sorted(self.unproductive),
        }

    def __repr__(self) -> str:
        return (
            f"GrammarStats(nt={self.nonterminal_count}, "
            f"t={self.terminal_count}, "
            f"prods={self.production_count}, "
            f"nullable={self.nullable_count})"
        )


# --------------------------------------------------------------------------- #
# BNF Grammar File Loader
# --------------------------------------------------------------------------- #

class GrammarLoader:
    """Parses a simple BNF-like grammar definition string into a :class:`Grammar`.

    Syntax::

        # Comments start with #
        <start> ::= <E>

        <E> ::= <E> "+" <E>
              | <E> "*" <E>
              | "(" <E> ")"
              | "id"

    Symbols in angle brackets ``<name>`` are non-terminals. Quoted strings
    are terminals. The first production's LHS is the start symbol (or use
    ``start ::= <X>`` to declare it explicitly). ``|`` separates alternatives.
    Empty alternative (e.g. ``|`` at end) means epsilon.
    """

    NONTERM_RE = re.compile(r"<([A-Za-z_][A-Za-z0-9_]*)>")
    TERM_RE = re.compile(r'"([^"]*)"' + r"|'([^']*)'")
    ARROW = "::="

    @classmethod
    def load(cls, text: str, name: str = "") -> Grammar:
        """Load a grammar from BNF text.

        Parameters
        ----------
        text : str
            The BNF grammar definition.
        name : str
            Optional name for the grammar.

        Raises
        ------
        GrammarError
            If the text is empty, unparseable, or contains invalid syntax.
        """
        if not text or not text.strip():
            raise GrammarError("Grammar file is empty or contains no content.")
        lines = text.split("\n")
        rules: List[Tuple[str, Tuple[Symbol, ...]]] = []
        explicit_start: Optional[str] = None
        current_lhs: Optional[str] = None

        for raw_line in lines:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            # Handle continuation lines starting with | (alternatives)
            if line.startswith("|"):
                line = line[1:].strip()
                if not line:
                    # Empty alternative => epsilon
                    if current_lhs is not None:
                        rules.append((current_lhs, ()))
                    continue
                rhs = cls._parse_rhs(line)
                if current_lhs is not None:
                    rules.append((current_lhs, tuple(rhs)))
                continue

            if cls.ARROW in line:
                lhs_part, rhs_part = line.split(cls.ARROW, 1)
                lhs_part = lhs_part.strip()
                # Check for bare "start" keyword (not wrapped in <>).
                if lhs_part == "start":
                    start_match = cls.NONTERM_RE.search(rhs_part.strip())
                    if start_match and not cls._has_terminals(rhs_part):
                        explicit_start = start_match.group(1)
                        current_lhs = None
                        continue
                lhs_match = cls.NONTERM_RE.search(lhs_part)
                if not lhs_match:
                    raise GrammarError(f"Invalid production LHS: {lhs_part!r}")
                lhs = lhs_match.group(1)
                current_lhs = lhs
                rhs = cls._parse_rhs(rhs_part)
                rules.append((lhs, tuple(rhs)))
            else:
                raise GrammarError(f"Unparseable grammar line: {raw_line!r}")

        if not rules:
            raise GrammarError("Grammar file contains no production rules.")
        start = explicit_start or rules[0][0]
        if start not in {lhs for lhs, _ in rules}:
            raise GrammarError(
                f"Start symbol '{start}' has no productions in the grammar."
            )
        # Collect terminals: symbols that are not non-terminal names.
        nts = {lhs for lhs, _ in rules}
        terminals: Set[str] = set()
        for _, rhs in rules:
            for sym in rhs:
                if sym != EMPTY and sym not in nts:
                    terminals.add(sym)
        return Grammar.from_rules(start, rules, terminals=terminals, name=name)

    @classmethod
    def load_file(cls, path: str) -> Grammar:
        """Load a grammar from a file path."""
        with open(path, "r") as f:
            text = f.read()
        import os
        name = os.path.splitext(os.path.basename(path))[0]
        return cls.load(text, name=name)

    @classmethod
    def _parse_rhs(cls, text: str) -> List[Symbol]:
        """Parse an RHS string into a list of symbols."""
        symbols: List[Symbol] = []
        i = 0
        while i < len(text):
            ch = text[i]
            if ch.isspace():
                i += 1
                continue
            if ch == "<":
                m = cls.NONTERM_RE.match(text, i)
                if m:
                    symbols.append(m.group(1))
                    i = m.end()
                    continue
            if ch == '"' or ch == "'":
                m = cls.TERM_RE.match(text, i)
                if m:
                    term = m.group(1) if m.group(1) is not None else m.group(2)
                    symbols.append(term)
                    i = m.end()
                    continue
            # Unquoted bare word => terminal
            j = i
            while j < len(text) and not text[j].isspace() and text[j] not in "<\"'|":
                j += 1
            if j > i:
                symbols.append(text[i:j])
                i = j
                continue
            if text[i] == "|":
                i += 1
                continue
            i += 1
        return symbols

    @classmethod
    def _has_terminals(cls, text: str) -> bool:
        return bool(cls.TERM_RE.search(text))