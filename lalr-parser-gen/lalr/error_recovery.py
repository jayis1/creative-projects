"""Error recovery strategies for the LR parser.

This module provides error recovery mechanisms that allow the parser
to continue after encountering a syntax error, collecting multiple
errors in a single parse rather than stopping at the first one.

Strategies implemented:
    - Panic mode: skip tokens until a known synchronization point is reached
    - Error productions: yacc-style ``error`` pseudo-terminal in grammar rules
    - Error collection: accumulate errors and continue parsing

Usage::

    from lalr import Grammar, LALRTable, Token
    from lalr.error_recovery import RecoveringParser

    grammar = Grammar([...])
    table = LALRTable(grammar)
    parser = RecoveringParser(grammar, table=table)
    errors = []
    result = parser.parse(tokens, on_error=errors.append)
    if errors:
        for e in errors:
            print(f"Error at position {e.position}: {e.message}")
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Set

from .parser import ParseError, Parser, Token

logger = logging.getLogger(__name__)


class ParseErrorEntry:
    """A collected parse error entry."""

    def __init__(
        self,
        message: str,
        position: int = -1,
        state: int = -1,
        expected: Optional[List[str]] = None,
        skipped: int = 0,
    ) -> None:
        self.message = message
        self.position = position
        self.state = state
        self.expected = expected or []
        self.skipped = skipped  # number of tokens skipped during recovery

    def __str__(self) -> str:
        parts = [self.message]
        if self.position >= 0:
            parts.append(f"at position {self.position}")
        if self.state >= 0:
            parts.append(f"in state {self.state}")
        if self.expected:
            parts.append(f"expected one of: {', '.join(sorted(self.expected))}")
        if self.skipped:
            parts.append(f"(recovered by skipping {self.skipped} tokens)")
        return " ".join(parts)

    def __repr__(self) -> str:
        return f"ParseErrorEntry({self.message!r}, pos={self.position})"


class RecoveringParser(Parser):
    """LR parser with panic-mode error recovery.

    When a syntax error is encountered, the parser:
    1. Records the error.
    2. Discards tokens until it finds one that has a valid action in the
       current state (synchronization token).
    3. If no valid action exists in the current state, pops states from
       the stack until a state that can handle the token is found.
    4. Continues parsing.

    This allows collecting multiple errors in a single parse pass.
    """

    def __init__(
        self,
        grammar: Any,
        table: Optional[Any] = None,
        actions: Optional[Dict[int, Callable[[List[Any]], Any]]] = None,
        on_shift: Optional[Callable[[Token, int], None]] = None,
        sync_tokens: Optional[Set[str]] = None,
        max_errors: int = 50,
    ) -> None:
        super().__init__(grammar, table=table, actions=actions, on_shift=on_shift)
        self.sync_tokens: Set[str] = sync_tokens or set()
        self.max_errors = max_errors
        self.errors: List[ParseErrorEntry] = []

    def parse(
        self,
        tokens: List[Token],
        on_error: Optional[Callable[[ParseErrorEntry], None]] = None,
    ) -> Any:
        """Parse with error recovery.

        Args:
            tokens: Input token list.
            on_error: Optional callback invoked for each error encountered.
                If not provided, errors are collected in self.errors.

        Returns:
            The semantic value of the start symbol, or None if parsing
            could not complete due to excessive errors.
        """
        self.errors = []
        tokens = list(tokens) + [Token("$", value=None, position=-1)]

        state_stack: List[int] = [0]
        value_stack: List[Any] = []
        pos_stack: List[int] = []
        ip = 0
        error_count = 0

        while ip < len(tokens):
            if not state_stack:
                # State stack empty — recovery emptied it.
                # If the current token is EOF, give up.
                if tokens[ip].type == "$":
                    break
                # Re-initialize to state 0
                state_stack.append(0)
                value_stack.clear()
                pos_stack.clear()
                logger.warning("State stack emptied during recovery, reinitializing to state 0")
            state = state_stack[-1]
            current_token = tokens[ip]
            action_type, action_arg = self.table.get_action(
                state, current_token.type
            )

            if action_type == "shift":
                state_stack.append(action_arg)
                value_stack.append(current_token.value)
                pos_stack.append(current_token.position)
                if self.on_shift:
                    self.on_shift(current_token, action_arg)
                ip += 1

            elif action_type == "reduce":
                prod = self.grammar.production_by_index(action_arg)
                n = len(prod.body)
                if n > 0:
                    children = value_stack[-n:]
                    positions = pos_stack[-n:]
                    del value_stack[-n:]
                    del pos_stack[-n:]
                    del state_stack[-n:]
                else:
                    children = []
                    positions = []

                if action_arg in self.actions:
                    val = self.actions[action_arg](children)
                else:
                    val = children[0] if len(children) == 1 else children

                value_stack.append(val)
                pos_stack.append(
                    positions[0] if positions else current_token.position
                )

                top_state = state_stack[-1]
                goto_state = self.table.get_goto(top_state, prod.head)
                if goto_state < 0:
                    # This shouldn't happen in a valid table, but handle it
                    entry = ParseErrorEntry(
                        f"GOTO error: no transition from state {top_state} "
                        f"on non-terminal '{prod.head}'",
                        position=current_token.position,
                        state=top_state,
                    )
                    self._report_error(entry, on_error)
                    error_count += 1
                    if error_count >= self.max_errors:
                        return None
                    # Try recovery
                    state_stack.pop()
                    if state_stack:
                        continue
                    return None
                state_stack.append(goto_state)

            elif action_type == "accept":
                return value_stack[-1] if value_stack else None

            else:
                # Error — attempt recovery
                expected = [
                    t for t in self.grammar.terminals
                    if self.table.get_action(state, t)[0] != "error"
                ]
                entry = ParseErrorEntry(
                    f"Unexpected token '{current_token.type}'",
                    position=current_token.position,
                    state=state,
                    expected=expected,
                )
                self._report_error(entry, on_error)
                error_count += 1
                if error_count >= self.max_errors:
                    logger.error("Max errors (%d) exceeded, aborting parse",
                                 self.max_errors)
                    return None

                # Panic mode recovery
                ip = self._panic_recover(
                    tokens, ip, state_stack, value_stack, pos_stack
                )

        return value_stack[-1] if value_stack else None

    def _report_error(
        self,
        entry: ParseErrorEntry,
        on_error: Optional[Callable[[ParseErrorEntry], None]],
    ) -> None:
        self.errors.append(entry)
        logger.warning("Parse error: %s", entry)
        if on_error is not None:
            on_error(entry)

    def _panic_recover(
        self,
        tokens: List[Token],
        ip: int,
        state_stack: List[int],
        value_stack: List[Any],
        pos_stack: List[int],
    ) -> int:
        """Panic mode recovery: skip tokens and pop states.

        Returns the new input pointer position. Always advances at
        least one token to prevent infinite loops.
        """
        skipped = 0
        original_ip = ip

        # Phase 1: Pop states until we find one that has a valid action
        # for the current token, or until the stack is empty.
        # Do NOT return on sync token match here — we need to advance
        # to the sync token first (Phase 2 handles that).
        while state_stack and ip < len(tokens):
            state = state_stack[-1]
            current_token = tokens[ip]
            action_type, _ = self.table.get_action(state, current_token.type)
            if action_type != "error":
                # Current state can handle the current token — resume
                if skipped and self.errors:
                    self.errors[-1].skipped = skipped
                return ip
            # Current state can't handle this token — pop it
            state_stack.pop()
            if value_stack:
                value_stack.pop()
            if pos_stack:
                pos_stack.pop()

        # Phase 2: Skip tokens until we find one with a valid action
        # in any remaining state on the stack.
        # If the stack is empty, reinitialize to state 0.
        if not state_stack:
            state_stack.append(0)
            value_stack.clear()
            pos_stack.clear()

        while ip < len(tokens):
            current_token = tokens[ip]
            if current_token.type == "$":
                # End of input — give up, but consume the $ to signal done
                if skipped and self.errors:
                    self.errors[-1].skipped = skipped
                return ip + 1  # advance past $ to end the main loop

            # Check all states on the stack
            for state in reversed(state_stack):
                action_type, _ = self.table.get_action(
                    state, current_token.type
                )
                if action_type != "error":
                    if skipped and self.errors:
                        self.errors[-1].skipped = skipped
                    return ip

            # Check sync tokens: if the current token is a sync token,
            # check if any state on the stack can handle it
            if self.sync_tokens and current_token.type in self.sync_tokens:
                for state in reversed(state_stack):
                    act_type, _ = self.table.get_action(
                        state, current_token.type
                    )
                    if act_type != "error":
                        if skipped and self.errors:
                            self.errors[-1].skipped = skipped
                        return ip

            # Skip this token and try the next one
            skipped += 1
            ip += 1

        if skipped and self.errors:
            self.errors[-1].skipped = skipped
        return ip