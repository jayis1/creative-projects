"""Tests for query API."""
import pytest
from rete import Engine, Fact, Var


class TestQuery:
    def test_query_all_by_type(self):
        eng = Engine()
        eng.assert_fact(Fact("person", name="Alice", age=30))
        eng.assert_fact(Fact("person", name="Bob", age=25))
        eng.assert_fact(Fact("person", name="Carol", age=30))
        results = eng.query("person")
        assert len(results) == 3

    def test_query_by_field_value(self):
        eng = Engine()
        eng.assert_fact(Fact("person", name="Alice", age=30))
        eng.assert_fact(Fact("person", name="Bob", age=25))
        eng.assert_fact(Fact("person", name="Carol", age=30))
        results = eng.query("person", age=30)
        assert len(results) == 2
        names = {f["name"] for f in results}
        assert names == {"Alice", "Carol"}

    def test_query_with_var_wildcard(self):
        eng = Engine()
        eng.assert_fact(Fact("person", name="Alice", age=30))
        eng.assert_fact(Fact("person", name="Bob", age=25))
        results = eng.query("person", name=Var("n"))
        assert len(results) == 2

    def test_query_one_returns_first(self):
        eng = Engine()
        eng.assert_fact(Fact("person", name="Alice", age=30))
        eng.assert_fact(Fact("person", name="Bob", age=25))
        one = eng.query_one("person", age=30)
        assert one is not None
        assert one["name"] == "Alice"

    def test_query_one_returns_none(self):
        eng = Engine()
        eng.assert_fact(Fact("person", name="Alice"))
        one = eng.query_one("person", name="Zoe")
        assert one is None

    def test_fact_count_total(self):
        eng = Engine()
        eng.assert_fact(Fact("person", name="Alice"))
        eng.assert_fact(Fact("person", name="Bob"))
        eng.assert_fact(Fact("animal", species="cat"))
        assert eng.fact_count() == 3

    def test_fact_count_by_type(self):
        eng = Engine()
        eng.assert_fact(Fact("person", name="Alice"))
        eng.assert_fact(Fact("person", name="Bob"))
        eng.assert_fact(Fact("animal", species="cat"))
        assert eng.fact_count("person") == 2
        assert eng.fact_count("animal") == 1
        assert eng.fact_count("nonexistent") == 0

    def test_query_multiple_fields(self):
        eng = Engine()
        eng.assert_fact(Fact("person", name="Alice", age=30, city="NYC"))
        eng.assert_fact(Fact("person", name="Bob", age=30, city="LA"))
        eng.assert_fact(Fact("person", name="Carol", age=25, city="NYC"))
        results = eng.query("person", age=30, city="NYC")
        assert len(results) == 1
        assert results[0]["name"] == "Alice"

    def test_query_empty_type(self):
        eng = Engine()
        results = eng.query("nonexistent")
        assert results == []