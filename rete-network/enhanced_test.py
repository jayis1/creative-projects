"""Test enhanced features: query, TMS, stats, tracing, serialization."""
from rete import Engine, Fact, Rule, Condition, Var, Const, ConflictResolution, load_json, save_facts
import tempfile, os, json

def test_query():
    eng = Engine()
    eng.assert_fact(Fact("person", name="Alice", age=30))
    eng.assert_fact(Fact("person", name="Bob", age=25))
    eng.assert_fact(Fact("person", name="Carol", age=30))
    all_p = eng.query("person")
    assert len(all_p) == 3
    age30 = eng.query("person", age=30)
    assert len(age30) == 2
    one = eng.query_one("person", name="Alice")
    assert one is not None
    assert one["age"] == 30
    none = eng.query_one("person", name="Zoe")
    assert none is None
    assert eng.fact_count("person") == 3
    assert eng.fact_count() == 3
    print("test_query: PASS")

def test_tracing():
    eng = Engine()
    eng.enable_tracing()
    eng.add_rule(Rule(
        name="greet",
        conditions=[Condition("person", name=Var("n"))],
        actions=[lambda b, e: None],
    ))
    eng.assert_fact(Fact("person", name="Alice"))
    eng.run()
    trace = eng.get_trace()
    assert len(trace) == 1
    assert trace[0]["rule"] == "greet"
    assert trace[0]["bindings"]["n"] == "Alice"
    print("test_tracing: PASS")

def test_stats():
    eng = Engine()
    eng.add_rule(Rule(
        name="r1",
        conditions=[Condition("person", name=Var("n"))],
        actions=[lambda b, e: None],
    ))
    eng.assert_fact(Fact("person", name="Alice"))
    eng.assert_fact(Fact("person", name="Bob"))
    eng.run()
    stats = eng.get_stats()
    assert stats["r1"]["fires"] == 2
    print("test_stats: PASS")

def test_tms():
    eng = Engine()
    sig = ("test-rule", ())

    # Logically assert a fact
    f = Fact("derived", value=42)
    eng.assert_logical(f, sig)
    assert f in eng.facts

    # Retract support → fact should disappear
    eng._retract_support(sig)
    assert f not in eng.facts
    print("test_tms: PASS")

def test_priority_strategy():
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
    # Without refraction, high fires repeatedly; we just check it fires first
    assert results[0] == "high", f"expected high first, got {results[0]}"
    print("test_priority_strategy: PASS")

def test_json_roundtrip():
    eng = Engine()
    eng.assert_fact(Fact("person", name="Alice"))
    eng.assert_fact(Fact("person", name="Bob"))
    tmp = tempfile.mktemp(suffix=".json")
    try:
        save_facts(eng, tmp)
        with open(tmp) as f:
            data = json.load(f)
        assert len(data["facts"]) == 2
        print("test_json_roundtrip: PASS")
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

def test_load_json_rules():
    rules, facts = load_json("examples/social.json")
    assert len(rules) == 3
    assert len(facts) == 6
    # Check the negated condition
    allow_rule = [r for r in rules if r.name == "allow-entry"][0]
    assert allow_rule.conditions[1].negated
    print("test_load_json_rules: PASS")

def test_remove_rule():
    eng = Engine()
    eng.add_rule(Rule(
        name="r1",
        conditions=[Condition("person", name=Var("n"))],
        actions=[lambda b, e: None],
    ))
    assert "r1" in eng.rules
    eng.remove_rule("r1")
    assert "r1" not in eng.rules
    print("test_remove_rule: PASS")

def test_retract_type():
    eng = Engine()
    eng.assert_fact(Fact("person", name="Alice"))
    eng.assert_fact(Fact("person", name="Bob"))
    eng.assert_fact(Fact("animal", species="cat"))
    n = eng.retract_type("person")
    assert n == 2
    assert eng.fact_count("person") == 0
    assert eng.fact_count("animal") == 1
    print("test_retract_type: PASS")

if __name__ == "__main__":
    test_query()
    test_tracing()
    test_stats()
    test_tms()
    test_priority_strategy()
    test_json_roundtrip()
    test_load_json_rules()
    test_remove_rule()
    test_retract_type()
    print("ALL ENHANCED TESTS PASSED")