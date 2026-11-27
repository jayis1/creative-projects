# DFA Minimizer

A dependency-free deterministic finite automata toolkit. It validates automata, evaluates words, completes partial transition tables with a sink, removes unreachable states, minimizes with Hopcroft partition refinement, and finds shortest counterexamples to language equivalence.

## How it works

Missing transitions reject in the original partial automaton; `complete()` makes this explicit with a fresh sink. Minimization first completes, then partitions reachable states into accepting/non-accepting classes and repeatedly splits classes according to their transitions. `distinguishing_word()` performs breadth-first search over pairs of states, so any returned witness is shortest.

## Usage

```python
from dfa import DFA

a = DFA(frozenset({'even', 'odd'}), frozenset({'1'}), 'even', frozenset({'even'}),
        {('even', '1'): 'odd', ('odd', '1'): 'even'})
print(a.accepts('111'))           # False
minimal = a.minimize()
print(minimal.states)             # frozenset({'q0', 'q1'})
```

The library also provides `complement()` (over the declared alphabet) and `product(other, operation='intersection')`; use `operation='union'` for union. Products account for disjoint alphabets by treating unavailable symbols as implicit rejecting transitions.

```python
not_a = a.complement()
both = a.product(other, 'intersection')
either = a.product(other, 'union')
```

Run tests with `python3 -m pytest -q` from this directory. Python 3.10+; standard library only for runtime (pytest for tests).

## Limitations

Symbols are single Python characters when using `accepts(str)`. DFA transition mappings use `(state, symbol)` keys. Equivalence treats a symbol absent from one alphabet as an implicit rejecting transition.
