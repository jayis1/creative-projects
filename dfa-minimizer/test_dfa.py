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


def test_complement_and_product_over_mixed_alphabets():
    ends_a = sample()
    only_b = DFA(frozenset({'s', 'f'}), frozenset({'b'}), 's', frozenset({'f'}),
                 {('s', 'b'): 'f', ('f', 'b'): 'f'})
    complement = ends_a.complement()
    intersection = ends_a.product(only_b)
    union = ends_a.product(only_b, 'union')
    for word in ('', 'a', 'b', 'ab', 'bb', 'ba'):
        assert complement.accepts(word) == (not ends_a.accepts(word))
        assert intersection.accepts(word) == (ends_a.accepts(word) and only_b.accepts(word))
        assert union.accepts(word) == (ends_a.accepts(word) or only_b.accepts(word))


def test_invalid_product_operation_is_rejected():
    try:
        sample().product(sample(), 'xor')
    except ValueError:
        pass
    else:
        raise AssertionError('invalid operation should be rejected')