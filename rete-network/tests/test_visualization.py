"""Tests for network visualization (DOT export, summary)."""
import json
import pytest
from rete import Engine, Fact, Rule, Condition, Var, Const


class TestVisualization:
    def test_to_dot_basic(self):
        eng = Engine()
        eng.add_rule(Rule(
            name="r1",
            conditions=[Condition("person", name=Var("n"))],
            actions=[lambda b, e: None],
        ))
        dot = eng.to_dot()
        assert "digraph rete" in dot
        assert "r1" in dot

    def test_to_dot_multiple_rules(self):
        eng = Engine()
        eng.add_rule(Rule(
            name="r1",
            conditions=[Condition("person", name=Var("n"))],
            actions=[lambda b, e: None],
        ))
        eng.add_rule(Rule(
            name="r2",
            conditions=[
                Condition("likes", a=Var("x"), b=Var("y")),
                Condition("likes", a=Var("y"), b=Var("x")),
            ],
            actions=[lambda b, e: None],
        ))
        dot = eng.to_dot()
        assert "r1" in dot
        assert "r2" in dot

    def test_network_summary(self):
        eng = Engine()
        eng.add_rule(Rule(
            name="r1",
            conditions=[Condition("person", name=Var("n"))],
            actions=[lambda b, e: None],
        ))
        eng.assert_fact(Fact("person", name="Alice"))
        summary = eng.network_summary()
        assert summary["rules"] == 1
        assert summary["facts"] == 1
        assert "r1" in summary["rule_details"]
        assert summary["rule_details"]["r1"]["conditions"] == 1

    def test_network_summary_empty_engine(self):
        eng = Engine()
        summary = eng.network_summary()
        assert summary["rules"] == 0
        assert summary["facts"] == 0
        assert summary["rule_details"] == {}