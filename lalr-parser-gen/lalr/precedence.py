"""Precedence and associativity declarations for conflict resolution.

Many real-world grammars are ambiguous but can be made usable by
declaring precedence and associativity for operators, similar to
yacc/bison.  This module implements that mechanism.

Precedence levels are numbered; higher numbers bind tighter.
Associativity can be 'left', 'right', or 'nonassoc'.

When a shift/reduce conflict occurs on a terminal with precedence:
  - If the terminal's precedence > the production's precedence → shift.
  - If the terminal's precedence < the production's precedence → reduce.
  - If equal:
      - left  → reduce
      - right → shift
      - nonassoc → error

A production's precedence is that of its rightmost terminal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .grammar import Grammar


@dataclass
class Precedence:
    """A precedence level with associativity."""

    level: int
    associativity: str  # 'left', 'right', 'nonassoc'
    terminals: List[str] = field(default_factory=list)


class PrecedenceTable:
    """Manages precedence and associativity for a grammar.

    Usage::

        prec = PrecedenceTable()
        prec.add_level(1, 'left', ['+'])
        prec.add_level(2, 'left', ['*'])
        prec.add_level(3, 'right', ['UMINUS'])  # unary minus pseudo-terminal
        prec.add_level(4, 'nonassoc', ['^'])
    """

    def __init__(self) -> None:
        self._levels: List[Precedence] = []
        self._terminal_level: Dict[str, int] = {}
        self._terminal_assoc: Dict[str, str] = {}
        # Production-specific precedence overrides from %prec directives.
        # Maps production index -> precedence level.
        self._production_overrides: Dict[int, int] = {}

    def add_production_override(self, prod_index: int, level: int) -> None:
        """Override a production's precedence level (from %prec directive)."""
        self._production_overrides[prod_index] = level

    def add_level(self, level: int, associativity: str, terminals: List[str]) -> None:
        if associativity not in ("left", "right", "nonassoc"):
            raise ValueError(
                f"Associativity must be 'left', 'right', or 'nonassoc', "
                f"got: {associativity!r}"
            )
        self._levels.append(Precedence(level, associativity, terminals))
        for t in terminals:
            self._terminal_level[t] = level
            self._terminal_assoc[t] = associativity

    def has_precedence(self, terminal: str) -> bool:
        return terminal in self._terminal_level

    def get_precedence(self, terminal: str) -> int:
        return self._terminal_level.get(terminal, -1)

    def get_associativity(self, terminal: str) -> Optional[str]:
        return self._terminal_assoc.get(terminal)

    def production_precedence(self, grammar: Grammar, prod_index: int) -> int:
        """Get the precedence of a production.

        If a %prec override was declared, use that.  Otherwise use the
        precedence of the rightmost terminal symbol in the body.
        """
        # Check for %prec override first
        if prod_index in self._production_overrides:
            return self._production_overrides[prod_index]
        prod = grammar.production_by_index(prod_index)
        for sym in reversed(prod.body):
            if self.has_precedence(sym):
                return self.get_precedence(sym)
        return -1

    def production_associativity(self, grammar: Grammar, prod_index: int) -> Optional[str]:
        """Get the associativity implied by a production's rightmost terminal."""
        prod = grammar.production_by_index(prod_index)
        for sym in reversed(prod.body):
            if self.has_precedence(sym):
                return self.get_associativity(sym)
        return None

    def resolve_conflict(
        self,
        grammar: Grammar,
        state: int,
        terminal: str,
        shift_action: Tuple[str, int],
        reduce_action: Tuple[str, int],
    ) -> Tuple[str, int]:
        """Resolve a shift/reduce conflict using precedence.

        Returns the winning action.  If no precedence applies, defaults
        to shift (the standard default).
        """
        term_prec = self.get_precedence(terminal)
        prod_prec = self.production_precedence(grammar, reduce_action[1])

        if term_prec < 0 and prod_prec < 0:
            # No precedence info — default to shift
            return shift_action

        if term_prec > prod_prec:
            return shift_action
        elif term_prec < prod_prec:
            return reduce_action
        else:
            # Equal precedence — use associativity
            assoc = self.get_associativity(terminal)
            if assoc == "left":
                return reduce_action
            elif assoc == "right":
                return shift_action
            elif assoc == "nonassoc":
                # Neither shift nor reduce — error
                return ("error", 0)
            return shift_action  # fallback

    @property
    def levels(self) -> List[Precedence]:
        return list(self._levels)

    def describe(self) -> str:
        lines = ["Precedence levels (low → high):"]
        for p in sorted(self._levels, key=lambda x: x.level):
            lines.append(
                f"  level {p.level}: {p.associativity:>8} — {', '.join(p.terminals)}"
            )
        return "\n".join(lines)