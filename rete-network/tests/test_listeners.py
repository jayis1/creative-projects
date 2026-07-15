"""Tests for the event listener / observer pattern."""
import pytest
from rete import Engine, Fact, Rule, Condition, Var
from rete.engine import EngineListener


class EventCollector:
    """Simple listener that records all events."""

    def __init__(self):
        self.asserted = []
        self.retracted = []
        self.fired = []

    def on_assert(self, fact):
        self.asserted.append(fact)

    def on_retract(self, fact):
        self.retracted.append(fact)

    def on_fire(self, rule_name, bindings):
        self.fired.append((rule_name, dict(bindings)))


class PartialListener:
    """Listener that only implements on_assert."""

    def __init__(self):
        self.asserted = []

    def on_assert(self, fact):
        self.asserted.append(fact)


class TestListeners:
    def test_assert_notification(self):
        eng = Engine()
        collector = EventCollector()
        eng.add_listener(collector)
        f = Fact("person", name="Alice")
        eng.assert_fact(f)
        assert len(collector.asserted) == 1
        assert collector.asserted[0] == f

    def test_retract_notification(self):
        eng = Engine()
        collector = EventCollector()
        eng.add_listener(collector)
        f = Fact("person", name="Alice")
        eng.assert_fact(f)
        eng.retract_fact(f)
        assert len(collector.retracted) == 1
        assert collector.retracted[0] == f

    def test_fire_notification(self):
        eng = Engine()
        collector = EventCollector()
        eng.add_listener(collector)
        eng.add_rule(Rule(
            name="r1",
            conditions=[Condition("person", name=Var("n"))],
            actions=[lambda b, e: None],
        ))
        eng.assert_fact(Fact("person", name="Alice"))
        eng.run()
        assert len(collector.fired) == 1
        assert collector.fired[0][0] == "r1"
        assert collector.fired[0][1]["n"] == "Alice"

    def test_remove_listener(self):
        eng = Engine()
        collector = EventCollector()
        eng.add_listener(collector)
        eng.remove_listener(collector)
        eng.assert_fact(Fact("person", name="Alice"))
        assert len(collector.asserted) == 0

    def test_partial_listener(self):
        """A listener that only implements some methods should not crash."""
        eng = Engine()
        listener = PartialListener()
        eng.add_listener(listener)
        f = Fact("person", name="Alice")
        eng.assert_fact(f)
        assert len(listener.asserted) == 1

        # Retract should not crash even though on_retract is missing
        eng.retract_fact(f)

    def test_multiple_listeners(self):
        eng = Engine()
        c1 = EventCollector()
        c2 = EventCollector()
        eng.add_listener(c1)
        eng.add_listener(c2)
        f = Fact("person", name="Alice")
        eng.assert_fact(f)
        assert len(c1.asserted) == 1
        assert len(c2.asserted) == 1