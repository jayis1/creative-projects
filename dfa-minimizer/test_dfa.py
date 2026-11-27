from dfa import DFA


def sample():
    # Accept words over {a,b} ending in a.
    return DFA(frozenset({'start', 'end'}), frozenset({'a', 'b'}), 'start', frozenset({'end'}),
               {('start', 'a'): 'end', ('start', 'b'): 'start', ('end', 'a'): 'end', ('end', 'b'): 'start'})


def test_accepts_and_shortest_witness():
    dfa = sample()
    assert dfa.accepts('ba') and not dfa.accepts('ab')
    assert dfa.distinguishing_word(DFA(frozenset({'x'}), frozenset({'a','b'}), 'x', frozenset(), {('x','a'):'x',('x','b'):'x'})) == 'a'


def test_minimization_preserves_language_and_drops_unreachable():
    dfa = sample()
    assert dfa.minimize().states == frozenset({'q0', 'q1'})
    minimized = dfa.minimize()
    for word in ('', 'a', 'b', 'abba', 'bbab'):
        assert dfa.accepts(word) == minimized.accepts(word)


def test_completion_routes_missing_edges_to_sink():
    partial = DFA(frozenset({'s'}), frozenset({'a'}), 's', frozenset(), {})
    total = partial.complete()
    assert total.transitions['s', 'a'] != 's'
    assert not total.accepts('a')
