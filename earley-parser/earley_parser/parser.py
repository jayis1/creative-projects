"""Core Earley parser engine.

Provides:
- ``Item``: a dotted Earley item.
- ``Chart``: one chart per input position with O(1) dedup and indexed
  complete-item lookup.
- ``ParseNode``: a node in a parse tree (with ambiguity support).
- ``ParseForest``: a shared packed parse forest (SPPF) container.
- ``EarleyParser``: the main parser with recognition, tree extraction,
  and structured error reporting.
"""
from __future__ import annotations

import copy
import json
import logging
from dataclasses import dataclass, field
from typing import (
    Dict, List, Set, Tuple, Optional, Iterator, Any, Union,
)
from collections import defaultdict

from .grammar import Grammar, Symbol, EMPTY
from .errors import ParseError

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Earley items & chart
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Item:
    """A dotted Earley item: ``(lhs -> α • β, origin)``.

    Attributes
    ----------
    lhs : str
        Left-hand side non-terminal.
    rhs : tuple[str, ...]
        Right-hand side symbol sequence.
    dot : int
        Position of the dot (0..len(rhs)).
    origin : int
        Input position at which recognition of this non-terminal began.
    """

    lhs: str
    rhs: Tuple[Symbol, ...]
    dot: int
    origin: int

    def next_symbol(self) -> Optional[Symbol]:
        """Return the symbol after the dot, or ``None`` if complete."""
        if self.dot < len(self.rhs):
            return self.rhs[self.dot]
        return None

    def is_complete(self) -> bool:
        """Return ``True`` if the dot is at the end (item is complete)."""
        return self.dot >= len(self.rhs)

    def advanced(self) -> "Item":
        """Return a copy of this item with the dot moved one position right."""
        return Item(self.lhs, self.rhs, self.dot + 1, self.origin)

    def __repr__(self) -> str:
        before = " ".join(self.rhs[: self.dot])
        after = " ".join(self.rhs[self.dot :])
        return f"{self.lhs} -> {before} • {after}  (from {self.origin})"


class Chart:
    """One chart per input position.

    Items are stored in insertion order with O(1) deduplication via a
    ``set``. An index of complete items by LHS enables fast
    complete()-operation lookups.
    """

    def __init__(self) -> None:
        self._items: List[Item] = []
        self._seen: Set[Item] = set()
        self._complete_index: Dict[str, List[Item]] = defaultdict(list)

    def add(self, item: Item) -> bool:
        """Add *item* if not already present.

        Returns ``True`` if newly added, ``False`` if it was a duplicate.
        """
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

    def incomplete_items_for(self, lhs: str) -> List[Item]:
        """Return all incomplete items expecting *lhs* as the next symbol."""
        return [
            item for item in self._items
            if not item.is_complete() and item.next_symbol() == lhs
        ]

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
    """A node in a parse tree.

    For ambiguous nodes, ``alternatives`` holds multiple alternative
    child-lists.

    Attributes
    ----------
    symbol : str
        The grammar symbol (terminal or non-terminal).
    start : int
        Start position in the input.
    end : int
        End position in the input.
    children : list[ParseNode]
        Child nodes for the default (first) interpretation.
    alternatives : list[list[ParseNode]] or None
        Additional child-lists for ambiguous parses.
    """

    symbol: Symbol
    start: int
    end: int
    children: List["ParseNode"] = field(default_factory=list)
    alternatives: Optional[List[List["ParseNode"]]] = None

    def is_leaf(self) -> bool:
        """Return ``True`` if this node has no children."""
        return not self.children and not self.alternatives

    def is_ambiguous(self) -> bool:
        """Return ``True`` if this node has multiple interpretations."""
        return self.alternatives is not None and len(self.alternatives) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a nested dictionary."""
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

    def to_json(self, indent: Optional[int] = 2) -> str:
        """Serialize to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def pretty(self, indent: int = 0) -> str:
        """Return a human-readable indented tree representation."""
        pad = "  " * indent
        head = f"{pad}{self.symbol}  [{self.start}:{self.end}]"
        lines = [head]
        if self.alternatives:
            for i, alt in enumerate(self.alternatives):
                lines.append(f"{pad}  (alt {i + 1})")
                for c in alt:
                    lines.append(c.pretty(indent + 2))
        else:
            for c in self.children:
                lines.append(c.pretty(indent + 1))
        return "\n".join(lines)

    def yield_terminals(self) -> List[Symbol]:
        """Return the list of terminal symbols at the leaves (left to right)."""
        result: List[Symbol] = []
        if self.alternatives:
            # Use first alternative
            for c in self.alternatives[0]:
                result.extend(c.yield_terminals())
        else:
            for c in self.children:
                result.extend(c.yield_terminals())
        if self.is_leaf():
            result.append(self.symbol)
        return result

    def depth(self) -> int:
        """Return the maximum depth of the tree."""
        if self.alternatives:
            return 1 + max(
                (c.depth() for alt in self.alternatives for c in alt),
                default=0,
            )
        return 1 + max((c.depth() for c in self.children), default=0)

    def count_nodes(self) -> int:
        """Return the total number of nodes in the tree."""
        if self.alternatives:
            return 1 + sum(
                c.count_nodes() for alt in self.alternatives for c in alt
            )
        return 1 + sum(c.count_nodes() for c in self.children)

    def walk(self) -> Iterator["ParseNode"]:
        """Yield all nodes in the tree (depth-first, pre-order)."""
        yield self
        if self.alternatives:
            for alt in self.alternatives:
                for c in alt:
                    yield from c.walk()
        else:
            for c in self.children:
                yield from c.walk()

    def __repr__(self) -> str:
        return (
            f"ParseNode({self.symbol!r}, {self.start}:{self.end}, "
            f"children={len(self.children)})"
        )


class ParseForest:
    """A shared packed parse forest (SPPF) container.

    Wraps a list of :class:`ParseNode` trees and provides analysis,
    serialization, and export utilities.
    """

    def __init__(self, trees: List[ParseNode], grammar: Optional[Grammar] = None) -> None:
        self.trees = trees
        self.grammar = grammar

    def __len__(self) -> int:
        return len(self.trees)

    def __iter__(self) -> Iterator[ParseNode]:
        return iter(self.trees)

    def __getitem__(self, idx: int) -> ParseNode:
        return self.trees[idx]

    @property
    def is_ambiguous(self) -> bool:
        """Return ``True`` if the forest contains more than one tree."""
        return len(self.trees) > 1

    @property
    def ambiguity_count(self) -> int:
        """Return the number of distinct parse trees."""
        return len(self.trees)

    def pretty(self) -> str:
        """Return a string representation of all trees."""
        lines: List[str] = []
        for i, t in enumerate(self.trees):
            lines.append(f"--- Tree {i + 1} ---")
            lines.append(t.pretty())
            lines.append("")
        return "\n".join(lines)

    def to_json(self, indent: Optional[int] = 2) -> str:
        """Serialize the forest to a JSON array of tree dicts."""
        return json.dumps([t.to_dict() for t in self.trees], indent=indent)

    def to_dot(self) -> str:
        """Export the first tree as a Graphviz DOT graph string.

        Ambiguous nodes show alternatives as separate sub-trees.
        """
        lines = ["digraph ParseTree {"]
        lines.append("  rankdir=TB;")
        lines.append('  node [fontname="monospace"];')
        counter = [0]

        def emit(node: ParseNode, parent_id: Optional[int]) -> int:
            nid = counter[0]
            counter[0] += 1
            label = f"{node.symbol}\\n[{node.start}:{node.end}]"
            lines.append(f'  n{nid} [label="{label}"];')
            if parent_id is not None:
                lines.append(f"  n{parent_id} -> n{nid};")
            if node.alternatives:
                for alt in node.alternatives:
                    for c in alt:
                        emit(c, nid)
            else:
                for c in node.children:
                    emit(c, nid)
            return nid

        if self.trees:
            emit(self.trees[0], None)
        lines.append("}")
        return "\n".join(lines)

    def to_lisp(self) -> str:
        """Return the first tree as a Lisp-style S-expression."""
        def to_sexpr(node: ParseNode) -> str:
            children = node.children
            if node.alternatives:
                children = node.alternatives[0]
            if not children:
                return node.symbol
            inner = " ".join(to_sexpr(c) for c in children)
            return f"({node.symbol} {inner})"
        return to_sexpr(self.trees[0]) if self.trees else ""

    def stats(self) -> dict:
        """Return statistics about the forest."""
        return {
            "tree_count": len(self.trees),
            "is_ambiguous": self.is_ambiguous,
            "max_depth": max((t.depth() for t in self.trees), default=0),
            "total_nodes": sum(t.count_nodes() for t in self.trees),
        }


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #

class EarleyParser:
    """Earley parser with recognition, tree extraction, and error reporting.

    Parameters
    ----------
    grammar : Grammar
        The context-free grammar to parse against.
    """

    def __init__(self, grammar: Grammar) -> None:
        self.grammar = grammar
        self.nullable = grammar.nullable()
        self.charts: List[Chart] = []
        self._backpointers: Dict[Tuple[Item, int], List[Tuple]] = defaultdict(list)
        self._last_tokens: List[str] = []
        self._chart_stats: List[int] = []

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
            self._backpointers[(advanced, chart_idx + 1)].append(
                ("terminal", sym, chart_idx)
            )

    def _complete(self, item: Item, chart_idx: int) -> None:
        if not item.is_complete():
            return
        chart = self.charts[chart_idx]
        origin_chart = self.charts[item.origin]
        for existing in list(origin_chart):
            if existing.next_symbol() == item.lhs:
                advanced = existing.advanced()
                chart.add(advanced)
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
            self._chart_stats.append(len(chart))

    def parse(self, tokens: List[str]) -> bool:
        """Recognize input; return ``True`` iff the token list is in the language."""
        self._last_tokens = list(tokens)
        self._build_charts(tokens)
        n = len(tokens)
        for item in self.charts[n]:
            if (item.is_complete() and item.lhs == self.grammar.start
                    and item.origin == 0):
                logger.debug("Parse accepted: %s", tokens)
                return True
        logger.debug("Parse rejected: %s", tokens)
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
        """Parse and return all parse trees (up to *max_trees*).

        For ambiguous grammars, multiple trees are returned. Tree extraction
        uses left-to-right split-point enumeration with cycle detection via
        a path set and memoization for reuse across branches.
        """
        return self._extract_trees(tokens, max_trees)

    def forest(self, tokens: List[str], max_trees: int = 50) -> ParseForest:
        """Parse and return a :class:`ParseForest` container."""
        trees = self.trees(tokens, max_trees)
        return ParseForest(trees, self.grammar)

    @staticmethod
    def _copy_tree(node: ParseNode) -> ParseNode:
        """Deep-copy a :class:`ParseNode` tree."""
        return ParseNode(
            node.symbol, node.start, node.end,
            [EarleyParser._copy_tree(c) for c in node.children],
        )

    def _build_trees(
        self,
        item: Item,
        end: int,
        path: Set[Tuple[Item, int]],
        max_trees: int,
        memo: Dict[Tuple[Item, int], List[ParseNode]],
    ) -> List[ParseNode]:
        """Build all parse trees rooted at *item* (ending at *end*).

        Uses *path* (ancestor chain) for cycle detection and *memo*
        for caching completed sub-results.
        """
        key = (item, end)
        if key in memo:
            return memo[key]
        if key in path:
            return []
        path.add(key)

        rhs = item.rhs
        if len(rhs) == 0:
            result = [ParseNode(item.lhs, item.origin, end, [])]
            path.discard(key)
            memo[key] = result
            return result

        nodes_list: List[ParseNode] = []

        def split(pos: int, start: int, acc: List[ParseNode]) -> None:
            if len(nodes_list) >= max_trees:
                return
            if pos == len(rhs):
                if start == end:
                    # Deep-copy all children so each tree is independent.
                    nodes_list.append(
                        ParseNode(item.lhs, item.origin, end,
                                  [self._copy_tree(c) for c in acc])
                    )
                return
            sym = rhs[pos]
            if self.grammar.is_terminal(sym):
                if start < len(self._last_tokens) and self._last_tokens[start] == sym:
                    split(pos + 1, start + 1,
                          acc + [ParseNode(sym, start, start + 1, [])])
                return
            # Non-terminal: find completed items for sym starting at `start`.
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
        # Only cache if not truncated by max_trees.
        if len(nodes_list) < max_trees:
            memo[key] = nodes_list
        return nodes_list

    def _extract_trees(
        self, tokens: List[str], max_trees: int = 50
    ) -> List[ParseNode]:
        """Internal tree extraction that builds charts and enumerates trees."""
        self._last_tokens = list(tokens)
        self._build_charts(tokens)
        n = len(tokens)
        if not self._all_complete_starts(n):
            expected = self._expected_at_furthest()
            furthest = self._furthest_position()
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

    # -- back-compat alias -------------------------------------------------- #

    def trees_v2(self, tokens: List[str], max_trees: int = 50) -> List[ParseNode]:
        """Alias for :meth:`trees` (backward compatibility with v1)."""
        return self.trees(tokens, max_trees)

    # -- error reporting ---------------------------------------------------- #

    def _furthest_position(self) -> int:
        """Return the rightmost chart index that has any items."""
        for i in range(len(self.charts) - 1, -1, -1):
            if len(self.charts[i]) > 0:
                return i
        return 0

    def _token_at(self, pos: int) -> Optional[str]:
        if 0 <= pos < len(self._last_tokens):
            return self._last_tokens[pos]
        return None

    def _expected_at_furthest(self) -> Set[str]:
        """Compute the set of terminals expected at the furthest position."""
        pos = self._furthest_position()
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
                first_sets = self.grammar.first()
                expected |= first_sets.get(sym, set()) - {EMPTY}
        return expected

    def parse_or_error(self, tokens: List[str]) -> Union[bool, ParseError]:
        """Parse and return ``True`` on success, or a :class:`ParseError` on failure."""
        if self.parse(tokens):
            return True
        furthest = self._furthest_position()
        expected = self._expected_at_furthest()
        return ParseError(
            furthest, expected,
            self._token_at(furthest) if furthest < len(tokens) else None
        )

    # -- diagnostics -------------------------------------------------------- #

    def chart_stats(self) -> List[int]:
        """Return a list of item-counts per chart position after a parse."""
        return [len(c) for c in self.charts]

    def chart_dump(self, positions: Optional[List[int]] = None) -> str:
        """Return a human-readable dump of chart contents.

        If *positions* is given, only those indices are included.
        """
        lines: List[str] = []
        for i, chart in enumerate(self.charts):
            if positions is not None and i not in positions:
                continue
            lines.append(f"Chart[{i}] ({len(chart)} items):")
            for item in chart:
                lines.append(f"  {item}")
        return "\n".join(lines)

    def ambiguity_count(self, tokens: List[str], max_trees: int = 100) -> int:
        """Return the number of distinct parse trees (up to *max_trees*).

        This is a convenience method for ambiguity analysis.
        """
        try:
            return len(self.trees(tokens, max_trees))
        except ParseError:
            return 0

    def is_ambiguous(self, tokens: List[str]) -> bool:
        """Return ``True`` if the input has more than one parse tree."""
        return self.ambiguity_count(tokens, max_trees=2) > 1