"""Tests for JSON and YAML serialization."""
import json
import tempfile
import os
import pytest
from rete import Engine, Fact, Rule, Condition, Var, Const, ConflictResolution
from rete import load_json, load_engine, save_facts, save_state
from rete.serialization import _parse_action, _parse_condition, _parse_fact, _parse_rule
from rete.exceptions import ReteError, SerializationError


class TestJSONSerialization:
    def test_load_json(self):
        rules, facts = load_json("examples/social.json")
        assert len(rules) == 3
        assert len(facts) == 6

    def test_load_json_ancestry(self):
        rules, facts = load_json("examples/ancestry.json")
        assert len(rules) == 2
        assert len(facts) == 3

    def test_load_json_nonexistent(self):
        with pytest.raises(ReteError):
            load_json("nonexistent.json")

    def test_load_json_invalid_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{invalid json")
            f.flush()
            path = f.name
        try:
            with pytest.raises(SerializationError):
                load_json(path)
        finally:
            os.unlink(path)

    def test_save_facts_roundtrip(self):
        eng = Engine()
        eng.assert_fact(Fact("person", name="Alice"))
        eng.assert_fact(Fact("person", name="Bob"))
        tmp = tempfile.mktemp(suffix=".json")
        try:
            save_facts(eng, tmp)
            with open(tmp) as f:
                data = json.load(f)
            assert len(data["facts"]) == 2
            types = {f["type"] for f in data["facts"]}
            assert types == {"person"}
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def test_save_state(self):
        eng = Engine()
        eng.add_rule(Rule(
            name="r1",
            conditions=[Condition("person", name=Var("n"))],
            actions=[lambda b, e: None],
        ))
        eng.assert_fact(Fact("person", name="Alice"))
        tmp = tempfile.mktemp(suffix=".json")
        try:
            save_state(eng, tmp)
            with open(tmp) as f:
                data = json.load(f)
            assert len(data["rules"]) == 1
            assert len(data["facts"]) == 1
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def test_load_engine_with_strategy(self):
        eng = load_engine("examples/social.json", strategy="fifo")
        assert eng.strategy == ConflictResolution.FIFO

    def test_parse_condition(self):
        c = _parse_condition({"type": "person", "fields": {"name": "?n"}})
        assert c.fact_type == "person"
        assert c.fields["name"].is_var

    def test_parse_condition_negated(self):
        c = _parse_condition({
            "type": "banned",
            "fields": {"name": "?n"},
            "negated": True,
        })
        assert c.negated is True

    def test_parse_condition_missing_type(self):
        with pytest.raises(SerializationError):
            _parse_condition({"fields": {}})

    def test_parse_fact(self):
        f = _parse_fact({"type": "person", "fields": {"name": "Alice"}})
        assert f.fact_type == "person"
        assert f["name"] == "Alice"

    def test_parse_fact_missing_type(self):
        with pytest.raises(SerializationError):
            _parse_fact({"fields": {}})

    def test_parse_action_print(self):
        action = _parse_action(["print", "Hello {n}!"])
        assert callable(action)

    def test_parse_action_assert(self):
        action = _parse_action(["assert", "result", {"value": "?x"}])
        assert callable(action)

    def test_parse_action_retract(self):
        action = _parse_action(["retract", "temp", {"id": "?i"}])
        assert callable(action)

    def test_parse_action_log(self):
        action = _parse_action(["log", "Processing {n}"])
        assert callable(action)

    def test_parse_action_unknown(self):
        with pytest.raises(SerializationError):
            _parse_action(["unknown_action", "arg"])

    def test_parse_action_string_shorthand(self):
        action = _parse_action("print:Hello World")
        assert callable(action)

    def test_parse_action_invalid(self):
        with pytest.raises(SerializationError):
            _parse_action(123)

    def test_parse_rule(self):
        rule = _parse_rule({
            "name": "test",
            "conditions": [{"type": "person", "fields": {"name": "?n"}}],
            "actions": [["print", "Hi {n}"]],
        })
        assert rule.name == "test"
        assert len(rule.conditions) == 1
        assert len(rule.actions) == 1

    def test_parse_rule_missing_name(self):
        with pytest.raises(SerializationError):
            _parse_rule({"conditions": [], "actions": []})

    def test_parse_rule_missing_conditions(self):
        with pytest.raises(SerializationError):
            _parse_rule({"name": "x", "actions": []})

    def test_parse_rule_missing_actions(self):
        with pytest.raises(SerializationError):
            _parse_rule({"name": "x", "conditions": []})


class TestYAMLSerialization:
    def test_load_yaml(self):
        yaml = pytest.importorskip("yaml")
        # Create a YAML file
        content = """
rules:
  - name: greet
    priority: 0
    conditions:
      - type: person
        fields:
          name: "?n"
    actions:
      - ["print", "Hello, {n}!"]
facts:
  - type: person
    fields:
      name: Alice
"""
        tmp = tempfile.mktemp(suffix=".yaml")
        try:
            with open(tmp, "w") as f:
                f.write(content)
            from rete import load_yaml, load_file
            rules, facts = load_yaml(tmp)
            assert len(rules) == 1
            assert len(facts) == 1
            assert rules[0].name == "greet"
            assert facts[0]["name"] == "Alice"

            # Test load_file auto-detection
            rules2, facts2 = load_file(tmp)
            assert len(rules2) == 1
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def test_save_facts_yaml(self):
        yaml = pytest.importorskip("yaml")
        eng = Engine()
        eng.assert_fact(Fact("person", name="Alice"))
        tmp = tempfile.mktemp(suffix=".yaml")
        try:
            from rete import save_facts_yaml
            save_facts_yaml(eng, tmp)
            with open(tmp) as f:
                data = yaml.safe_load(f)
            assert len(data["facts"]) == 1
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)