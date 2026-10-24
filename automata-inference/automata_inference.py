"""Infer a compact deterministic finite automaton from labeled examples.

The learner builds an augmented prefix tree acceptor and applies the classic
RPNI red/blue state-merging procedure. It is intended for small, finite sample
sets, not as a guarantee of identifying an unknown language from finite data.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Iterable


@dataclass
class State:
    """A DFA state with labeled outgoing transitions."""
    accepting: bool = False
    transitions: dict[str, int] = field(default_factory=dict)


@dataclass
class DFA:
    """A deterministic finite automaton over single-character symbols."""
    states: list[State]
    start: int = 0

    def accepts(self, word: str) -> bool:
        state = self.start
        for symbol in word:
            nxt = self.states[state].transitions.get(symbol)
            if nxt is None:
                return False
            state = nxt
        return self.states[state].accepting

    def accepts_many(self, words: Iterable[str]) -> list[bool]:
        """Classify a sequence of words in input order."""
        return [self.accepts(word) for word in words]

    def distinguishing_word(self, other: "DFA") -> str | None:
        """Return a shortest word on which two DFAs disagree, or None if equivalent."""
        alphabet = sorted({ch for machine in (self, other) for state in machine.states
                           for ch in state.transitions})
        start = (self.start, other.start)
        queue = deque([(start, "")])
        seen = {start}
        while queue:
            (left, right), prefix = queue.popleft()
            left_accepts = left >= 0 and self.states[left].accepting
            right_accepts = right >= 0 and other.states[right].accepting
            if left_accepts != right_accepts:
                return prefix
            for symbol in alphabet:
                a = self.states[left].transitions.get(symbol, -1) if left >= 0 else -1
                b = other.states[right].transitions.get(symbol, -1) if right >= 0 else -1
                pair = (a, b)
                if pair not in seen:
                    seen.add(pair)
                    queue.append((pair, prefix + symbol))
        return None

    def to_dict(self) -> dict:
        """Return a stable JSON-compatible representation."""
        return {"start": self.start, "accepting": [i for i, s in enumerate(self.states) if s.accepting],
                "transitions": {str(i): dict(sorted(s.transitions.items()))
                                for i, s in enumerate(self.states) if s.transitions}}

    def minimize(self) -> "DFA":
        """Return an equivalent DFA using partition refinement."""
        alphabet = sorted({c for state in self.states for c in state.transitions})
        reachable = _reachable(self)
        if not reachable:
            return DFA([State(False)])
        # Complete only conceptually: missing edges go to a rejecting sink.
        sink = len(self.states)
        groups = [{i for i in reachable if self.states[i].accepting},
                  {i for i in reachable if not self.states[i].accepting}, {sink}]
        groups = [g for g in groups if g]
        changed = True
        while changed:
            changed = False
            owner = {s: n for n, group in enumerate(groups) for s in group}
            refined = []
            for group in groups:
                buckets: dict[tuple[int, ...], set[int]] = {}
                for state in group:
                    signature = tuple(owner.get(self.states[state].transitions.get(ch, sink), owner.get(sink))
                                      if state != sink else owner.get(sink) for ch in alphabet)
                    buckets.setdefault(signature, set()).add(state)
                refined.extend(buckets.values())
                changed |= len(buckets) > 1
            groups = refined
        owner = {s: n for n, group in enumerate(groups) for s in group}
        result = [State(any(s != sink and self.states[s].accepting for s in group)) for group in groups]
        for n, group in enumerate(groups):
            representative = next(iter(group))
            if representative == sink:
                continue
            for ch, target in self.states[representative].transitions.items():
                if target in owner:
                    result[n].transitions[ch] = owner[target]
        return DFA(result, owner[self.start])


def _reachable(dfa: DFA) -> set[int]:
    seen = {dfa.start}
    todo = [dfa.start]
    while todo:
        state = todo.pop()
        for target in dfa.states[state].transitions.values():
            if target not in seen:
                seen.add(target)
                todo.append(target)
    return seen


def _compatible(states: list[State], red: int, blue: int) -> list[State] | None:
    """Attempt recursive deterministic merge; None means conflicting labels."""
    merged = [State(s.accepting, dict(s.transitions)) for s in states]
    queue = [(red, blue)]
    seen: set[tuple[int, int]] = set()
    while queue:
        a, b = queue.pop()
        if (a, b) in seen:
            continue
        seen.add((a, b))
        if merged[a].accepting != merged[b].accepting:
            # RPNI consistency: positive and negative examples may not collapse.
            if merged[a].accepting or merged[b].accepting:
                return None
        merged[a].accepting = merged[a].accepting or merged[b].accepting
        for symbol, target_b in list(merged[b].transitions.items()):
            target_a = merged[a].transitions.get(symbol)
            if target_a is None:
                merged[a].transitions[symbol] = target_b
            else:
                queue.append((target_a, target_b))
    # Redirect all references through representative map, then remove merged states.
    parent = list(range(len(merged)))
    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    # Recreate equivalences from recursive merge pairs.
    for a, b in seen:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    roots = sorted({find(i) for i in range(len(merged))})
    remap = {root: i for i, root in enumerate(roots)}
    compact = [State(merged[root].accepting) for root in roots]
    for root in roots:
        for symbol, target in merged[root].transitions.items():
            compact[remap[root]].transitions[symbol] = remap[find(target)]
    return compact


def infer(positive: Iterable[str], negative: Iterable[str]) -> DFA:
    """Infer a DFA using RPNI from positive and negative word samples.

    Raises ValueError for contradictory labels or non-string samples.
    The empty string is a valid sample; symbols are Unicode code points.
    """
    positives, negatives = list(positive), list(negative)
    if any(not isinstance(word, str) for word in positives + negatives):
        raise ValueError("all samples must be strings")
    if set(positives) & set(negatives):
        raise ValueError("a sample cannot be both positive and negative")
    states = [State()]
    for word in positives + negatives:
        current = 0
        for symbol in word:
            if symbol not in states[current].transitions:
                states[current].transitions[symbol] = len(states)
                states.append(State())
            current = states[current].transitions[symbol]
        if word in positives:
            states[current].accepting = True
    red = {0}
    blue = {target for target in states[0].transitions.values()}
    while blue:
        candidate = min(blue)
        merged = None
        for representative in sorted(red):
            trial = _compatible(states, representative, candidate)
            if trial is not None and all(_classify(trial, word) for word in positives) and not any(
                    _classify(trial, word) for word in negatives):
                merged = (representative, trial)
                break
        if merged:
            representative, states = merged
            # Any state redirected into representative is no longer blue/red.
            red = {i for i in red if i < len(states)}
            red.add(representative)
            blue = {t for i in red for t in states[i].transitions.values()} - red
        else:
            red.add(candidate)
            blue.update(states[candidate].transitions.values())
            blue.difference_update(red)
    return _compact(states)


def _classify(states: list[State], word: str) -> bool:
    state = 0
    for symbol in word:
        state = states[state].transitions.get(symbol, -1)
        if state < 0:
            return False
    return states[state].accepting


def _compact(states: list[State]) -> DFA:
    reachable = _reachable(DFA(states))
    order = [0] + sorted(reachable - {0})
    mapping = {old: new for new, old in enumerate(order)}
    compact = [State(states[old].accepting,
                     {ch: mapping[target] for ch, target in sorted(states[old].transitions.items())
                      if target in mapping}) for old in order]
    return DFA(compact)
