"""Deterministic finite automata algorithms: completion, minimization, and products."""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class DFA:
    states: frozenset[str]
    alphabet: frozenset[str]
    start: str
    accepting: frozenset[str]
    transitions: dict[tuple[str, str], str]

    def __post_init__(self):
        if self.start not in self.states:
            raise ValueError("start state is not declared")
        if not self.accepting <= self.states:
            raise ValueError("accepting state is not declared")
        for (state, symbol), target in self.transitions.items():
            if state not in self.states or target not in self.states or symbol not in self.alphabet:
                raise ValueError("transition references undeclared state or symbol")

    def accepts(self, word: str) -> bool:
        state = self.start
        for symbol in word:
            if symbol not in self.alphabet:
                return False
            state = self.transitions.get((state, symbol))
            if state is None:
                return False
        return state in self.accepting

    def complete(self) -> "DFA":
        """Return an equivalent total DFA, routing absent edges to a sink."""
        missing = [(s, a) for s in self.states for a in self.alphabet if (s, a) not in self.transitions]
        if not missing:
            return self
        sink = "__sink__"
        while sink in self.states:
            sink += "_"
        states = self.states | {sink}
        transitions = dict(self.transitions)
        for state in self.states:
            for symbol in self.alphabet:
                transitions.setdefault((state, symbol), sink)
        for symbol in self.alphabet:
            transitions[sink, symbol] = sink
        return DFA(states, self.alphabet, self.start, self.accepting, transitions)

    def reachable(self) -> frozenset[str]:
        seen = {self.start}
        queue = deque([self.start])
        while queue:
            state = queue.popleft()
            for symbol in self.alphabet:
                target = self.transitions.get((state, symbol))
                if target is not None and target not in seen:
                    seen.add(target); queue.append(target)
        return frozenset(seen)

    def minimize(self) -> "DFA":
        """Hopcroft partition refinement, omitting unreachable states first."""
        dfa = self.complete()
        reachable = dfa.reachable()
        finals = dfa.accepting & reachable
        nonfinals = reachable - finals
        blocks = [b for b in (finals, nonfinals) if b]
        work = [min(blocks, key=len)] if blocks else []
        while work:
            splitter = work.pop()
            for symbol in sorted(dfa.alphabet):
                predecessors = frozenset(s for s in reachable if dfa.transitions[s, symbol] in splitter)
                updated = []
                for block in blocks:
                    left, right = block & predecessors, block - predecessors
                    if left and right:
                        updated.extend((left, right))
                        if block in work:
                            work.remove(block); work.extend((left, right))
                        else:
                            work.append(left if len(left) <= len(right) else right)
                    else:
                        updated.append(block)
                blocks = updated
        # Canonical names make results reproducible and easy to compare.
        ordered = sorted(blocks, key=lambda b: (0 if dfa.start in b else 1, min(b)))
        names = {state: f"q{i}" for i, block in enumerate(ordered) for state in block}
        transitions = {(names[next(iter(block))], a): names[dfa.transitions[next(iter(block)), a]]
                       for block in ordered for a in sorted(dfa.alphabet)}
        states = frozenset(f"q{i}" for i in range(len(ordered)))
        accepting = frozenset(names[s] for s in finals)
        return DFA(states, dfa.alphabet, names[dfa.start], accepting, transitions)

    def complement(self) -> "DFA":
        """Return the language complement over this DFA's declared alphabet."""
        total = self.complete()
        return DFA(total.states, total.alphabet, total.start,
                   total.states - total.accepting, total.transitions)

    def product(self, other: "DFA", operation: str = "intersection") -> "DFA":
        """Build a reachable product DFA for intersection or union."""
        if operation not in {"intersection", "union"}:
            raise ValueError("operation must be 'intersection' or 'union'")
        alphabet = self.alphabet | other.alphabet
        # Missing symbols and transitions lead to independent rejecting sinks.
        left = self.complete(); right = other.complete()
        l_sink, r_sink = "__implicit_left__", "__implicit_right__"
        while l_sink in left.states: l_sink += "_"
        while r_sink in right.states: r_sink += "_"
        def step(machine: "DFA", sink: str, state: str, symbol: str) -> str:
            if state == sink or symbol not in machine.alphabet:
                return sink
            return machine.transitions.get((state, symbol), sink)
        start_pair = (left.start, right.start)
        pairs = {start_pair}; queue = deque([start_pair]); transitions = {}
        while queue:
            pair = queue.popleft()
            for symbol in alphabet:
                target = (step(left, l_sink, pair[0], symbol), step(right, r_sink, pair[1], symbol))
                transitions[(pair, symbol)] = target
                if target not in pairs:
                    pairs.add(target); queue.append(target)
        names = {pair: f"p{i}" for i, pair in enumerate(sorted(pairs, key=repr))}
        finals = set()
        for pair in pairs:
            accepted = ((pair[0] in left.accepting) and (pair[1] in right.accepting))
            if operation == "union":
                accepted = pair[0] in left.accepting or pair[1] in right.accepting
            if accepted: finals.add(names[pair])
        return DFA(frozenset(names.values()), alphabet, names[start_pair], frozenset(finals),
                   {(names[pair], symbol): names[target] for (pair, symbol), target in transitions.items()})

    def distinguishing_word(self, other: "DFA") -> str | None:
        """Shortest word on the union alphabet with differing acceptance; None if equivalent."""
        alphabet = self.alphabet | other.alphabet
        start = (self.start, other.start, "")
        queue = deque([start]); seen = {(self.start, other.start)}
        while queue:
            left, right, word = queue.popleft()
            if (left in self.accepting) != (right in other.accepting):
                return word
            for symbol in sorted(alphabet):
                nl = self.transitions.get((left, symbol)) if symbol in self.alphabet else None
                nr = other.transitions.get((right, symbol)) if symbol in other.alphabet else None
                pair = (nl, nr)
                if pair not in seen:
                    seen.add(pair); queue.append((nl, nr, word + symbol))
        return None
