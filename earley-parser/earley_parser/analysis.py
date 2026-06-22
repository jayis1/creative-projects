"""Grammar analysis tools.

Provides:
- ``LL1Table``: LL(1) predictive parser table construction and analysis.
- ``is_ll1``: check if a grammar is LL(1).
- ``detect_ambiguity``: empirical ambiguity detection.
- ``compute_bracket_depth``: estimate nesting complexity.
- ``GrammarComparator``: compare two grammars for language equivalence
  (approximate, via sampling).
"""
from __future__ import annotations

from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict

from .grammar import Grammar, Symbol, EMPTY
from .parser import EarleyParser


# --------------------------------------------------------------------------- #
# LL(1) Analysis
# --------------------------------------------------------------------------- #

class LL1Table:
    """LL(1) predictive parsing table.

    The table maps ``(non-terminal, terminal)`` pairs to a production
    (RHS tuple). If any cell has multiple entries, the grammar is not
    LL(1).
    """

    def __init__(self, grammar: Grammar) -> None:
        self.grammar = grammar
        self._table: Dict[Tuple[str, str], List[Tuple[Symbol, ...]]] = defaultdict(list)
        self._conflicts: List[str] = []
        self._built = False

    def build(self) -> "LL1Table":
        """Construct the LL(1) table. Returns self for chaining."""
        first = self.grammar.first()
        follow = self.grammar.follow()
        for nt, rhss in self.grammar.productions.items():
            for rhs in rhss:
                first_alpha = self.grammar.first_of_sequence(rhs)
                for terminal in first_alpha - {EMPTY}:
                    self._table[(nt, terminal)].append(rhs)
                # If alpha is nullable, add FOLLOW(nt) entries
                if EMPTY in first_alpha:
                    for terminal in follow.get(nt, set()):
                        self._table[(nt, terminal)].append(rhs)
        # Detect conflicts
        for key, entries in self._table.items():
            if len(entries) > 1:
                nt, term = key
                self._conflicts.append(
                    f"Conflict at [{nt}, {term}]: {len(entries)} productions"
                )
        self._built = True
        return self

    @property
    def is_ll1(self) -> bool:
        """Return ``True`` if the grammar is LL(1) (no conflicts)."""
        if not self._built:
            self.build()
        return len(self._conflicts) == 0

    @property
    def conflicts(self) -> List[str]:
        """Return a list of conflict descriptions."""
        if not self._built:
            self.build()
        return self._conflicts

    def get(self, nt: str, terminal: str) -> Optional[Tuple[Symbol, ...]]:
        """Get the production for ``(nt, terminal)``.

        Returns ``None`` if no entry exists. Returns the first entry if
        multiple exist (grammatically a conflict — check :attr:`is_ll1`).
        """
        if not self._built:
            self.build()
        entries = self._table.get((nt, terminal), [])
        return entries[0] if entries else None

    def get_all(self, nt: str, terminal: str) -> List[Tuple[Symbol, ...]]:
        """Get all productions for ``(nt, terminal)`` (may be multiple)."""
        if not self._built:
            self.build()
        return list(self._table.get((nt, terminal), []))

    def terminals(self) -> Set[str]:
        """Return all terminals that appear in the table."""
        return {t for (_, t) in self._table}

    def nonterminals(self) -> Set[str]:
        """Return all non-terminals that appear in the table."""
        return {nt for (nt, _) in self._table}

    def pretty(self) -> str:
        """Return a human-readable table representation."""
        if not self._built:
            self.build()
        terms = sorted(self.terminals() | {"$"})
        nts = sorted(self.nonterminals())
        if not nts:
            return "(empty LL(1) table)"
        header = "  | " + " | ".join(f"{t:^10}" for t in terms) + " |"
        sep = "--+" + "+".join("-" * 12 for _ in terms) + "+"
        lines = [header, sep]
        for nt in nts:
            row = f"{nt} |"
            for t in terms:
                prod = self.get(nt, t)
                if prod is None:
                    row += f"{'':^10}|"
                else:
                    s = " ".join(prod) if prod else "ε"
                    if len(s) > 10:
                        s = s[:9] + "…"
                    row += f"{s:^10}|"
            lines.append(row)
        return "\n".join(lines)

    def __repr__(self) -> str:
        if not self._built:
            self.build()
        return f"LL1Table(entries={len(self._table)}, ll1={self.is_ll1})"


def is_ll1(grammar: Grammar) -> bool:
    """Check if *grammar* is LL(1).

    A grammar is LL(1) if its LL(1) parsing table has no conflicts.
    """
    return LL1Table(grammar).build().is_ll1


# --------------------------------------------------------------------------- #
# Ambiguity Detection
# --------------------------------------------------------------------------- #

def detect_ambiguity(
    grammar: Grammar,
    max_length: int = 6,
    alphabet: Optional[List[str]] = None,
) -> List[List[str]]:
    """Empirically detect ambiguity in a grammar.

    Generates all token sequences up to *max_length* using the given
    *alphabet* (or the grammar's terminals) and checks if any produces
    multiple parse trees.

    Returns a list of ambiguous token sequences.
    """
    parser = EarleyParser(grammar)
    if alphabet is None:
        alphabet = sorted(grammar.terminal_set())
    ambiguous: List[List[str]] = []
    # BFS over all token sequences up to max_length
    from itertools import product
    for length in range(1, max_length + 1):
        for combo in product(alphabet, repeat=length):
            tokens = list(combo)
            try:
                count = parser.ambiguity_count(tokens, max_trees=2)
                if count > 1:
                    ambiguous.append(tokens)
            except Exception:
                pass
    return ambiguous


def is_ambiguous(
    grammar: Grammar,
    max_length: int = 6,
    alphabet: Optional[List[str]] = None,
) -> bool:
    """Return ``True`` if the grammar is ambiguous (empirically detected)."""
    return len(detect_ambiguity(grammar, max_length, alphabet)) > 0


# --------------------------------------------------------------------------- #
# Grammar comparison (approximate)
# --------------------------------------------------------------------------- #

class GrammarComparator:
    """Approximately compare two grammars for language equivalence.

    Since exact CFG equivalence is undecidable in general, this uses
    sampling: generate short strings and check membership in both
    grammars. Mismatches indicate the languages differ.
    """

    def __init__(self, g1: Grammar, g2: Grammar) -> None:
        self.g1 = g1
        self.g2 = g2
        self.p1 = EarleyParser(g1)
        self.p2 = EarleyParser(g2)

    def compare(
        self, max_length: int = 5,
        alphabet: Optional[List[str]] = None,
    ) -> Dict[str, object]:
        """Compare the two grammars' languages.

        Returns a dict with keys:
        - ``in_1_not_2``: strings accepted by g1 but not g2
        - ``in_2_not_1``: strings accepted by g2 but not g1
        - ``in_both``: strings accepted by both
        - ``match``: True if no differences found
        """
        if alphabet is None:
            alphabet = sorted(
                self.g1.terminal_set() | self.g2.terminal_set()
            )
        from itertools import product
        in_1_not_2: List[List[str]] = []
        in_2_not_1: List[List[str]] = []
        in_both: List[List[str]] = []
        for length in range(0, max_length + 1):
            for combo in product(alphabet, repeat=length):
                tokens = list(combo)
                a = self.p1.parse(tokens)
                b = self.p2.parse(tokens)
                if a and b:
                    in_both.append(tokens)
                elif a and not b:
                    in_1_not_2.append(tokens)
                elif b and not a:
                    in_2_not_1.append(tokens)
        return {
            "in_1_not_2": in_1_not_2,
            "in_2_not_1": in_2_not_1,
            "in_both": in_both,
            "match": len(in_1_not_2) == 0 and len(in_2_not_1) == 0,
        }


# --------------------------------------------------------------------------- #
# Utility functions
# --------------------------------------------------------------------------- #

def compute_bracket_depth(grammar: Grammar) -> int:
    """Estimate the maximum nesting depth of a grammar.

    This computes the longest chain of non-terminal references
    (A → B → C → …) from the start symbol, giving a rough measure of
    the grammar's structural complexity.
    """
    visited: Set[str] = set()
    def depth(nt: str) -> int:
        if nt in visited:
            return 0  # cycle
        visited.add(nt)
        max_d = 0
        for rhs in grammar.rhs_options(nt):
            for sym in rhs:
                if grammar.is_nonterminal(sym):
                    max_d = max(max_d, 1 + depth(sym))
        visited.discard(nt)
        return max_d
    return depth(grammar.start)


def grammar_summary(grammar: Grammar) -> str:
    """Return a human-readable summary string of the grammar."""
    stats = grammar.stats()
    ll1 = is_ll1(grammar)
    follow = grammar.follow()
    lines = [
        f"Grammar: {grammar.name or '(unnamed)'}",
        f"  Start symbol: {grammar.start}",
        f"  Non-terminals: {stats.nonterminal_count}",
        f"  Terminals: {stats.terminal_count}",
        f"  Productions: {stats.production_count}",
        f"  Nullable: {stats.nullable_count} non-terminal(s)",
        f"  Max RHS length: {stats.max_rhs_length}",
        f"  Avg RHS length: {stats.avg_rhs_length:.2f}",
        f"  Unreachable: {sorted(stats.unreachable) or 'none'}",
        f"  Unproductive: {sorted(stats.unproductive) or 'none'}",
        f"  LL(1): {'yes' if ll1 else 'no'}",
        f"  Max nesting depth: {compute_bracket_depth(grammar)}",
        f"  FOLLOW sets:",
    ]
    for nt in sorted(grammar.productions):
        follows = sorted(follow.get(nt, set()))
        lines.append(f"    {nt}: {{ {', '.join(follows)} }}")
    return "\n".join(lines)