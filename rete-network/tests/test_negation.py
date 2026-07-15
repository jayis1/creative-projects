"""Tests for negated conditions (NCC — Negated Conjunctive Conditions)."""
import pytest
from rete import Engine, Fact, Rule, Condition, Var, Const


class TestNegation:
    def test_simple_negation(self):
        """Rule fires when a negated condition has no matching fact."""
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
        assert n == 1
        assert results == ["Alice"]

    def test_negation_no_blocking_facts(self):
        """All persons allowed when no one is banned."""
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
        n = eng.run()
        assert n == 2

    def test_negation_blocked_for_all(self):
        """No one is allowed when everyone is banned."""
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
        eng.assert_fact(Fact("banned", name="Alice"))
        n = eng.run()
        assert n == 0

    def test_negation_dynamic_block(self):
        """Asserting a banned fact after initial run blocks future firings."""
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
        eng.run()
        assert results == ["Alice"]

        # Now ban Alice
        eng.reset_agenda()
        results.clear()
        banned = Fact("banned", name="Alice")
        eng.assert_fact(banned)
        assert eng.agenda() == []

    def test_negation_dynamic_unblock(self):
        """Retracting a banned fact unblocks the rule."""
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
        banned = Fact("banned", name="Alice")
        eng.assert_fact(banned)
        eng.run()
        assert results == []  # Alice is banned

        # Unban Alice
        eng.retract_fact(banned)
        eng.run()
        assert results == ["Alice"]

    def test_negation_no_duplicates_on_retract(self):
        """Retracting a negated fact should not create duplicate instantiations."""
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
        eng.run()
        assert results == ["Alice"]

        eng.reset_agenda()
        results.clear()
        banned = Fact("banned", name="Alice")
        eng.assert_fact(banned)
        eng.retract_fact(banned)
        n = eng.run()
        assert n == 1
        assert results == ["Alice"]

    def test_negated_alpha_sharing(self):
        """Negated and non-negated conditions with same fields get separate alpha nodes."""
        eng = Engine()
        eng.add_rule(Rule(
            name="r1",
            conditions=[Condition("person", name=Var("n"))],
            actions=[lambda b, e: None],
        ))
        eng.add_rule(Rule(
            name="r2",
            conditions=[Condition("person", name=Var("n"), negated=True)],
            actions=[lambda b, e: None],
        ))
        assert len(eng._alpha_nodes) >= 2

    def test_multiple_negated_conditions(self):
        """A rule with multiple negated conditions."""
        eng = Engine()
        results = []
        eng.add_rule(Rule(
            name="vip",
            conditions=[
                Condition("person", name=Var("n")),
                Condition("banned", name=Var("n"), negated=True),
                Condition("suspended", name=Var("n"), negated=True),
            ],
            actions=[lambda b, e: results.append(b["n"])],
        ))
        eng.assert_fact(Fact("person", name="Alice"))
        eng.assert_fact(Fact("person", name="Bob"))
        eng.assert_fact(Fact("suspended", name="Bob"))
        n = eng.run()
        assert n == 1
        assert results == ["Alice"]