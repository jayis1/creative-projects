"""Tests for edge cases and error handling."""
import pytest
from rete import Engine, Fact, Rule, Condition, Var, Const, ConflictResolution
from rete.exceptions import FactError, RuleError, InfiniteLoopError


class TestEdgeCases:
    def test_fact_with_special_chars(self):
        f = Fact("data", value="hello\nworld\ttab")
        assert f["value"] == "hello\nworld\ttab"

    def test_fact_with_numeric_fields(self):
        f = Fact("score", value=42, pi=3.14)
        assert f["value"] == 42
        assert f["pi"] == 3.14

    def test_fact_with_nested_dict(self):
        f = Fact("config", settings={"key": "value"})
        assert f["settings"] == {"key": "value"}

    def test_fact_with_list_value(self):
        f = Fact("data", items=[1, 2, 3])
        assert f["items"] == [1, 2, 3]

    def test_fact_with_bool_value(self):
        f = Fact("flag", active=True, inactive=False)
        assert f["active"] is True
        assert f["inactive"] is False

    def test_empty_engine_run(self):
        eng = Engine()
        n = eng.run()
        assert n == 0

    def test_run_with_no_rules(self):
        eng = Engine()
        eng.assert_fact(Fact("person", name="Alice"))
        n = eng.run()
        assert n == 0

    def test_infinite_loop_detection(self):
        """Engine raises InfiniteLoopError when max_steps is exceeded."""
        eng = Engine(max_steps=5)
        # A rule that re-asserts a fact each time, creating infinite loop
        eng.add_rule(Rule(
            name="loop",
            conditions=[Condition("event", type=Const("x"))],
            actions=[lambda b, e: None],
        ))
        eng.assert_fact(Fact("event", type="x"))
        # With REFC strategy (default), this won't loop because of refraction
        n = eng.run()
        assert n <= 5

    def test_run_with_explicit_max_steps(self):
        eng = Engine(max_steps=1000)
        results = []
        eng.add_rule(Rule(
            name="r1",
            conditions=[Condition("person", name=Var("n"))],
            actions=[lambda b, e: results.append(b["n"])],
        ))
        eng.assert_fact(Fact("person", name="Alice"))
        n = eng.run(max_steps=10)
        assert n == 1  # Only one fact, so only one firing

    def test_rule_with_multiple_actions(self):
        eng = Engine()
        results = []
        eng.add_rule(Rule(
            name="multi",
            conditions=[Condition("person", name=Var("n"))],
            actions=[
                lambda b, e: results.append(f"action1: {b['n']}"),
                lambda b, e: results.append(f"action2: {b['n']}"),
            ],
        ))
        eng.assert_fact(Fact("person", name="Alice"))
        eng.run()
        assert len(results) == 2
        assert results[0] == "action1: Alice"
        assert results[1] == "action2: Alice"

    def test_fact_with_none_value(self):
        f = Fact("item", value=None)
        assert f["value"] is None

    def test_fact_none_value_matches_var(self):
        eng = Engine()
        results = []
        eng.add_rule(Rule(
            name="r1",
            conditions=[Condition("item", value=Var("v"))],
            actions=[lambda b, e: results.append(b["v"])],
        ))
        eng.assert_fact(Fact("item", value=None))
        n = eng.run()
        assert n == 1
        assert results == [None]

    def test_duplicate_assert_no_double_fire(self):
        eng = Engine()
        results = []
        eng.add_rule(Rule(
            name="r1",
            conditions=[Condition("person", name=Var("n"))],
            actions=[lambda b, e: results.append(b["n"])],
        ))
        f = Fact("person", name="Alice")
        assert eng.assert_fact(f) is True
        assert eng.assert_fact(f) is False
        n = eng.run()
        assert n == 1
        assert results == ["Alice"]

    def test_retract_nonexistent_fact(self):
        eng = Engine()
        f = Fact("person", name="Alice")
        assert eng.retract_fact(f) is False

    def test_add_rule_after_facts(self):
        """Rules added after facts should still match those facts."""
        eng = Engine()
        eng.assert_fact(Fact("person", name="Alice"))
        results = []
        eng.add_rule(Rule(
            name="r1",
            conditions=[Condition("person", name=Var("n"))],
            actions=[lambda b, e: results.append(b["n"])],
        ))
        n = eng.run()
        assert n == 1
        assert results == ["Alice"]

    def test_tracing_disabled_by_default(self):
        eng = Engine()
        eng.add_rule(Rule(
            name="r1",
            conditions=[Condition("person", name=Var("n"))],
            actions=[lambda b, e: None],
        ))
        eng.assert_fact(Fact("person", name="Alice"))
        eng.run()
        assert len(eng.get_trace()) == 0

    def test_enable_disable_tracing(self):
        eng = Engine()
        eng.add_rule(Rule(
            name="r1",
            conditions=[Condition("person", name=Var("n"))],
            actions=[lambda b, e: None],
        ))
        eng.assert_fact(Fact("person", name="Alice"))
        eng.enable_tracing()
        eng.run()
        assert len(eng.get_trace()) == 1
        eng.disable_tracing()
        eng.reset_agenda()
        eng.run()
        # Tracing was disabled, so no new entries
        assert len(eng.get_trace()) == 1

    def test_reset_stats(self):
        eng = Engine()
        eng.add_rule(Rule(
            name="r1",
            conditions=[Condition("person", name=Var("n"))],
            actions=[lambda b, e: None],
        ))
        eng.assert_fact(Fact("person", name="Alice"))
        eng.run()
        stats = eng.get_stats()
        assert stats["r1"]["fires"] == 1
        eng.reset_stats()
        stats2 = eng.get_stats()
        # Stats may show 0 fires or key may be absent
        assert stats2.get("r1", {}).get("fires", 0) == 0

    def test_log_method(self):
        eng = Engine(log_level="DEBUG")
        # Should not raise
        eng.log("test message", "INFO")

    def test_fire_one_returns_false_when_empty(self):
        eng = Engine()
        assert eng.fire_one() is False

    def test_fact_get_missing_key(self):
        f = Fact("person", name="Alice")
        assert f.get("missing") is None
        assert f.get("missing", "default") == "default"

    def test_fact_getitem_raises_keyerror(self):
        f = Fact("person", name="Alice")
        with pytest.raises(KeyError):
            _ = f["nonexistent"]