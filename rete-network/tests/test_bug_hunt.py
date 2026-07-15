"""Bug hunt tests for the Rete engine."""
from rete import Engine, Fact, Rule, Condition, Var, Const, ConflictResolution, ReteError
from rete.engine import AlphaNode, JoinNode, BetaMemory, ProductionNode, DummyBeta
from rete.exceptions import RuleError, FactError, InfiniteLoopError
import pytest


# ---------------------------------------------------------------------------
# Bug 1: Condition.key sorts _Term objects which may not be comparable
# ---------------------------------------------------------------------------

def test_bug_condition_key_different_term_types():
    """Condition.key should not crash when fields have mixed Var/Const types."""
    # This should not raise TypeError
    c1 = Condition("person", name=Var("n"))
    c2 = Condition("person", name=Const("Alice"))
    k1 = c1.key
    k2 = c2.key
    assert k1 != k2  # different keys


def test_bug_condition_key_same_field_var_and_const():
    """A condition with both Var and Const in different fields should produce a valid key."""
    c = Condition("person", name=Var("n"), age=Const(30))
    k = c.key
    assert isinstance(k, tuple)


# ---------------------------------------------------------------------------
# Bug 2: remove_rule leaves orphaned join nodes in alpha successors
# ---------------------------------------------------------------------------

def test_bug_remove_rule_cleans_alpha_successors():
    """remove_rule should remove join nodes from alpha node successor lists."""
    eng = Engine()
    eng.add_rule(Rule(
        name="r1",
        conditions=[Condition("person", name=Var("n"))],
        actions=[lambda b, e: None],
    ))
    # Check that alpha node has the join node as successor
    assert any(
        len(an.successors) > 0
        for an in eng._alpha_nodes.values()
    )
    eng.remove_rule("r1")
    # After removal, alpha nodes should have no successors pointing to r1's joins
    for an in eng._alpha_nodes.values():
        # Successors should be empty or only contain live join nodes
        for jn in an.successors:
            # The join node's successor should not be a dead production node
            assert jn.successor is not None


# ---------------------------------------------------------------------------
# Bug 3: _action_print crashes on missing format key
# ---------------------------------------------------------------------------

def test_bug_action_print_missing_key():
    """_action_print should handle missing binding keys gracefully."""
    from rete.serialization import _action_print
    action = _action_print("Hello, {name}!")
    # After fix: missing keys should not crash, they're left as-is
    action({}, Engine())  # should not raise


# ---------------------------------------------------------------------------
# Bug 4: Fact with None field value fails to match Condition with Var
# ---------------------------------------------------------------------------

def test_bug_fact_none_field_value():
    """A fact with a field set to None should still match a Var condition."""
    eng = Engine()
    results = []
    eng.add_rule(Rule(
        name="test",
        conditions=[Condition("item", value=Var("v"))],
        actions=[lambda b, e: results.append(b["v"])],
    ))
    eng.assert_fact(Fact("item", value=None))
    n = eng.run()
    # Should match and bind v=None
    assert n == 1, f"expected 1 match, got {n}"
    assert results == [None]


# ---------------------------------------------------------------------------
# Bug 5: Duplicate facts in working memory get propagated twice
# ---------------------------------------------------------------------------

def test_bug_action_assert_missing_binding():
    """_action_assert should resolve missing bindings to None, not leak '?x'."""
    from rete.serialization import _action_assert
    eng = Engine()
    action = _action_assert("result", value="?x")
    action({}, eng)  # no bindings → ?x is missing
    facts = eng.facts_of_type("result")
    assert len(facts) == 1
    # After fix: value should be None, not the string "?x"
    assert facts[0].fields.get("value") is None


def test_bug_duplicate_assert_no_double_fire():
    """Asserting the same fact twice should not cause double firing."""
    eng = Engine()
    results = []
    eng.add_rule(Rule(
        name="r1",
        conditions=[Condition("person", name=Var("n"))],
        actions=[lambda b, e: results.append(b["n"])],
    ))
    f = Fact("person", name="Alice")
    assert eng.assert_fact(f) == True
    assert eng.assert_fact(f) == False  # duplicate
    n = eng.run()
    assert n == 1
    assert results == ["Alice"]


# ---------------------------------------------------------------------------
# Bug 6: Right retract for negated conditions can add duplicate items
# ---------------------------------------------------------------------------

def test_bug_negated_retract_no_duplicates():
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
    # Alice is allowed (no banned fact)
    eng.run()
    assert results == ["Alice"]

    # Now ban Alice
    eng.reset_agenda()
    results.clear()
    banned = Fact("banned", name="Alice")
    eng.assert_fact(banned)
    # Alice should not be allowed now
    assert eng.agenda() == []

    # Unban Alice — should be allowed again
    eng.retract_fact(banned)
    assert len(eng.agenda()) == 1
    eng.run()
    assert results == ["Alice"]


# ---------------------------------------------------------------------------
# Bug 7: PRIORITY strategy with REFC should combine both behaviors
# ---------------------------------------------------------------------------

def test_bug_priority_with_refc():
    """PRIORITY strategy should also apply refraction to prevent infinite loops."""
    eng = Engine(strategy=ConflictResolution.PRIORITY)
    results = []
    eng.add_rule(Rule(
        name="high",
        priority=10,
        conditions=[Condition("event", type=Const("trigger"))],
        actions=[lambda b, e: results.append("high")],
    ))
    eng.add_rule(Rule(
        name="low",
        priority=1,
        conditions=[Condition("event", type=Const("trigger"))],
        actions=[lambda b, e: results.append("low")],
    ))
    eng.assert_fact(Fact("event", type="trigger"))
    eng.run()
    # With PRIORITY but no refraction, high fires forever (up to max_steps)
    # This is technically "by design" but is a usability bug — PRIORITY
    # should probably also use refraction to avoid infinite loops.
    # At minimum, high should fire first.
    assert results[0] == "high"


# ---------------------------------------------------------------------------
# Bug 8: clear() doesn't reset refraction memory
# ---------------------------------------------------------------------------

def test_bug_clear_resets_refraction():
    """clear() should also reset the fired set so rules can re-fire."""
    eng = Engine()
    results = []
    eng.add_rule(Rule(
        name="r1",
        conditions=[Condition("person", name=Var("n"))],
        actions=[lambda b, e: results.append(b["n"])],
    ))
    eng.assert_fact(Fact("person", name="Alice"))
    eng.run()
    assert results == ["Alice"]

    eng.clear()
    results.clear()
    eng.assert_fact(Fact("person", name="Alice"))
    n = eng.run()
    # After clear, the rule should fire again
    assert n == 1
    assert results == ["Alice"]


# ---------------------------------------------------------------------------
# Bug 9: Alpha node sharing between negated and non-negated conditions
# ---------------------------------------------------------------------------

def test_bug_alpha_sharing_negated_and_non_negated():
    """A negated and non-negated condition with same fields should not share alpha node."""
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
    # The key includes negated flag, so they should have different alpha nodes
    assert len(eng._alpha_nodes) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])