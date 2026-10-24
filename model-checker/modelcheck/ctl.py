"""CTL model checking over finite explicit-state transition systems."""
from dataclasses import dataclass
from .system import State, TransitionSystem

@dataclass(frozen=True)
class Formula:
    op: str
    args: tuple = ()

    @staticmethod
    def atom(name: str): return Formula('atom', (name,))
    @staticmethod
    def neg(a): return Formula('not', (a,))
    @staticmethod
    def both(a, b): return Formula('and', (a, b))
    @staticmethod
    def either(a, b): return Formula('or', (a, b))
    @staticmethod
    def EX(a): return Formula('EX', (a,))
    @staticmethod
    def AX(a): return Formula('AX', (a,))
    @staticmethod
    def EF(a): return Formula('EF', (a,))
    @staticmethod
    def AF(a): return Formula('AF', (a,))
    @staticmethod
    def EG(a): return Formula('EG', (a,))
    @staticmethod
    def AG(a): return Formula('AG', (a,))


def satisfying(ts: TransitionSystem, f: Formula) -> set[State]:
    """Compute the states satisfying f using CTL least/greatest fixed points."""
    all_states = set(ts.states)
    op, args = f.op, f.args
    if op == 'atom': return {s for s in all_states if args[0] in ts.labels.get(s, frozenset())}
    if op == 'not': return all_states - satisfying(ts, args[0])
    if op in ('and', 'or'):
        left, right = (satisfying(ts, x) for x in args)
        return left & right if op == 'and' else left | right
    if op in ('EX', 'AX'):
        target = satisfying(ts, args[0])
        return {s for s in all_states if (any if op == 'EX' else all)(t in target for t in ts.successors(s))}
    if op in ('EF', 'AF'):
        target = satisfying(ts, args[0]); result = set(target)
        while True:
            previous = result
            result = result | {s for s in all_states - result if (any if op == 'EF' else all)(t in result for t in ts.successors(s))}
            if result == previous: return result
    if op in ('EG', 'AG'):
        target = satisfying(ts, args[0]); result = set(target)
        while True:
            previous = result
            result = {s for s in result if (any if op == 'EG' else all)(t in result for t in ts.successors(s))}
            if result == previous: return result
    raise ValueError(f'unsupported CTL operator: {op}')


def check(ts: TransitionSystem, formula: Formula) -> bool:
    """Check whether the initial state satisfies formula."""
    return ts.initial in satisfying(ts, formula)
