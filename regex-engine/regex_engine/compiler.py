"""
Compiler — compiles the parsed regex AST into an NFA using Thompson's construction.

Based on Russ Cox's "Regular Expression Matching Can Be Simple And Fast":
  - Each regex node compiles into a constant number of NFA states
  - Total states = O(n) where n is the pattern length
  - Two-list simulation gives O(nm) matching time
"""

from __future__ import annotations
from typing import Optional

from .parser import (ASTNode, Literal, Dot, AnchorStart, AnchorEnd,
                     CharClass, Shorthand, Concat, Alternation,
                     Quantified, Group)
from .nfa import State, Fragment, patch, append_outs


def _check_shorthand(ch: str, kind: str) -> bool:
    """Check if a character matches a shorthand class."""
    if kind == 'digit':
        return ch.isdigit()
    elif kind == 'word':
        return ch.isalnum() or ch == '_'
    elif kind == 'space':
        return ch in ' \t\n\r\f\v'
    return False


class Compiler:
    """Compiles a regex AST into an NFA."""

    def compile(self, ast: ASTNode) -> State:
        """Compile AST and return the NFA start state.

        Returns the start state. The NFA has exactly one match state
        reachable from any accepting path.
        """
        frag = self._compile_node(ast)
        match_state = State.match_state()
        patch(frag.outs, match_state)
        return frag.start

    def _compile_node(self, node: ASTNode) -> Fragment:
        if isinstance(node, Literal):
            return self._compile_literal(node)
        elif isinstance(node, Dot):
            return self._compile_dot()
        elif isinstance(node, AnchorStart):
            return self._compile_anchor_start()
        elif isinstance(node, AnchorEnd):
            return self._compile_anchor_end()
        elif isinstance(node, CharClass):
            return self._compile_char_class(node)
        elif isinstance(node, Shorthand):
            return self._compile_shorthand(node)
        elif isinstance(node, Concat):
            return self._compile_concat(node)
        elif isinstance(node, Alternation):
            return self._compile_alternation(node)
        elif isinstance(node, Quantified):
            return self._compile_quantified(node)
        elif isinstance(node, Group):
            return self._compile_node(node.child)
        else:
            raise ValueError(f"Unknown AST node: {type(node)}")

    def _compile_literal(self, node: Literal) -> Fragment:
        s = State.char_state(lambda ch, c=node.char: ch == c)
        return Fragment(s, [(s, 'out2')])

    def _compile_dot(self) -> Fragment:
        s = State.char_state(lambda ch: ch is not None and ch != '\n')
        return Fragment(s, [(s, 'out2')])

    def _compile_anchor_start(self) -> Fragment:
        """Compile ^ anchor — matches at start of string or after newline."""
        s = State.anchor_start_state()
        return Fragment(s, [(s, 'out1')])

    def _compile_anchor_end(self) -> Fragment:
        """Compile $ anchor — matches at end of string or before newline."""
        s = State.anchor_end_state()
        return Fragment(s, [(s, 'out1')])

    def _compile_char_class(self, node: CharClass) -> Fragment:
        def match_class(ch):
            if ch is None:
                return False
            found = False
            for start, end in node.ranges:
                if start <= ch <= end:
                    found = True
                    break
            if not found:
                for c in node.chars:
                    if ch == c:
                        found = True
                        break
            if not found:
                for kind, positive in node.shorthands:
                    if _check_shorthand(ch, kind):
                        found = True
                        break
            return found if not node.negated else not found

        s = State.char_state(match_class)
        return Fragment(s, [(s, 'out2')])

    def _compile_shorthand(self, node: Shorthand) -> Fragment:
        # Map shorthand character to the kind name expected by _check_shorthand
        kind_map = {
            'd': 'digit', 'D': 'digit',
            'w': 'word', 'W': 'word',
            's': 'space', 'S': 'space',
        }
        kind_char = node.kind
        kind_name = kind_map[kind_char]
        is_upper = kind_char.isupper()

        def match_shorthand(ch):
            if ch is None:
                return False
            result = _check_shorthand(ch, kind_name)
            if is_upper:
                result = not result
            return result

        s = State.char_state(match_shorthand)
        return Fragment(s, [(s, 'out2')])

    def _compile_concat(self, node: Concat) -> Fragment:
        if not node.children:
            # Empty pattern — epsilon transition
            s = State(State.SPLIT)
            s.out1 = None
            s.out2 = None
            return Fragment(s, [(s, 'out1'), (s, 'out2')])

        frags = [self._compile_node(child) for child in node.children]
        # Wire each fragment's outs to the next fragment's start
        for i in range(len(frags) - 1):
            patch(frags[i].outs, frags[i + 1].start)
        return Fragment(frags[0].start, frags[-1].outs)

    def _compile_alternation(self, node: Alternation) -> Fragment:
        frags = [self._compile_node(child) for child in node.children]

        if len(frags) == 1:
            return frags[0]

        # Thompson construction for alternation:
        # For a|b:
        #   SPLIT(out1 -> a, out2 -> b)
        #   a's outs and b's outs are all dangling
        #
        # For a|b|c:
        #   SPLIT(out1 -> a, out2 -> SPLIT2)
        #   SPLIT2(out1 -> b, out2 -> c)
        #   a's outs, b's outs, c's outs are all dangling
        #
        # Key: no extra epsilon path — all paths go through actual content.

        all_outs = []

        if len(frags) == 2:
            # Simple case: a|b
            split = State(State.SPLIT)
            split.out1 = frags[0].start
            split.out2 = frags[1].start
            all_outs.extend(frags[0].outs)
            all_outs.extend(frags[1].outs)
            return Fragment(split, all_outs)

        # General case: chain of SPLIT states
        # Create (n-1) SPLIT states
        splits = [State(State.SPLIT) for _ in range(len(frags) - 1)]

        for i in range(len(splits)):
            splits[i].out1 = frags[i].start
            all_outs.extend(frags[i].outs)

            if i < len(splits) - 1:
                splits[i].out2 = splits[i + 1]
            else:
                # Last SPLIT: out2 goes to the last alternative
                splits[i].out2 = frags[-1].start
                all_outs.extend(frags[-1].outs)

        return Fragment(splits[0], all_outs)

    def _compile_quantified(self, node: Quantified) -> Fragment:
        min_count = node.min
        max_count = node.max
        greedy = node.greedy

        if max_count is not None and max_count == 0:
            # {0} — matches empty string
            s = State(State.SPLIT)
            s.out1 = None
            s.out2 = None
            return Fragment(s, [(s, 'out1'), (s, 'out2')])

        if min_count == 0 and max_count is None:
            return self._compile_star(node.child, greedy)
        elif min_count == 1 and max_count is None:
            return self._compile_plus(node.child, greedy)
        elif min_count == 0 and max_count == 1:
            return self._compile_optional(node.child, greedy)
        else:
            return self._compile_general(node.child, min_count, max_count, greedy)

    def _compile_star(self, child: ASTNode, greedy: bool) -> Fragment:
        """Compile a* pattern."""
        frag = self._compile_node(child)
        split = State(State.SPLIT)

        if greedy:
            split.out1 = frag.start
            split.out2 = None  # dangling — skip path
            patch(frag.outs, split)  # loop back
            return Fragment(split, [(split, 'out2')])
        else:
            split.out2 = frag.start
            split.out1 = None  # dangling — skip path
            patch(frag.outs, split)
            return Fragment(split, [(split, 'out1')])

    def _compile_plus(self, child: ASTNode, greedy: bool) -> Fragment:
        """Compile a+ pattern."""
        frag = self._compile_node(child)
        split = State(State.SPLIT)

        if greedy:
            split.out1 = frag.start
            split.out2 = None
        else:
            split.out2 = frag.start
            split.out1 = None

        patch(frag.outs, split)
        skip_attr = 'out2' if greedy else 'out1'
        return Fragment(frag.start, [(split, skip_attr)])

    def _compile_optional(self, child: ASTNode, greedy: bool) -> Fragment:
        """Compile a? pattern."""
        frag = self._compile_node(child)
        split = State(State.SPLIT)

        if greedy:
            split.out1 = frag.start
            split.out2 = None
            return Fragment(split, frag.outs + [(split, 'out2')])
        else:
            split.out2 = frag.start
            split.out1 = None
            return Fragment(split, frag.outs + [(split, 'out1')])

    def _compile_general(self, child: ASTNode, min_count: int,
                         max_count: Optional[int], greedy: bool) -> Fragment:
        """Compile a{n,m} pattern."""
        # Build min_count mandatory copies
        mandatory_frags = []
        for _ in range(min_count):
            mandatory_frags.append(self._compile_node(child))

        if max_count is None:
            # {n,} — mandatory n copies then a*
            star_frag = self._compile_star(child, greedy)
            if mandatory_frags:
                # Wire mandatory copies in sequence
                for i in range(len(mandatory_frags) - 1):
                    patch(mandatory_frags[i].outs, mandatory_frags[i + 1].start)
                # Wire last mandatory to star
                patch(mandatory_frags[-1].outs, star_frag.start)
                return Fragment(mandatory_frags[0].start, star_frag.outs)
            else:
                return star_frag

        if max_count == min_count:
            # {n} — exactly n copies
            if not mandatory_frags:
                s = State(State.SPLIT)
                s.out1 = None
                s.out2 = None
                return Fragment(s, [(s, 'out1'), (s, 'out2')])
            for i in range(len(mandatory_frags) - 1):
                patch(mandatory_frags[i].outs, mandatory_frags[i + 1].start)
            return Fragment(mandatory_frags[0].start, mandatory_frags[-1].outs)

        # {n,m} — mandatory n copies then (m-n) optional copies
        optional_count = max_count - min_count

        if not mandatory_frags:
            # min_count == 0
            all_frags = [self._compile_optional(child, greedy) for _ in range(optional_count)]
            if len(all_frags) == 1:
                return all_frags[0]
            for i in range(len(all_frags) - 1):
                patch(all_frags[i].outs, all_frags[i + 1].start)
            return Fragment(all_frags[0].start, all_frags[-1].outs)

        # Wire mandatory copies
        for i in range(len(mandatory_frags) - 1):
            patch(mandatory_frags[i].outs, mandatory_frags[i + 1].start)

        # Add optional copies
        current_start = mandatory_frags[0].start
        current_outs = mandatory_frags[-1].outs

        for _ in range(optional_count):
            opt_frag = self._compile_optional(child, greedy)
            patch(current_outs, opt_frag.start)
            current_outs = opt_frag.outs

        return Fragment(current_start, current_outs)