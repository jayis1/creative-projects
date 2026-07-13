"""SLR(1) table builder for comparison with LALR(1).

SLR(1) uses FOLLOW sets for reduce actions instead of precise LALR(1)
lookaheads.  This is useful for demonstrating why LALR(1) is more
powerful and for educational comparison.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from .grammar import EPSILON, Grammar
from .table import LR0Automaton


class SLRTable:
    """SLR(1) ACTION and GOTO tables.

    Uses FOLLOW(A) as the lookahead for reduce items A → α•.
    """

    def __init__(self, grammar: Grammar) -> None:
        self.grammar = grammar
        self.automaton = LR0Automaton(grammar)
        self.num_states = len(self.automaton.states)
        self.action: Dict[int, Dict[str, Tuple[str, int]]] = {}
        self.goto: Dict[int, Dict[str, int]] = {}
        self.conflicts: List[str] = []
        self._build_tables()

    def _build_tables(self) -> None:
        grammar = self.grammar
        for idx in range(self.num_states):
            self.action[idx] = {}
            self.goto[idx] = {}
            state = self.automaton.get_state(idx)

            for item in state:
                sym = item.next_symbol
                if sym is not None:
                    target = self.automaton.transitions.get(idx, {}).get(sym)
                    if target is not None:
                        if grammar.is_terminal(sym):
                            self._set_action(idx, sym, ("shift", target))
                        else:
                            self.goto[idx][sym] = target
                else:
                    if item.production.head == Grammar.AUGMENTED_START:
                        self._set_action(idx, "$", ("accept", 0))
                    else:
                        # SLR: use FOLLOW(head) as lookaheads
                        follow_set = grammar.follow.get(item.production.head, set())
                        for la in follow_set:
                            if la == EPSILON:
                                continue
                            self._set_action(
                                idx, la, ("reduce", item.production.index)
                            )

    def _set_action(
        self, state: int, terminal: str, action: Tuple[str, int]
    ) -> None:
        existing = self.action[state].get(terminal)
        if existing is None:
            self.action[state][terminal] = action
        elif existing != action:
            if existing[0] == "shift" and action[0] == "reduce":
                self.conflicts.append(
                    f"Shift/reduce conflict in state {state} on '{terminal}': "
                    f"shift to {existing[1]} vs reduce by prod {action[1]}"
                )
            elif existing[0] == "reduce" and action[0] == "shift":
                self.conflicts.append(
                    f"Shift/reduce conflict in state {state} on '{terminal}': "
                    f"reduce by prod {existing[1]} vs shift to {action[1]}"
                )
            elif existing[0] == "reduce" and action[0] == "reduce":
                self.conflicts.append(
                    f"Reduce/reduce conflict in state {state} on '{terminal}': "
                    f"prod {existing[1]} vs prod {action[1]}"
                )
            # Keep the first action (standard: prefer shift over reduce)
            if existing[0] == "shift":
                pass  # keep shift
            elif action[0] == "shift":
                self.action[state][terminal] = action
            elif existing[1] > action[1]:
                self.action[state][terminal] = action

    @property
    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0

    def summary(self) -> str:
        lines = [
            f"SLR(1) Table: {self.num_states} states, "
            f"{len(self.grammar.productions)} productions",
        ]
        if self.has_conflicts:
            lines.append(f"Conflicts ({len(self.conflicts)}):")
            for c in self.conflicts:
                lines.append(f"  {c}")
        else:
            lines.append("No conflicts — grammar is SLR(1).")
        return "\n".join(lines)