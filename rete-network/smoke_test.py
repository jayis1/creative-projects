"""Smoke test for the Rete engine."""
from rete import Engine, Fact, Rule, Condition, Var, Const

def test_simple():
    eng = Engine()
    results = []
    eng.add_rule(Rule(
        name="greet",
        conditions=[Condition("person", name=Var("n"))],
        actions=[lambda b, e: results.append(f"Hello, {b['n']}!")],
    ))
    eng.assert_fact(Fact("person", name="Alice"))
    eng.assert_fact(Fact("person", name="Bob"))
    n = eng.run()
    assert n == 2, f"expected 2 firings, got {n}"
    assert "Hello, Alice!" in results
    assert "Hello, Bob!" in results
    print("test_simple: PASS")

def test_join():
    eng = Engine()
    results = []
    eng.add_rule(Rule(
        name="friends",
        conditions=[
            Condition("likes", a=Var("x"), b=Var("y")),
            Condition("likes", a=Var("y"), b=Var("x")),
        ],
        actions=[lambda b, e: results.append((b["x"], b["y"]))],
    ))
    eng.assert_fact(Fact("likes", a="alice", b="bob"))
    eng.assert_fact(Fact("likes", a="bob", b="alice"))
    n = eng.run()
    # Both orderings (alice→bob, bob→alice) are valid instantiations
    assert n == 2, f"expected 2 firings, got {n}"
    assert ("alice", "bob") in results
    assert ("bob", "alice") in results
    print("test_join: PASS")

def test_constant_filter():
    eng = Engine()
    results = []
    eng.add_rule(Rule(
        name="adult",
        conditions=[Condition("person", age=Const(25))],
        actions=[lambda b, e: results.append("found25")],
    ))
    eng.assert_fact(Fact("person", name="A", age=25))
    eng.assert_fact(Fact("person", name="B", age=30))
    n = eng.run()
    assert n == 1, f"expected 1, got {n}"
    print("test_constant_filter: PASS")

def test_retract():
    eng = Engine()
    results = []
    eng.add_rule(Rule(
        name="greet",
        conditions=[Condition("person", name=Var("n"))],
        actions=[lambda b, e: results.append(b["n"])],
    ))
    f = Fact("person", name="Alice")
    eng.assert_fact(f)
    eng.retract_fact(f)
    n = eng.run()
    assert n == 0, f"expected 0 after retract, got {n}"
    print("test_retract: PASS")

def test_negation():
    eng = Engine()
    results = []
    eng.add_rule(Rule(
        name="allow",
        conditions=[
            Condition("person", name=Var("n")),
            Condition("banned", name=Var("n"), negated=True),
        ],
        actions=[lambda b, e: results.append(b["n"])],
    ))
    eng.assert_fact(Fact("person", name="Alice"))
    eng.assert_fact(Fact("person", name="Bob"))
    eng.assert_fact(Fact("banned", name="Bob"))
    n = eng.run()
    assert n == 1, f"expected 1 (Alice only), got {n}"
    assert results == ["Alice"]
    print("test_negation: PASS")

def test_predicate():
    eng = Engine()
    results = []
    eng.add_rule(Rule(
        name="adult",
        conditions=[Condition("person", age=Var("a"),
                               predicate=lambda f, b: b["a"] >= 18)],
        actions=[lambda b, e: results.append(b["a"])],
    ))
    eng.assert_fact(Fact("person", name="A", age=15))
    eng.assert_fact(Fact("person", name="B", age=20))
    eng.assert_fact(Fact("person", name="C", age=30))
    n = eng.run()
    assert n == 2, f"expected 2, got {n}"
    assert sorted(results) == [20, 30]
    print("test_predicate: PASS")

if __name__ == "__main__":
    test_simple()
    test_join()
    test_constant_filter()
    test_retract()
    test_negation()
    test_predicate()
    print("ALL TESTS PASSED")