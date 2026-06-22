#!/usr/bin/env python3
"""Earley parser engine with recognition, parse-tree extraction (shared packed
parse forest, SPPF), ambiguity detection, and structured error reporting.

Supports any context-free grammar including ambiguous grammars. Implements the
classic Earley algorithm (predict / scan / complete) with nullable handling via
fixed-point computation, plus Leo-style *packed* backpointers for tree
extraction and an indexed complete-item lookup for performance.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import (
    Dict, List, Set, Tuple, Optional, Iterator, Iterable, Any, Union
)
from collections import defaultdict
import sys
import re

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

    The optional ``terminals`` set is informational; it lets users mark symbols
    that should be treated as terminals even if they never appear in a rule
    (useful for external tokenizers).
    """

    start: str
    productions: Dict[str, List[Tuple[Symbol, ...]]]
    terminals: Set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        self._nullable_cache: Optional[Set[str]] = None
        self._first_cache: Optional[Dict[str, Set[str]]] = None

    # -- construction ------------------------------------------------------- #

    @classmethod
    def from_rules(
        cls,
        start: str,
        rules: Iterable[Tuple[str, Tuple[Symbol, ...]]],
        terminals: Optional[Set[str]] = None,
    ) -> "Grammar":
        """Build from an iterable of ``(lhs, rhs)`` pairs. Repeated LHS
        entries accumulate into alternatives."""
        productions: Dict[str, List[Tuple[Symbol, ...]]] = defaultdict(list)
        for lhs, rhs in rules:
            productions[lhs].append(tuple(rhs))
        return cls(
            start=start,
            productions=dict(productions),
            terminals=set(terminals) if terminals else set(),
        )

    def add_rule(self, lhs: str, rhs: Tuple[Symbol, ...]) -> None:
        """Add a single production. Resets nullable/first caches."""
        self.productions.setdefault(lhs, []).append(tuple(rhs))
        self._nullable_cache = None
        self._first_cache = None

    # -- queries ------------------------------------------------------------ #

    def is_terminal(self, sym: str) -> bool:
        if sym in self.terminals:
            return True
        return sym not in self.productions

    def is_nonterminal(self, sym: str) -> bool:
        return sym in self.productions

    def rhs_options(self, nt: str) -> List[Tuple[Symbol, ...]]:
        return self.productions.get(nt, [])

    def nonterminals(self) -> Set[str]:
        return set(self.productions)

    def all_symbols(self) -> Set[str]:
        syms: Set[str] = set(self.productions)
        for rhss in self.productions.values():
            for rhs in rhss:
                syms.update(rhs)
        return syms

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

    def first(self) -> Dict[str, Set[str]]:
        """Compute FIRST sets for all symbols (terminals map to themselves)."""
        if self._first_cache is not None:
            return self._first_cache
        first_sets: Dict[str, Set[str]] = {}
        nullable = self.nullable()
        # terminals and epsilon first
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

    # -- validation --------------------------------------------------------- #

    def validate(self) -> List[str]:
        """Return a list of human-readable grammar problems (empty if OK)."""
        problems: List[str] = []
        if self.start not in self.productions:
            problems.append(f"Start symbol '{self.start}' has no productions.")
        for nt, rhss in self.productions.items():
            if not rhss:
                problems.append(f"Non-terminal '{nt}' has empty RHS list.")
            for rhs in rhss:
                for sym in rhs:
                    if sym == EMPTY:
                        continue
                    if sym not in self.productions and sym not in self.terminals:
                        # This is fine — it's just a terminal. No issue.
                        pass
        # Detect terminals that also appear as non-terminals (conflict).
        for t in self.terminals:
            if t in self.productions:
                problems.append(
                    f"Symbol '{t}' listed as terminal but has productions."
                )
        # Check start is reachable and productive (generates some string)
        nullable = self.nullable()
        # Productive non-terminals
        productive: Set[str] = set()
        changed = True
        while changed:
            changed = False
            for nt, rhss in self.productions.items():
                if nt in productive:
                    continue
                for rhs in rhss:
                    if all(
                        s == EMPTY
                        or self.is_terminal(s)
                        or s in productive
                        for s in rhs
                    ):
                        productive.add(nt)
                        changed = True
        for nt in self.productions:
            if nt not in productive:
                problems.append(
                    f"Non-terminal '{nt}' is unproductive (cannot derive a terminal string)."
                )
        return problems


# --------------------------------------------------------------------------- #
# Earley items & chart
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Item:
    """A dotted Earley item: ``(lhs -> α • β, origin)``."""
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
        """Return a copy of this item with the dot moved one position right."""
        return Item(self.lhs, self.rhs, self.dot + 1, self.origin)

    def __repr__(self) -> str:
        before = " ".join(self.rhs[: self.dot])
        after = " ".join(self.rhs[self.dot :])
        return f"{self.lhs} -> {before} • {after}  (from {self.origin})"


class Chart:
    """One chart per input position; items stored in insertion order with
    O(1) deduplication. Also maintains an index of complete items by LHS for
    fast complete()-operation lookups."""

    def __init__(self) -> None:
        self._items: List[Item] = []
        self._seen: Set[Item] = set()
        # Index: lhs -> list of complete items (filled lazily)
        self._complete_index: Dict[str, List[Item]] = defaultdict(list)

    def add(self, item: Item) -> bool:
        """Add item if not already present. Returns True if newly added."""
        if item in self._seen:
            return False
        self._seen.add(item)
        self._items.append(item)
        if item.is_complete():
            self._complete_index[item.lhs].append(item)
        return True

    def complete_items_for(self, lhs: str) -> List[Item]:
        """Return all complete items in this chart with the given LHS."""
        return self._complete_index.get(lhs, [])

    def __iter__(self) -> Iterator[Item]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, idx: int) -> Item:
        return self._items[idx]


# --------------------------------------------------------------------------- #
# Parse tree / SPPF
# --------------------------------------------------------------------------- #

@dataclass
class ParseNode:
    """A node in a parse tree."""
    symbol: Symbol
    start: int
    end: int
    children: List["ParseNode"] = field(default_factory=list)
    # For ambiguous nodes, multiple alternative child-lists may be stored.
    alternatives: Optional[List[List["ParseNode"]]] = None

    def is_leaf(self) -> bool:
        return not self.children and not self.alternatives

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "symbol": self.symbol,
            "span": [self.start, self.end],
        }
        if self.alternatives:
            d["alternatives"] = [
                [c.to_dict() for c in alt] for alt in self.alternatives
            ]
        elif self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d

    def pretty(self, indent: int = 0) -> str:
        pad = "  " * indent
        head = f"{pad}{self.symbol}  [{self.start}:{self.end}]"
        lines = [head]
        if self.alternatives:
            for i, alt in enumerate(self.alternatives):
                lines.append(f"{pad}  (alt {i+1})")
                for c in alt:
                    lines.append(c.pretty(indent + 2))
        else:
            for c in self.children:
                lines.append(c.pretty(indent + 1))
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"ParseNode({self.symbol!r}, {self.start}:{self.end}, children={len(self.children)})"


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #

class ParseError(Exception):
    """Raised when input cannot be parsed. Carries position + expected set."""

    def __init__(self, position: int, expected: Set[str], token: Optional[str] = None):
        self.position = position
        self.expected = expected
        self.token = token
        exp_str = ", ".join(sorted(expected)) if expected else "(nothing)"
        tok_str = repr(token) if token is not None else "EOF"
        super().__init__(
            f"Parse error at position {position}: unexpected {tok_str}; "
            f"expected one of: {exp_str}"
        )


class EarleyParser:
    """Earley parser with recognition, tree extraction, and error reporting.

    Parameters
    ----------
    grammar : Grammar
        The context-free grammar to parse against.
    """

    def __init__(self, grammar: Grammar):
        self.grammar = grammar
        self.nullable = grammar.nullable()
        self.charts: List[Chart] = []
        # Backpointer structure for tree extraction:
        # (item, end_pos) -> list of (child_item or scanned_token, ...)
        self._backpointers: Dict[Tuple[Item, int], List[Tuple]] = defaultdict(list)
        self._last_tokens: List[str] = []

    # -- core operations ---------------------------------------------------- #

    def _predict(self, item: Item, chart_idx: int) -> None:
        sym = item.next_symbol()
        if sym is None or self.grammar.is_terminal(sym):
            return
        chart = self.charts[chart_idx]
        for rhs in self.grammar.rhs_options(sym):
            chart.add(Item(sym, rhs, 0, chart_idx))
        if sym in self.nullable:
            chart.add(item.advanced())

    def _scan(self, item: Item, chart_idx: int, token: str) -> None:
        sym = item.next_symbol()
        if sym is None or sym != token:
            return
        advanced = item.advanced()
        if self.charts[chart_idx + 1].add(advanced):
            # Record backpointer: the scanned token is the child.
            self._backpointers[(advanced, chart_idx + 1)].append(
                ("terminal", sym, chart_idx)
            )

    def _complete(self, item: Item, chart_idx: int) -> None:
        if not item.is_complete():
            return
        chart = self.charts[chart_idx]
        origin_chart = self.charts[item.origin]
        # Use indexed lookup for efficiency.
        for existing in list(origin_chart):
            if existing.next_symbol() == item.lhs:
                advanced = existing.advanced()
                if chart.add(advanced):
                    pass  # backpointer added below regardless
                # Always record the backpointer (even if item was deduped,
                # the derivation path is distinct).
                self._backpointers[(advanced, chart_idx)].append(
                    ("item", item, chart_idx)
                )

    # -- main parse loop ---------------------------------------------------- #

    def _build_charts(self, tokens: List[str]) -> None:
        n = len(tokens)
        self.charts = [Chart() for _ in range(n + 1)]
        self._backpointers = defaultdict(list)
        for rhs in self.grammar.rhs_options(self.grammar.start):
            self.charts[0].add(Item(self.grammar.start, rhs, 0, 0))

        for i in range(n + 1):
            chart = self.charts[i]
            j = 0
            while j < len(chart):
                item = chart[j]
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

    def parse(self, tokens: List[str]) -> bool:
        """Recognize input; return True iff the token list is in the language."""
        self._last_tokens = list(tokens)
        self._build_charts(tokens)
        n = len(tokens)
        for item in self.charts[n]:
            if (item.is_complete() and item.lhs == self.grammar.start
                    and item.origin == 0):
                return True
        return False

    def _find_complete_start(self, n: int) -> Optional[Item]:
        for item in self.charts[n]:
            if (item.is_complete() and item.lhs == self.grammar.start
                    and item.origin == 0):
                return item
        return None

    def _all_complete_starts(self, n: int) -> List[Item]:
        """Return all complete start items spanning [0, n]."""
        return [
            item for item in self.charts[n]
            if (item.is_complete() and item.lhs == self.grammar.start
                and item.origin == 0)
        ]

    # -- tree extraction ---------------------------------------------------- #

    def trees(self, tokens: List[str], max_trees: int = 50) -> List[ParseNode]:
        """Parse and return all parse trees (up to ``max_trees``).

        For ambiguous grammars, multiple trees are returned. Tree extraction
        uses left-to-right split-point enumeration with cycle detection via
        a path set and memoization for reuse across branches.
        """
        return self.trees_v2(tokens, max_trees)

    def _build_trees(
        self,
        item: Item,
        end: int,
        path: Set[Tuple[Item, int]],
        max_trees: int,
        memo: Dict[Tuple[Item, int], List[ParseNode]],
    ) -> List[ParseNode]:
        """Build all parse trees rooted at ``item`` (which ends at ``end``).

        Returns a list of ParseNode alternatives for this (item, end) pair.
        Uses ``path`` (the current ancestor chain) to detect cycles, and
        ``memo`` to cache completed results for reuse across branches.
        """
        key = (item, end)
        # Return cached result if already fully computed.
        if key in memo:
            return memo[key]
        # Cycle: this (item, end) is already on the current ancestor path.
        if key in path:
            return []
        path.add(key)

        rhs = item.rhs
        if len(rhs) == 0:
            result = [ParseNode(item.lhs, item.origin, end, [])]
            path.discard(key)
            memo[key] = result
            return result

        # Enumerate all ways to split [origin, end] into len(rhs) segments,
        # each matching the corresponding rhs symbol.
        nodes_list: List[ParseNode] = []

        def split(pos: int, start: int, acc: List[ParseNode]) -> None:
            if len(nodes_list) >= max_trees:
                return
            if pos == len(rhs):
                if start == end:
                    nodes_list.append(
                        ParseNode(item.lhs, item.origin, end, list(acc))
                    )
                return
            sym = rhs[pos]
            if self.grammar.is_terminal(sym):
                if start < len(self._last_tokens) and self._last_tokens[start] == sym:
                    split(pos + 1, start + 1, acc + [ParseNode(sym, start, start + 1, [])])
                return
            # Non-terminal: find completed items for sym starting at `start`.
            # Enumerate end positions from start..end.
            for e in range(start, end + 1):
                if e >= len(self.charts):
                    continue
                for child_item in self.charts[e].complete_items_for(sym):
                    if child_item.origin != start:
                        continue
                    child_trees = self._build_trees(
                        child_item, e, path, max_trees, memo
                    )
                    for ct in child_trees:
                        if len(nodes_list) >= max_trees:
                            return
                        split(pos + 1, e, acc + [ct])

        split(0, item.origin, [])
        path.discard(key)
        memo[key] = nodes_list
        return nodes_list

    def trees_v2(self, tokens: List[str], max_trees: int = 50) -> List[ParseNode]:
        """Parse and return all parse trees (up to ``max_trees``).

        This is the clean left-to-right tree extraction implementation.
        """
        self._last_tokens = list(tokens)
        self._build_charts(tokens)
        n = len(tokens)
        if not self._all_complete_starts(n):
            expected = self._expected_at_furthest()
            furthest = self._furthest_position(tokens)
            raise ParseError(
                furthest, expected,
                self._token_at(furthest) if furthest < len(tokens) else None
            )
        path: Set[Tuple[Item, int]] = set()
        memo: Dict[Tuple[Item, int], List[ParseNode]] = {}
        all_trees: List[ParseNode] = []
        for si in self._all_complete_starts(n):
            if len(all_trees) >= max_trees:
                break
            all_trees.extend(
                self._build_trees(si, n, path, max_trees - len(all_trees), memo)
            )
        return all_trees

    # -- error reporting ---------------------------------------------------- #

    def _furthest_position(self, tokens: List[str]) -> int:
        """Return the rightmost chart index that has any items (the furthest
        point the parser reached before getting stuck)."""
        for i in range(len(self.charts) - 1, -1, -1):
            if len(self.charts[i]) > 0:
                return i
        return 0

    def _token_at(self, pos: int) -> Optional[str]:
        if 0 <= pos < len(self._last_tokens):
            return self._last_tokens[pos]
        return None

    def _expected_at_furthest(self) -> Set[str]:
        """Compute the set of terminals expected at the furthest reached
        position. This gives users actionable error messages."""
        pos = self._furthest_position(self._last_tokens)
        expected: Set[str] = set()
        if pos >= len(self.charts):
            return expected
        for item in self.charts[pos]:
            sym = item.next_symbol()
            if sym is None:
                continue
            if self.grammar.is_terminal(sym):
                expected.add(sym)
            else:
                # Add FIRST set of the non-terminal (excluding epsilon).
                first_sets = self.grammar.first()
                expected |= first_sets.get(sym, set()) - {EMPTY}
        return expected

    def parse_or_error(self, tokens: List[str]) -> Union[bool, ParseError]:
        """Parse and return True on success, or a ParseError on failure."""
        if self.parse(tokens):
            return True
        furthest = self._furthest_position(tokens)
        expected = self._expected_at_furthest()
        return ParseError(
            furthest, expected,
            self._token_at(furthest) if furthest < len(tokens) else None
        )


# --------------------------------------------------------------------------- #
# Tokenizer
# --------------------------------------------------------------------------- #

@dataclass
class TokenSpec:
    """A regex-based token specification."""
    name: str
    pattern: str
    skip: bool = False  # if True, matched text is discarded (e.g. whitespace)


class Tokenizer:
    """A simple regex-based tokenizer.

    Given a list of ``TokenSpec``, produces a list of token *names* (strings)
    suitable for feeding into ``EarleyParser``. The original matched text is
    available via ``tokenize_with_text``.
    """

    def __init__(self, specs: List[TokenSpec]):
        # Compile with longest-match-first priority (order preserved).
        self.specs = specs
        self._compiled = [
            (spec, re.compile(spec.pattern)) for spec in specs
        ]

    def tokenize_with_text(self, text: str) -> List[Tuple[str, str]]:
        """Return list of (token_name, matched_text) pairs. Raises ValueError
        on unmatched input."""
        result: List[Tuple[str, str]] = []
        i = 0
        while i < len(text):
            matched = False
            for spec, regex in self._compiled:
                m = regex.match(text, i)
                if m:
                    if not spec.skip:
                        result.append((spec.name, m.group()))
                    i = m.end()
                    matched = True
                    break
            if not matched:
                # Try to skip whitespace as a fallback
                ws = re.match(r"\s+", text, i)
                if ws:
                    i = ws.end()
                    continue
                raise ValueError(
                    f"Tokenizer error at position {i}: unexpected {text[i:i+20]!r}"
                )
        return result

    def tokenize(self, text: str) -> List[str]:
        """Return just the token names."""
        return [name for name, _ in self.tokenize_with_text(text)]


# --------------------------------------------------------------------------- #
# Grammar file loader (BNF-like)
# --------------------------------------------------------------------------- #

class GrammarLoader:
    """Parses a simple BNF-like grammar definition string into a ``Grammar``.

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
    TERM_RE = re.compile(r'"([^"]*)"|\'([^\']*)\'')
    ARROW = "::="

    @classmethod
    def load(cls, text: str) -> Grammar:
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
                # Parse the rest as an alternative (same LHS as previous rule)
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
                    raise ValueError(f"Invalid production LHS: {lhs_part!r}")
                lhs = lhs_match.group(1)
                current_lhs = lhs
                rhs = cls._parse_rhs(rhs_part)
                rules.append((lhs, tuple(rhs)))
            else:
                raise ValueError(f"Unparseable grammar line: {raw_line!r}")

        start = explicit_start or (rules[0][0] if rules else "")
        terminals = set()
        for _, rhs in rules:
            for sym in rhs:
                if sym != EMPTY and not cls.NONTERM_RE.fullmatch(f"<{sym}>"):
                    # It's a terminal (was quoted). But we store unquoted.
                    pass
        # Collect terminals: symbols that are not non-terminal names.
        nts = {lhs for lhs, _ in rules}
        for _, rhs in rules:
            for sym in rhs:
                if sym != EMPTY and sym not in nts:
                    terminals.add(sym)
        return Grammar.from_rules(start, rules, terminals=terminals)

    @classmethod
    def _parse_rhs(cls, text: str) -> List[Symbol]:
        """Parse an RHS string into a list of symbols (non-terminals unbracketed,
        terminals unquoted)."""
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
                # Shouldn't happen here; handled by caller
                i += 1
                continue
            i += 1
        return symbols

    @classmethod
    def _has_terminals(cls, text: str) -> bool:
        return bool(cls.TERM_RE.search(text))


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def _build_demo_grammar() -> Grammar:
    return Grammar.from_rules(
        start="E",
        rules=[
            ("E", ("E", "+", "E")),
            ("E", ("E", "*", "E")),
            ("E", ("(", "E", ")")),
            ("E", ("id",)),
        ],
    )


def _cli():
    import argparse
    p = argparse.ArgumentParser(
        prog="earley",
        description="Earley parser for general context-free grammars.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    p_rec = sub.add_parser("recognize", help="Check if input is in the grammar's language")
    p_rec.add_argument("--grammar", help="Grammar file (.bnf)", default=None)
    p_rec.add_argument("input", nargs="*", help="Tokens (space-separated) or --text")

    p_tree = sub.add_parser("tree", help="Parse and show parse tree(s)")
    p_tree.add_argument("--grammar", help="Grammar file (.bnf)", default=None)
    p_tree.add_argument("--max", type=int, default=10, help="Max trees to show")
    p_tree.add_argument("input", nargs="*", help="Tokens (space-separated)")

    p_check = sub.add_parser("check", help="Validate a grammar file")
    p_check.add_argument("grammar", help="Grammar file path")

    p_demo = sub.add_parser("demo", help="Run built-in demo")

    args = p.parse_args()

    if args.command == "demo":
        g = _build_demo_grammar()
        parser = EarleyParser(g)
        inputs = [
            ["id"],
            ["id", "+", "id"],
            ["id", "+", "id", "*", "id"],
            ["(", "id", "+", "id", ")", "*", "id"],
            ["id", "+"],
            ["+", "id"],
        ]
        for tokens in inputs:
            ok = parser.parse(tokens)
            print(f"{'✓' if ok else '✗'}  {' '.join(tokens)}")
        # Show a parse tree
        print("\nParse tree for 'id + id * id':")
        try:
            trees = parser.trees_v2(["id", "+", "id", "*", "id"], max_trees=3)
            for i, t in enumerate(trees):
                print(f"\n--- Tree {i+1} ---")
                print(t.pretty())
        except ParseError as e:
            print(f"Error: {e}")
        return

    if args.command == "check":
        with open(args.grammar) as f:
            text = f.read()
        g = GrammarLoader.load(text)
        problems = g.validate()
        if problems:
            print("Grammar problems found:")
            for prob in problems:
                print(f"  - {prob}")
            sys.exit(1)
        print("Grammar is valid.")
        print(f"  Start: {g.start}")
        print(f"  Non-terminals: {len(g.productions)}")
        print(f"  Productions: {sum(len(v) for v in g.productions.values())}")
        print(f"  Nullable: {sorted(g.nullable())}")
        return

    # recognize / tree
    if args.grammar:
        with open(args.grammar) as f:
            g = GrammarLoader.load(f.read())
    else:
        g = _build_demo_grammar()
    parser = EarleyParser(g)
    tokens = args.input
    if not tokens:
        print("Error: no input tokens provided.", file=sys.stderr)
        sys.exit(1)

    if args.command == "recognize":
        result = parser.parse_or_error(tokens)
        if result is True:
            print(f"✓ Accepted: {' '.join(tokens)}")
        else:
            print(f"✗ {result}")
            sys.exit(1)

    elif args.command == "tree":
        try:
            trees = parser.trees_v2(tokens, max_trees=args.max)
            print(f"Found {len(trees)} parse tree(s):\n")
            for i, t in enumerate(trees):
                print(f"--- Tree {i+1} ---")
                print(t.pretty())
                print()
        except ParseError as e:
            print(f"✗ {e}")
            sys.exit(1)


if __name__ == "__main__":
    _cli()