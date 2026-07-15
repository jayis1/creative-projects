"""Tests for conflict resolution strategies."""
import pytest
from rete import Engine, Fact, Rule, Condition, Var, Const, ConflictResolution


class TestConflictResolution:
    def test_fifo(self):
        """FIFO: oldest activation fires first (with refraction to prevent loops)."""
        eng = Engine(strategy=ConflictResolution.FIFO, max_steps=10)
        results = []
        eng.add_rule(Rule(
            name="r1",
            conditions=[Condition("event", id=Var("i"))],
            # Retract the fact after firing so it only fires once per fact
            actions=[
                lambda b, e: results.append(b["i"]),
                lambda b, e: e.retract_fact(
                    e.query_one("event", id=b["i"])
                ),
            ],
        ))
        eng.assert_fact(Fact("event", id=1))
        eng.assert_fact(Fact("event", id=2))
        eng.assert_fact(Fact("event", id=3))
        eng.run()
        assert results == [1, 2, 3]

    def test_lifo(self):
        """LIFO: newest activation fires first (with retraction)."""
        eng = Engine(strategy=ConflictResolution.LIFO, max_steps=10)
        results = []
        eng.add_rule(Rule(
            name="r1",
            conditions=[Condition("event", id=Var("i"))],
            actions=[
                lambda b, e: results.append(b["i"]),
                lambda b, e: e.retract_fact(
                    e.query_one("event", id=b["i"])
                ),
            ],
        ))
        eng.assert_fact(Fact("event", id=1))
        eng.assert_fact(Fact("event", id=2))
        eng.assert_fact(Fact("event", id=3))
        eng.run()
        assert results == [3, 2, 1]

    def test_priority(self):
        """PRIORITY: highest priority rule fires first."""
        eng = Engine(strategy=ConflictResolution.PRIORITY, max_steps=10)
        results = []
        eng.add_rule(Rule(
            name="low",
            priority=1,
            conditions=[Condition("event", type=Const("trigger"))],
            actions=[lambda b, e: results.append("low")],
        ))
        eng.add_rule(Rule(
            name="high",
            priority=10,
            conditions=[Condition("event", type=Const("trigger"))],
            actions=[lambda b, e: results.append("high")],
        ))
        eng.assert_fact(Fact("event", type="trigger"))
        eng.run()
        assert results[0] == "high"

    def test_refc(self):
        """REFC: refraction prevents re-firing same instantiation."""
        eng = Engine(strategy=ConflictResolution.REFC)
        results = []
        eng.add_rule(Rule(
            name="r1",
            conditions=[Condition("person", name=Var("n"))],
            actions=[lambda b, e: results.append(b["n"])],
        ))
        eng.assert_fact(Fact("person", name="Alice"))
        n = eng.run()
        assert n == 1
        # Running again should not fire again
        n2 = eng.run()
        assert n2 == 0

    def test_refc_reset(self):
        """reset_agenda allows re-firing."""
        eng = Engine(strategy=ConflictResolution.REFC)
        results = []
        eng.add_rule(Rule(
            name="r1",
            conditions=[Condition("person", name=Var("n"))],
            actions=[lambda b, e: results.append(b["n"])],
        ))
        eng.assert_fact(Fact("person", name="Alice"))
        eng.run()
        assert results == ["Alice"]
        eng.reset_agenda()
        n = eng.run()
        assert n == 1
        assert results == ["Alice", "Alice"]

    def test_priority_refc(self):
        """PRIORITY_REFC: priority + refraction."""
        eng = Engine(strategy=ConflictResolution.PRIORITY_REFC)
        results = []
        eng.add_rule(Rule(
            name="low",
            priority=1,
            conditions=[Condition("event", type=Const("x"))],
            actions=[lambda b, e: results.append("low")],
        ))
        eng.add_rule(Rule(
            name="high",
            priority=10,
            conditions=[Condition("event", type=Const("x"))],
            actions=[lambda b, e: results.append("high")],
        ))
        eng.assert_fact(Fact("event", type="x"))
        eng.run()
        # High fires first, then low fires, then neither fires again
        assert results[0] == "high"
        assert "low" in results
        assert len(results) == 2  # refraction prevents re-firing

    def test_recent(self):
        """RECENT: most-recently-added fact fires first (with retraction)."""
        eng = Engine(strategy=ConflictResolution.RECENT, max_steps=10)
        results = []
        eng.add_rule(Rule(
            name="r1",
            conditions=[Condition("event", id=Var("i"))],
            actions=[
                lambda b, e: results.append(b["i"]),
                lambda b, e: e.retract_fact(
                    e.query_one("event", id=b["i"])
                ),
            ],
        ))
        eng.assert_fact(Fact("event", id=1))
        eng.assert_fact(Fact("event", id=2))
        eng.assert_fact(Fact("event", id=3))
        eng.run()
        assert results == [3, 2, 1]

    def test_clear_resets_refraction(self):
        """clear() resets refraction so rules can re-fire."""
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
        assert n == 1
        assert results == ["Alice"]

    def test_max_steps(self):
        """Engine stops at max_steps even without refraction."""
        eng = Engine(strategy=ConflictResolution.FIFO, max_steps=3)
        results = []
        eng.add_rule(Rule(
            name="r1",
            conditions=[Condition("event", type=Const("x"))],
            actions=[lambda b, e: results.append(1)],
        ))
        eng.assert_fact(Fact("event", type="x"))
        n = eng.run()
        assert n == 3  # stopped at max_steps