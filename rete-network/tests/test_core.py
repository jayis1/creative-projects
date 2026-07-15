"""Core engine tests: facts, conditions, rules, basic inference."""
import pytest
from rete import Engine, Fact, Rule, Condition, Var, Const, ReteError
from rete.exceptions import FactError, RuleError


class TestFact:
    def test_fact_creation(self):
        f = Fact("person", name="Alice", age=30)
        assert f.fact_type == "person"
        assert f["name"] == "Alice"
        assert f["age"] == 30
        assert f.get("missing", "default") == "default"

    def test_fact_equality_structural(self):
        f1 = Fact("person", name="Alice")
        f2 = Fact("person", name="Alice")
        f3 = Fact("person", name="Bob")
        assert f1 == f2  # same type+fields
        assert f1 != f3
        assert hash(f1) == hash(f2)

    def test_fact_unique_id(self):
        f1 = Fact("person", name="Alice")
        f2 = Fact("person", name="Alice")
        assert f1._id != f2._id  # different instances

    def test_fact_empty_type_raises(self):
        with pytest.raises(FactError):
            Fact("", name="x")
        with pytest.raises(FactError):
            Fact(123, name="x")

    def test_fact_to_dict(self):
        f = Fact("person", name="Alice", age=30)
        d = f.to_dict()
        assert d == {"type": "person", "fields": {"name": "Alice", "age": 30}}

    def test_fact_none_field(self):
        f = Fact("item", value=None)
        assert f["value"] is None


class TestCondition:
    def test_condition_with_var(self):
        c = Condition("person", name=Var("n"))
        assert c.fact_type == "person"
        assert c.fields["name"].is_var

    def test_condition_with_const(self):
        c = Condition("person", age=Const(30))
        assert not c.fields["age"].is_var

    def test_condition_auto_wraps_values(self):
        c = Condition("person", name="Alice", age=30)
        # Raw values should be auto-wrapped in Const
        assert not c.fields["name"].is_var
        assert c.fields["name"].matches("Alice")

    def test_condition_negated(self):
        c = Condition("banned", name=Var("n"), negated=True)
        assert c.negated is True

    def test_condition_key_different(self):
        c1 = Condition("person", name=Var("n"))
        c2 = Condition("person", name=Const("Alice"))
        assert c1.key != c2.key

    def test_condition_key_same(self):
        c1 = Condition("person", name=Var("n"))
        c2 = Condition("person", name=Var("n"))
        assert c1.key == c2.key

    def test_condition_invalid_type_raises(self):
        with pytest.raises(RuleError):
            Condition("", name=Var("n"))
        with pytest.raises(RuleError):
            Condition(123, name=Var("n"))


class TestRule:
    def test_rule_creation(self):
        r = Rule(
            name="test",
            conditions=[Condition("person", name=Var("n"))],
            actions=[lambda b, e: None],
        )
        assert r.name == "test"
        assert r.priority == 0

    def test_rule_with_priority(self):
        r = Rule(
            name="high",
            conditions=[Condition("event")],
            actions=[lambda b, e: None],
            priority=10,
        )
        assert r.priority == 10

    def test_rule_empty_name_raises(self):
        with pytest.raises(RuleError):
            Rule(name="", conditions=[Condition("x")], actions=[lambda b, e: None])

    def test_rule_no_conditions_raises(self):
        with pytest.raises(RuleError):
            Rule(name="x", conditions=[], actions=[lambda b, e: None])

    def test_rule_no_actions_raises(self):
        with pytest.raises(RuleError):
            Rule(name="x", conditions=[Condition("y")], actions=[])


class TestEngineBasic:
    def test_engine_creation(self):
        eng = Engine()
        assert len(eng.rules) == 0
        assert eng.fact_count() == 0

    def test_add_rule(self):
        eng = Engine()
        eng.add_rule(Rule(
            name="r1",
            conditions=[Condition("person", name=Var("n"))],
            actions=[lambda b, e: None],
        ))
        assert "r1" in eng.rules

    def test_duplicate_rule_raises(self):
        eng = Engine()
        eng.add_rule(Rule(
            name="r1",
            conditions=[Condition("person", name=Var("n"))],
            actions=[lambda b, e: None],
        ))
        with pytest.raises(RuleError):
            eng.add_rule(Rule(
                name="r1",
                conditions=[Condition("person", name=Var("n"))],
                actions=[lambda b, e: None],
            ))

    def test_assert_and_retract(self):
        eng = Engine()
        f = Fact("person", name="Alice")
        assert eng.assert_fact(f) is True
        assert eng.assert_fact(f) is False  # duplicate
        assert eng.fact_count() == 1
        assert eng.retract_fact(f) is True
        assert eng.fact_count() == 0

    def test_assert_non_fact_raises(self):
        eng = Engine()
        with pytest.raises(FactError):
            eng.assert_fact("not a fact")

    def test_simple_firing(self):
        eng = Engine()
        results = []
        eng.add_rule(Rule(
            name="greet",
            conditions=[Condition("person", name=Var("n"))],
            actions=[lambda b, e: results.append(b["n"])],
        ))
        eng.assert_fact(Fact("person", name="Alice"))
        n = eng.run()
        assert n == 1
        assert results == ["Alice"]

    def test_multiple_facts_fire(self):
        eng = Engine()
        results = []
        eng.add_rule(Rule(
            name="greet",
            conditions=[Condition("person", name=Var("n"))],
            actions=[lambda b, e: results.append(b["n"])],
        ))
        eng.assert_fact(Fact("person", name="Alice"))
        eng.assert_fact(Fact("person", name="Bob"))
        eng.assert_fact(Fact("person", name="Carol"))
        n = eng.run()
        assert n == 3
        assert sorted(results) == ["Alice", "Bob", "Carol"]

    def test_constant_filter(self):
        eng = Engine()
        results = []
        eng.add_rule(Rule(
            name="adult",
            conditions=[Condition("person", age=Const(25))],
            actions=[lambda b, e: results.append("found")],
        ))
        eng.assert_fact(Fact("person", name="A", age=25))
        eng.assert_fact(Fact("person", name="B", age=30))
        n = eng.run()
        assert n == 1

    def test_predicate(self):
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
        assert n == 2
        assert sorted(results) == [20, 30]

    def test_retract_prevents_fire(self):
        eng = Engine()
        results = []
        eng.add_rule(Rule(
            name="r1",
            conditions=[Condition("person", name=Var("n"))],
            actions=[lambda b, e: results.append(b["n"])],
        ))
        f = Fact("person", name="Alice")
        eng.assert_fact(f)
        eng.retract_fact(f)
        n = eng.run()
        assert n == 0
        assert results == []

    def test_clear(self):
        eng = Engine()
        eng.assert_fact(Fact("person", name="Alice"))
        eng.assert_fact(Fact("person", name="Bob"))
        assert eng.fact_count() == 2
        eng.clear()
        assert eng.fact_count() == 0

    def test_retract_type(self):
        eng = Engine()
        eng.assert_fact(Fact("person", name="Alice"))
        eng.assert_fact(Fact("person", name="Bob"))
        eng.assert_fact(Fact("animal", species="cat"))
        n = eng.retract_type("person")
        assert n == 2
        assert eng.fact_count("person") == 0
        assert eng.fact_count("animal") == 1

    def test_remove_rule(self):
        eng = Engine()
        eng.add_rule(Rule(
            name="r1",
            conditions=[Condition("person", name=Var("n"))],
            actions=[lambda b, e: None],
        ))
        assert "r1" in eng.rules
        eng.remove_rule("r1")
        assert "r1" not in eng.rules

    def test_remove_nonexistent_rule_raises(self):
        eng = Engine()
        with pytest.raises(RuleError):
            eng.remove_rule("nonexistent")

    def test_facts_of_type(self):
        eng = Engine()
        eng.assert_fact(Fact("person", name="Alice"))
        eng.assert_fact(Fact("person", name="Bob"))
        eng.assert_fact(Fact("animal", species="cat"))
        persons = eng.facts_of_type("person")
        assert len(persons) == 2
        animals = eng.facts_of_type("animal")
        assert len(animals) == 1

    def test_repr(self):
        eng = Engine()
        r = repr(eng)
        assert "Engine" in r
        assert "rules=0" in r