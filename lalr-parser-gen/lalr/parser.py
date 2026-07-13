"""LR parser driver — uses an LALR(1) table to parse token streams.

The parser is table-driven and supports semantic actions via a callback
mechanism.  Each production can have an associated ``action`` callable
that receives the reduced values and returns a semantic value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .grammar import Grammar
from .table import LALRTable


@dataclass
class ParseError(Exception):
    """Raised when the input cannot be parsed."""

    message: str
    position: int = -1
    expected: List[str] = field(default_factory=list)
    state: int = -1

    def __str__(self) -> str:
        parts = [self.message]
        if self.position >= 0:
            parts.append(f"at position {self.position}")
        if self.state >= 0:
            parts.append(f"in state {self.state}")
        if self.expected:
            parts.append(f"expected one of: {', '.join(sorted(self.expected))}")
        return " ".join(parts)


@dataclass
class Token:
    """A token produced by a lexer.

    Attributes:
        type: terminal symbol name (must match grammar terminal names).
        value: optional semantic value.
        position: source position for error reporting.
    """

    type: str
    value: Any = None
    position: int = -1

    def __repr__(self) -> str:  # pragma: no cover
        return f"Token({self.type!r}, {self.value!r})"


class Parser:
    """Table-driven LR parser.

    Parameters:
        grammar: the Grammar to parse with.
        table: optional pre-built LALR(1) table.  If None, one is built.
        actions: optional dict mapping production index -> callable.
            The callable receives a list of semantic values (one per
            symbol in the body) and returns the semantic value for the
            LHS.  If no action is provided, the default returns the list
            of values (or the single value for unit productions).
        on_shift: optional callback called with (token, new_state) on
            each shift.  Useful for building ASTs incrementally.
    """

    def __init__(
        self,
        grammar: Grammar,
        table: Optional[LALRTable] = None,
        actions: Optional[Dict[int, Callable[[List[Any]], Any]]] = None,
        on_shift: Optional[Callable[[Token, int], None]] = None,
    ) -> None:
        self.grammar = grammar
        self.table = table if table is not None else LALRTable(grammar)
        self.actions = actions or {}
        self.on_shift = on_shift
        # Allow overriding the default conflict resolution
        self.debug = False

    def parse(self, tokens: List[Token]) -> Any:
        """Parse a list of tokens and return the semantic value of the
        start symbol.

        Raises ParseError on syntax errors.
        """
        # Append EOF
        tokens = list(tokens) + [Token("$", value=None, position=-1)]

        state_stack: List[int] = [0]
        value_stack: List[Any] = []
        pos_stack: List[int] = []  # positions for error reporting

        ip = 0
        while True:
            state = state_stack[-1]
            current_token = tokens[ip]
            action_type, action_arg = self.table.get_action(
                state, current_token.type
            )

            if self.debug:
                print(
                    f"  state={state} token={current_token.type} "
                    f"action={action_type},{action_arg}"
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
                # Pop |body| symbols
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

                # Execute semantic action
                if action_arg in self.actions:
                    val = self.actions[action_arg](children)
                else:
                    val = children[0] if len(children) == 1 else children

                value_stack.append(val)
                pos_stack.append(
                    positions[0] if positions else current_token.position
                )

                # GOTO
                top_state = state_stack[-1]
                goto_state = self.table.get_goto(top_state, prod.head)
                if goto_state < 0:
                    raise ParseError(
                        f"GOTO error: no transition from state {top_state} "
                        f"on non-terminal '{prod.head}'",
                        position=current_token.position,
                        state=top_state,
                    )
                state_stack.append(goto_state)

                if self.debug:
                    print(f"    reduced by {prod}")

            elif action_type == "accept":
                return value_stack[-1] if value_stack else None

            else:
                # Error
                expected = [
                    t
                    for t in self.grammar.terminals
                    if self.table.get_action(state, t)[0] != "error"
                ]
                raise ParseError(
                    f"Unexpected token '{current_token.type}'",
                    position=current_token.position,
                    expected=expected,
                    state=state,
                )

    def parse_tokens(
        self, token_types: List[str], values: Optional[List[Any]] = None
    ) -> Any:
        """Convenience: parse from a list of token type strings."""
        if values is None:
            values = [None] * len(token_types)
        tokens = [
            Token(t, v, pos)
            for pos, (t, v) in enumerate(zip(token_types, values))
        ]
        return self.parse(tokens)