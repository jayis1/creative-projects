"""Tests for batch operations."""
import pytest
from rete import Engine, Fact, Rule, Condition, Var


class TestBatch:
    def test_assert_batch(self):
        eng = Engine()
        facts = [
            Fact("person", name="Alice"),
            Fact("person", name="Bob"),
            Fact("person", name="Carol"),
        ]
        count = eng.assert_batch(facts)
        assert count == 3
        assert eng.fact_count() == 3

    def test_assert_batch_with_duplicates(self):
        eng = Engine()
        f = Fact("person", name="Alice")
        facts = [f, f, Fact("person", name="Bob")]
        count = eng.assert_batch(facts)
        assert count == 2  # Alice deduped

    def test_assert_batch_empty(self):
        eng = Engine()
        count = eng.assert_batch([])
        assert count == 0

    def test_retract_batch(self):
        eng = Engine()
        f1 = Fact("person", name="Alice")
        f2 = Fact("person", name="Bob")
        f3 = Fact("person", name="Carol")
        eng.assert_batch([f1, f2, f3])
        count = eng.retract_batch([f1, f2])
        assert count == 2
        assert eng.fact_count() == 1

    def test_retract_batch_nonexistent(self):
        eng = Engine()
        f = Fact("person", name="Alice")
        count = eng.retract_batch([f])
        assert count == 0

    def test_batch_with_rule_firing(self):
        """Batch assert facts, then run rules."""
        eng = Engine()
        results = []
        eng.add_rule(Rule(
            name="r1",
            conditions=[Condition("person", name=Var("n"))],
            actions=[lambda b, e: results.append(b["n"])],
        ))
        eng.assert_batch([
            Fact("person", name="Alice"),
            Fact("person", name="Bob"),
            Fact("person", name="Carol"),
        ])
        n = eng.run()
        assert n == 3
        assert sorted(results) == ["Alice", "Bob", "Carol"]