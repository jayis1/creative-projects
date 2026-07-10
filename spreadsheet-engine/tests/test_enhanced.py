"""Tests for enhanced spreadsheet engine features (Phase 2)."""

import pytest
from spreadsheet import Engine
from spreadsheet.cell import CellError, ErrorType


class TestLookupFunctions:
    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_vlookup_exact(self):
        # Build a lookup table: A1:B3
        self.engine.set("S", "A1", "apple")
        self.engine.set("S", "B1", "10")
        self.engine.set("S", "A2", "banana")
        self.engine.set("S", "B2", "20")
        self.engine.set("S", "A3", "cherry")
        self.engine.set("S", "B3", "30")
        self.engine.set("S", "D1", '=VLOOKUP("banana", A1:B3, 2, FALSE)')
        self.engine.recalculate()
        assert self.engine.get("S", "D1") == 20.0

    def test_vlookup_not_found(self):
        self.engine.set("S", "A1", "apple")
        self.engine.set("S", "B1", "10")
        self.engine.set("S", "D1", '=VLOOKUP("grape", A1:B1, 2, FALSE)')
        self.engine.recalculate()
        result = self.engine.get("S", "D1")
        assert isinstance(result, CellError)
        assert result.type == ErrorType.NA

    def test_match(self):
        self.engine.set("S", "A1", "10")
        self.engine.set("S", "A2", "20")
        self.engine.set("S", "A3", "30")
        self.engine.set("S", "B1", "=MATCH(20, A1:A3, 0)")
        self.engine.recalculate()
        assert self.engine.get("S", "B1") == 2.0

    def test_index(self):
        self.engine.set("S", "A1", "10")
        self.engine.set("S", "A2", "20")
        self.engine.set("S", "A3", "30")
        self.engine.set("S", "B1", "=INDEX(A1:A3, 2)")
        self.engine.recalculate()
        assert self.engine.get("S", "B1") == 20.0

    def test_choose(self):
        self.engine.set("S", "A1", "=CHOOSE(2, \"red\", \"green\", \"blue\")")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == "green"


class TestTextFunctions:
    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_proper(self):
        self.engine.set("S", "A1", '=PROPER("hello world")')
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == "Hello World"

    def test_rept(self):
        self.engine.set("S", "A1", '=REPT("ab", 3)')
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == "ababab"

    def test_search(self):
        self.engine.set("S", "A1", '=SEARCH("world", "hello world")')
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == 7.0

    def test_exact(self):
        self.engine.set("S", "A1", '=EXACT("hello", "hello")')
        self.engine.set("S", "A2", '=EXACT("Hello", "hello")')
        self.engine.recalculate()
        assert self.engine.get("S", "A1") is True
        assert self.engine.get("S", "A2") is False

    def test_textjoin(self):
        self.engine.set("S", "A1", "a")
        self.engine.set("S", "A2", "b")
        self.engine.set("S", "A3", "c")
        self.engine.set("S", "B1", '=TEXTJOIN(",", TRUE, A1:A3)')
        self.engine.recalculate()
        assert self.engine.get("S", "B1") == "a,b,c"

    def test_code(self):
        self.engine.set("S", "A1", '=CODE("A")')
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == 65.0

    def test_char(self):
        self.engine.set("S", "A1", '=CHAR(65)')
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == "A"

    def test_concat_with_amp(self):
        self.engine.set("S", "A1", '="Hello" & " " & "World"')
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == "Hello World"


class TestMathFunctions:
    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_sign(self):
        self.engine.set("S", "A1", "=SIGN(-5)")
        self.engine.set("S", "A2", "=SIGN(0)")
        self.engine.set("S", "A3", "=SIGN(42)")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == -1.0
        assert self.engine.get("S", "A2") == 0.0
        assert self.engine.get("S", "A3") == 1.0

    def test_gcd(self):
        self.engine.set("S", "A1", "=GCD(12, 18)")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == 6.0

    def test_lcm(self):
        self.engine.set("S", "A1", "=LCM(4, 6)")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == 12.0

    def test_fact(self):
        self.engine.set("S", "A1", "=FACT(5)")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == 120.0

    def test_int(self):
        self.engine.set("S", "A1", "=INT(3.7)")
        self.engine.set("S", "A2", "=INT(-3.2)")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == 3.0
        assert self.engine.get("S", "A2") == -4.0  # floor

    def test_trunc(self):
        self.engine.set("S", "A1", "=TRUNC(3.7)")
        self.engine.set("S", "A2", "=TRUNC(-3.7)")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == 3.0
        assert self.engine.get("S", "A2") == -3.0  # toward zero

    def test_degrees_radians(self):
        self.engine.set("S", "A1", "=DEGREES(PI())")
        self.engine.set("S", "A2", "=RADIANS(180)")
        self.engine.recalculate()
        assert abs(self.engine.get("S", "A1") - 180.0) < 0.001
        assert abs(self.engine.get("S", "A2") - 3.14159) < 0.001


class TestStatisticsFunctions:
    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_stdevp(self):
        self.engine.set("S", "A1", "1")
        self.engine.set("S", "A2", "2")
        self.engine.set("S", "A3", "3")
        self.engine.set("S", "A4", "4")
        self.engine.set("S", "A5", "5")
        self.engine.set("S", "B1", "=STDEVP(A1:A5)")
        self.engine.recalculate()
        result = self.engine.get("S", "B1")
        # population stdev of 1..5 = sqrt(2) ≈ 1.4142
        assert abs(result - 1.414213) < 0.001

    def test_mode(self):
        self.engine.set("S", "A1", "1")
        self.engine.set("S", "A2", "2")
        self.engine.set("S", "A3", "2")
        self.engine.set("S", "A4", "3")
        self.engine.set("S", "B1", "=MODE(A1:A4)")
        self.engine.recalculate()
        assert self.engine.get("S", "B1") == 2.0

    def test_percentile(self):
        for i in range(1, 11):
            self.engine.set("S", f"A{i}", str(i))
        self.engine.set("S", "B1", "=PERCENTILE(A1:A10, 0.5)")
        self.engine.recalculate()
        # median of 1..10 = 5.5
        assert abs(self.engine.get("S", "B1") - 5.5) < 0.01

    def test_quartile(self):
        for i in range(1, 11):
            self.engine.set("S", f"A{i}", str(i))
        self.engine.set("S", "B1", "=QUARTILE(A1:A10, 0)")
        self.engine.set("S", "B2", "=QUARTILE(A1:A10, 4)")
        self.engine.recalculate()
        assert self.engine.get("S", "B1") == 1.0  # min
        assert self.engine.get("S", "B2") == 10.0  # max

    def test_correl(self):
        self.engine.set("S", "A1", "1")
        self.engine.set("S", "A2", "2")
        self.engine.set("S", "A3", "3")
        self.engine.set("S", "B1", "2")
        self.engine.set("S", "B2", "4")
        self.engine.set("S", "B3", "6")
        self.engine.set("S", "C1", "=CORREL(A1:A3, B1:B3)")
        self.engine.recalculate()
        result = self.engine.get("S", "C1")
        assert abs(result - 1.0) < 0.001  # perfect positive correlation


class TestComparisonOperators:
    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_equal(self):
        self.engine.set("S", "A1", "=IF(5=5, \"yes\", \"no\")")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == "yes"

    def test_not_equal(self):
        self.engine.set("S", "A1", "=IF(5<>5, \"yes\", \"no\")")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == "no"

    def test_greater_equal(self):
        self.engine.set("S", "A1", "=IF(5>=5, \"yes\", \"no\")")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == "yes"

    def test_less_than(self):
        self.engine.set("S", "A1", "=IF(3<5, \"yes\", \"no\")")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == "yes"

    def test_comparison_returns_bool(self):
        self.engine.set("S", "A1", "=5>3")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") is True


class TestNamedRanges:
    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_define_and_get(self):
        self.engine.define_name("Revenue", "S", "A1:A3")
        nr = self.engine.get_name("Revenue")
        assert nr is not None
        assert nr.sheet == "S"
        assert nr.is_range

    def test_list_names(self):
        self.engine.define_name("Revenue", "S", "A1:A3")
        self.engine.define_name("Total", "S", "B1")
        names = self.engine.list_names()
        assert "REVENUE" in names
        assert "TOTAL" in names


class TestFormulaAuditing:
    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_trace_precedents(self):
        self.engine.set("S", "A1", "10")
        self.engine.set("S", "B1", "=A1*2")
        self.engine.recalculate()
        precedents = self.engine.trace_precedents("S", "B1")
        assert ("S", 0, 0) in precedents

    def test_trace_dependents(self):
        self.engine.set("S", "A1", "10")
        self.engine.set("S", "B1", "=A1*2")
        self.engine.set("S", "C1", "=B1+1")
        self.engine.recalculate()
        dependents = self.engine.trace_dependents("S", "A1")
        assert ("S", 0, 1) in dependents  # B1 depends on A1

    def test_audit_cell(self):
        self.engine.set("S", "A1", "10")
        self.engine.set("S", "B1", "=A1*2")
        self.engine.recalculate()
        audit = self.engine.audit_cell("S", "B1")
        assert audit["raw"] == "=A1*2"
        assert audit["value"] == "20"
        assert len(audit["precedents"]) == 1
        assert audit["precedents"][0]["ref"] == "A1"


class TestIncrementalRecalc:
    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_incremental_recalc(self):
        self.engine.set("S", "A1", "10")
        self.engine.set("S", "B1", "=A1*2")
        self.engine.set("S", "C1", "=B1+1")
        self.engine.recalculate()
        assert self.engine.get("S", "C1") == 21.0

        # Change A1 and recalculate only affected cells
        self.engine.set("S", "A1", "20")
        stats = self.engine.recalculate_affected([("S", 0, 0)])
        assert self.engine.get("S", "C1") == 41.0
        assert stats["evaluated"] >= 2  # B1 and C1


class TestSheetOperations:
    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_copy_sheet(self):
        self.engine.set("S", "A1", "42")
        self.engine.set("S", "A2", "=A1*2")
        self.engine.copy_sheet("S", "Copy")
        self.engine.recalculate()
        assert self.engine.get("Copy", "A1") == 42.0
        assert self.engine.get("Copy", "A2") == 84.0

    def test_clear_sheet(self):
        self.engine.set("S", "A1", "42")
        self.engine.clear_sheet("S")
        assert self.engine.get("S", "A1") is None

    def test_list_functions(self):
        funcs = self.engine.list_functions()
        assert "SUM" in funcs
        assert "VLOOKUP" in funcs
        assert "IF" in funcs
        assert len(funcs) >= 80


class Test2DRanges:
    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_2d_sum(self):
        # 3x3 grid
        for r in range(3):
            for c in range(3):
                self.engine.set("S", f"{chr(65+c)}{r+1}", str(r * 3 + c + 1))
        self.engine.set("S", "D1", "=SUM(A1:C3)")
        self.engine.recalculate()
        assert self.engine.get("S", "D1") == 45.0  # sum 1..9

    def test_vlookup_2d(self):
        # 3x2 table
        self.engine.set("S", "A1", "1")
        self.engine.set("S", "B1", "alpha")
        self.engine.set("S", "A2", "2")
        self.engine.set("S", "B2", "beta")
        self.engine.set("S", "A3", "3")
        self.engine.set("S", "B3", "gamma")
        self.engine.set("S", "D1", '=VLOOKUP(2, A1:B3, 2, FALSE)')
        self.engine.recalculate()
        assert self.engine.get("S", "D1") == "beta"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])