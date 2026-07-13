"""LR(0) / LALR(1) item and state construction.

This module implements the core LALR(1) table-building algorithm:

1. Compute LR(0) item sets (the "canonical LR(0) collection").
2. Compute lookahead sets for each item by propagating through the
   goto graph (DeRemer/Pennello style LALR lookahead propagation).
3. Build ACTION / GOTO tables.

The implementation favours clarity over micro-optimisation while still
being efficient enough for real-world grammars (hundreds of productions).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from .grammar import EPSILON, Grammar, Production


# --------------------------------------------------------------------------- #
# Items
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class LR0Item:
    """An LR(0) item: production *dot_position*.

    Attributes:
        production: the production rule.
        dot: index of the dot in the body (0..len(body)).
    """

    production: Production
    dot: int

    @property
    def is_reduce(self) -> bool:
        return self.dot >= len(self.production.body)

    @property
    def next_symbol(self) -> Optional[str]:
        if self.is_reduce:
            return None
        return self.production.body[self.dot]

    def advance(self) -> "LR0Item":
        if self.is_reduce:
            raise ValueError("Cannot advance a reduce item")
        return LR0Item(self.production, self.dot + 1)

    def __str__(self) -> str:  # pragma: no cover
        body = list(self.production.body)
        body.insert(self.dot, "•")
        rhs = " ".join(body) if body != ["•"] else "•"
        return f"{self.production.head} -> {rhs}"


@dataclass(frozen=True)
class LALR1Item:
    """An LALR(1) item: LR0Item + a lookahead terminal."""

    lr0: LR0Item
    lookahead: str

    @property
    def production(self) -> Production:
        return self.lr0.production

    @property
    def dot(self) -> int:
        return self.lr0.dot

    @property
    def is_reduce(self) -> bool:
        return self.lr0.is_reduce

    @property
    def next_symbol(self) -> Optional[str]:
        return self.lr0.next_symbol

    def advance(self) -> "LALR1Item":
        return LALR1Item(self.lr0.advance(), self.lookahead)

    def __str__(self) -> str:  # pragma: no cover
        return f"[{self.lr0}, {self.lookahead}]"


# --------------------------------------------------------------------------- #
# LR(0) automaton
# --------------------------------------------------------------------------- #
class LR0Automaton:
    """Builds the canonical collection of LR(0) item sets."""

    def __init__(self, grammar: Grammar) -> None:
        self.grammar = grammar
        self.states: List[FrozenSet[LR0Item]] = []
        self.state_index: Dict[FrozenSet[LR0Item], int] = {}
        self.transitions: Dict[int, Dict[str, int]] = {}
        self._build()

    def _closure(self, items: Set[LR0Item]) -> FrozenSet[LR0Item]:
        closure = set(items)
        queue = list(items)
        while queue:
            item = queue.pop()
            sym = item.next_symbol
            if sym is not None and self.grammar.is_nonterminal(sym):
                for prod in self.grammar.productions_for(sym):
                    new_item = LR0Item(prod, 0)
                    if new_item not in closure:
                        closure.add(new_item)
                        queue.append(new_item)
        return frozenset(closure)

    def _goto(self, items: FrozenSet[LR0Item], symbol: str) -> FrozenSet[LR0Item]:
        moved: Set[LR0Item] = set()
        for item in items:
            if item.next_symbol == symbol:
                moved.add(item.advance())
        if not moved:
            return frozenset()
        return self._closure(moved)

    def _build(self) -> None:
        start_item = LR0Item(self.grammar.start_production(), 0)
        initial = self._closure({start_item})
        self.states.append(initial)
        self.state_index[initial] = 0
        self.transitions[0] = {}
        queue = [initial]
        while queue:
            current = queue.pop(0)
            current_idx = self.state_index[current]
            # Group items by next symbol
            symbols: Dict[str, Set[LR0Item]] = {}
            for item in current:
                sym = item.next_symbol
                if sym is not None:
                    symbols.setdefault(sym, set()).add(item)
            for sym, _items in symbols.items():
                target = self._goto(current, sym)
                if not target:
                    continue
                if target not in self.state_index:
                    self.state_index[target] = len(self.states)
                    self.states.append(target)
                    self.transitions[len(self.states) - 1] = {}
                    queue.append(target)
                self.transitions[current_idx][sym] = self.state_index[target]

    def get_state(self, idx: int) -> FrozenSet[LR0Item]:
        return self.states[idx]


# --------------------------------------------------------------------------- #
# LALR(1) lookahead computation
# --------------------------------------------------------------------------- #
class LALR1Builder:
    """Computes LALR(1) lookaheads via the DeRemer-Pennello propagation
    algorithm.

    The algorithm works in two passes per state:
    1. **Determine spontaneous generation**: for each item A → α•Bβ, the
       lookahead of B → •γ includes FIRST(β lookahead).
    2. **Propagate**: the lookahead of A → α•Bβ propagates to
       B → •γ and to A → αB•β (in the goto state).

    We iterate until a fixed point is reached.
    """

    def __init__(self, grammar: Grammar, automaton: LR0Automaton) -> None:
        self.grammar = grammar
        self.auto = automaton
        # lookahead sets keyed by (state_index, LR0Item)
        self.lookaheads: Dict[Tuple[int, LR0Item], Set[str]] = {}
        # propagation map: source (state, item) -> list of (state, item)
        self.propagates: Dict[
            Tuple[int, LR0Item], List[Tuple[int, LR0Item]]
        ] = {}
        self._init_lookaheads()
        self._build_propagation()
        self._propagate_fixpoint()

    def _init_lookaheads(self) -> None:
        for idx, state in enumerate(self.auto.states):
            for item in state:
                self.lookaheads[(idx, item)] = set()
        # Seed the augmented start item with $.
        start_item = LR0Item(self.grammar.start_production(), 0)
        self.lookaheads[(0, start_item)].add("$")

    def _build_propagation(self) -> None:
        """For each state and each item, compute spontaneous lookaheads
        and propagation targets."""
        for idx, state in enumerate(self.auto.states):
            for item in state:
                sym = item.next_symbol
                if sym is None:
                    continue
                # The lookahead we attach to generated/advanced items.
                # For LALR we use a special sentinel to detect propagation.
                # We compute with a "base" lookahead and see which items
                # in the goto state *inherit* it vs. get it spontaneously.
                key = (idx, item)
                # Determine the goto state for sym
                target_idx = self.auto.transitions.get(idx, {}).get(sym)
                if target_idx is None:
                    continue
                # For each item B -> •γ in closure of goto, if it came from
                # this item's advance, it's a propagation target.
                # For closure items generated by this non-terminal, we need
                # to distinguish spontaneous vs propagated.
                #
                # Standard technique: temporarily set lookahead to a unique
                # marker, compute closure, then check which items got it.
                marker = f"#MARK_{idx}_{item.production.index}_{item.dot}#"
                # Build the closure of {item.advance()} with marker lookahead
                self._compute_closure_lookahead(
                    item, idx, target_idx, marker, key
                )

    def _compute_closure_lookahead(
        self,
        item: LR0Item,
        source_state: int,
        target_state: int,
        marker: str,
        source_key: Tuple[int, LR0Item],
    ) -> None:
        """Compute spontaneous lookaheads and propagation for one source item."""
        grammar = self.grammar
        # Advanced item in goto state
        advanced = item.advance()
        # The lookahead for the advanced item is the same as source (propagation)
        # unless there's a beta after the non-terminal.
        #
        # For the source item A -> α•Bβ with lookahead la:
        #   - B -> •γ gets FIRST(β la) as spontaneous lookaheads (minus marker)
        #   - B -> •γ gets la via propagation if β is nullable (i.e., FIRST(β) contains ε)
        #   - A -> αB•β in goto gets la via propagation
        #
        # We detect propagation by giving the source a marker lookahead and
        # seeing which target items inherit it.

        body = item.production.body
        beta = body[item.dot + 1:] if item.dot + 1 < len(body) else ()
        sym = body[item.dot]  # the symbol after the dot

        # The "input" lookahead for this computation.
        # In the standard algorithm, we use the marker to detect propagation.
        # We simulate: closure of [A -> α•Bβ, marker] produces:
        #   [B -> •γ, FIRST(β marker)]
        # If marker appears in FIRST(β marker), that means β is nullable,
        # so the lookahead propagates → B -> •γ is a propagation target.
        # The non-marker terminals in FIRST(β marker) are spontaneous.

        # Compute FIRST(β) + marker if β nullable
        first_beta = grammar.first_of_string(beta)
        beta_nullable = EPSILON in first_beta
        spontaneous = first_beta - {EPSILON}

        if grammar.is_terminal(sym):
            # Goto on terminal: the advanced item propagates.
            target_key = (target_state, advanced)
            self.propagates.setdefault(source_key, []).append(target_key)
            return

        # sym is a non-terminal: B
        # 1. Advanced item A -> αB•β in GOTO(s, B) propagates from source.
        target_key = (target_state, advanced)
        self.propagates.setdefault(source_key, []).append(target_key)

        # 2. For each production B -> γ, the item B -> •γ is in the CLOSURE
        #    of the CURRENT state (source_state), not the goto state.
        #    It gets spontaneous lookaheads FIRST(β) minus ε, and
        #    propagation of la when β is nullable.
        for prod in grammar.productions_for(sym):
            new_lr0 = LR0Item(prod, 0)
            # B -> •γ lives in the closure of the source state
            closure_item_key = (source_state, new_lr0)
            if closure_item_key not in self.lookaheads:
                continue
            # Spontaneous lookaheads
            for la in spontaneous:
                self.lookaheads[closure_item_key].add(la)
            # Propagation if beta is nullable
            if beta_nullable:
                self.propagates.setdefault(source_key, []).append(
                    closure_item_key
                )

    def _propagate_fixpoint(self) -> None:
        """Iterate propagation until no changes."""
        changed = True
        while changed:
            changed = False
            for source_key, targets in self.propagates.items():
                source_lookaheads = self.lookaheads[source_key]
                if not source_lookaheads:
                    continue
                for target_key in targets:
                    before = len(self.lookaheads[target_key])
                    self.lookaheads[target_key] |= source_lookaheads
                    if len(self.lookaheads[target_key]) != before:
                        changed = True


# --------------------------------------------------------------------------- #
# Table construction
# --------------------------------------------------------------------------- #
class LALRTable:
    """ACTION and GOTO tables for an LALR(1) parser."""

    def __init__(self, grammar: Grammar) -> None:
        self.grammar = grammar
        self.automaton = LR0Automaton(grammar)
        self.lalr = LALR1Builder(grammar, self.automaton)
        self.num_states = len(self.automaton.states)
        # ACTION[state][terminal] = ('shift', state) | ('reduce', prod_idx) | ('accept',) | ('error',)
        self.action: Dict[int, Dict[str, Tuple[str, int]]] = {}
        # GOTO[state][nonterminal] = state
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
                    # Shift or goto
                    target = self.automaton.transitions.get(idx, {}).get(sym)
                    if target is not None:
                        if grammar.is_terminal(sym):
                            self._set_action(idx, sym, ("shift", target))
                        else:
                            self.goto[idx][sym] = target
                else:
                    # Reduce item
                    if item.production.head == Grammar.AUGMENTED_START:
                        la_set = self.lalr.lookaheads.get((idx, item), {"$"})
                        for la in la_set:
                            self._set_action(idx, la, ("accept", 0))
                    else:
                        la_set = self.lalr.lookaheads.get((idx, item), set())
                        for la in la_set:
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
            # Conflict!
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
            # else keep first reduce (lower production index)
            elif existing[1] > action[1]:
                self.action[state][terminal] = action

    @property
    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0

    def get_action(self, state: int, terminal: str) -> Tuple[str, int]:
        return self.action.get(state, {}).get(terminal, ("error", 0))

    def get_goto(self, state: int, nonterminal: str) -> int:
        return self.goto.get(state, {}).get(nonterminal, -1)

    def summary(self) -> str:
        lines = [
            f"LALR(1) Table: {self.num_states} states, "
            f"{len(self.grammar.productions)} productions",
        ]
        if self.has_conflicts:
            lines.append(f"Conflicts ({len(self.conflicts)}):")
            for c in self.conflicts:
                lines.append(f"  {c}")
        else:
            lines.append("No conflicts — grammar is LALR(1).")
        return "\n".join(lines)