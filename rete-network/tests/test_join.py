"""Tests for multi-condition joins and variable binding."""
import pytest
from rete import Engine, Fact, Rule, Condition, Var, Const


class TestJoin:
    def test_self_join(self):
        """A rule that joins a condition with itself via shared variables."""
        eng = Engine()
        results = []
        eng.add_rule(Rule(
            name="self-match",
            conditions=[
                Condition("person", name=Var("x"), age=Var("a")),
                Condition("person", name=Var("y"), age=Var("a")),
            ],
            actions=[lambda b, e: results.append((b["x"], b["y"]))],
        ))
        eng.assert_fact(Fact("person", name="Alice", age=30))
        eng.assert_fact(Fact("person", name="Bob", age=30))
        eng.assert_fact(Fact("person", name="Carol", age=25))
        n = eng.run()
        # Alice-Alice, Alice-Bob, Bob-Alice, Bob-Bob, Carol-Carol
        assert n == 5

    def test_two_condition_join(self):
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
        assert n == 2
        assert ("alice", "bob") in results
        assert ("bob", "alice") in results

    def test_three_condition_chain(self):
        """Three conditions with chained variables — directed path A->B->C."""
        eng = Engine()
        results = []
        eng.add_rule(Rule(
            name="path",
            conditions=[
                Condition("edge", src=Var("a"), dst=Var("b")),
                Condition("edge", src=Var("b"), dst=Var("c")),
            ],
            actions=[lambda b, e: results.append((b["a"], b["b"], b["c"]))],
        ))
        # Path: A->B, B->C
        eng.assert_fact(Fact("edge", src="A", dst="B"))
        eng.assert_fact(Fact("edge", src="B", dst="C"))
        n = eng.run()
        assert n == 1
        assert results == [("A", "B", "C")]

    def test_join_with_constant(self):
        """Join where one condition has a constant filter."""
        eng = Engine()
        results = []
        eng.add_rule(Rule(
            name="manager-subordinate",
            conditions=[
                Condition("employee", name=Var("n"), dept=Var("d")),
                Condition("department", id=Var("d"), head=Const("Alice")),
            ],
            actions=[lambda b, e: results.append(b["n"])],
        ))
        eng.assert_fact(Fact("employee", name="Bob", dept="eng"))
        eng.assert_fact(Fact("employee", name="Carol", dept="sales"))
        eng.assert_fact(Fact("department", id="eng", head="Alice"))
        eng.assert_fact(Fact("department", id="sales", head="Dave"))
        n = eng.run()
        assert n == 1
        assert results == ["Bob"]

    def test_join_no_match(self):
        """A join that doesn't find matching facts."""
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
        eng.assert_fact(Fact("likes", a="carol", b="dave"))
        n = eng.run()
        assert n == 0

    def test_transitive_closure(self):
        """Recursive transitive closure via rule assertions."""
        eng = Engine()
        eng.add_rule(Rule(
            name="direct",
            conditions=[Condition("parent", parent=Var("p"), child=Var("c"))],
            actions=[lambda b, e: e.assert_fact(
                Fact("ancestor", anc=b["p"], desc=b["c"])
            )],
        ))
        eng.add_rule(Rule(
            name="transitive",
            conditions=[
                Condition("ancestor", anc=Var("p"), desc=Var("c2")),
                Condition("parent", parent=Var("c2"), child=Var("c3")),
            ],
            actions=[lambda b, e: e.assert_fact(
                Fact("ancestor", anc=b["p"], desc=b["c3"])
            )],
        ))
        eng.assert_fact(Fact("parent", parent="A", child="B"))
        eng.assert_fact(Fact("parent", parent="B", child="C"))
        eng.run()
        ancestors = eng.facts_of_type("ancestor")
        assert len(ancestors) >= 2  # A->B, A->C (via transitivity)

    def test_alpha_node_sharing(self):
        """Two rules with the same condition should share an alpha node."""
        eng = Engine()
        eng.add_rule(Rule(
            name="r1",
            conditions=[Condition("person", name=Var("n"))],
            actions=[lambda b, e: None],
        ))
        eng.add_rule(Rule(
            name="r2",
            conditions=[Condition("person", name=Var("n"))],
            actions=[lambda b, e: None],
        ))
        # Same condition key → shared alpha node
        assert len(eng._alpha_nodes) == 1