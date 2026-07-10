"""Tests for the spreadsheet engine."""

import pytest
from spreadsheet import Engine
from spreadsheet.cell import CellError, ErrorType, parse_a1, format_a1, col_to_index, index_to_col
from spreadsheet.parser import parse_formula, tokenize


class TestCellRef:
    def test_parse_a1(self):
        assert parse_a1("A1") == (0, 0)
        assert parse_a1("B2") == (1, 1)
        assert parse_a1("Z1") == (0, 25)
        assert parse_a1("AA1") == (0, 26)
        assert parse_a1("AB10") == (9, 27)

    def test_format_a1(self):
        assert format_a1(0, 0) == "A1"
        assert format_a1(1, 1) == "B2"
        assert format_a1(0, 25) == "Z1"
        assert format_a1(0, 26) == "AA1"

    def test_col_conversion(self):
        assert col_to_index("A") == 0
        assert col_to_index("Z") == 25
        assert col_to_index("AA") == 26
        assert index_to_col(0) == "A"
        assert index_to_col(25) == "Z"
        assert index_to_col(26) == "AA"

    def test_roundtrip(self):
        for i in range(100):
            assert col_to_index(index_to_col(i)) == i

    def test_invalid_ref(self):
        with pytest.raises(ValueError):
            parse_a1("1A")
        with pytest.raises(ValueError):
            parse_a1("")


class TestParser:
    def test_number(self):
        ast = parse_formula("42")
        assert ast.value == 42.0

    def test_string(self):
        ast = parse_formula('"hello"')
        assert ast.value == "hello"

    def test_bool(self):
        ast = parse_formula("TRUE")
        assert ast.value is True

    def test_binop(self):
        ast = parse_formula("1+2")
        assert ast.op == "+"
        assert ast.left.value == 1.0
        assert ast.right.value == 2.0

    def test_precedence(self):
        # 1 + 2 * 3 => 1 + (2*3)
        ast = parse_formula("1+2*3")
        assert ast.op == "+"
        assert ast.right.op == "*"

    def test_power_right_assoc(self):
        # 2 ^ 3 ^ 2 => 2 ^ (3 ^ 2)
        ast = parse_formula("2^3^2")
        assert ast.op == "^"
        assert ast.right.op == "^"

    def test_unary_minus(self):
        ast = parse_formula("-5")
        assert ast.op == "-"
        assert ast.operand.value == 5.0

    def test_cell_ref(self):
        ast = parse_formula("A1")
        assert ast.row == 0
        assert ast.col == 0

    def test_range(self):
        ast = parse_formula("A1:B2")
        assert isinstance(ast, type(parse_formula("A1:A1")))
        assert ast.start.row == 0

    def test_func_call(self):
        ast = parse_formula("SUM(A1:A3)")
        assert ast.name == "SUM"
        assert len(ast.args) == 1

    def test_nested_func(self):
        ast = parse_formula("IF(A1>0, MAX(B1:B3), 0)")
        assert ast.name == "IF"
        assert len(ast.args) == 3

    def test_parens(self):
        ast = parse_formula("(1+2)*3")
        assert ast.op == "*"
        assert ast.left.op == "+"


class TestEngineBasics:
    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_set_get_number(self):
        self.engine.set("S", "A1", "42")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == 42.0

    def test_set_get_string(self):
        self.engine.set("S", "A1", "hello")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == "hello"

    def test_set_get_bool(self):
        self.engine.set("S", "A1", "TRUE")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") is True

    def test_simple_formula(self):
        self.engine.set("S", "A1", "=1+2")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == 3.0

    def test_cell_reference(self):
        self.engine.set("S", "A1", "10")
        self.engine.set("S", "B1", "=A1*2")
        self.engine.recalculate()
        assert self.engine.get("S", "B1") == 20.0

    def test_chained_references(self):
        self.engine.set("S", "A1", "5")
        self.engine.set("S", "B1", "=A1+1")
        self.engine.set("S", "C1", "=B1+1")
        self.engine.recalculate()
        assert self.engine.get("S", "C1") == 7.0


class TestFormulas:
    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_sum_range(self):
        for i in range(5):
            self.engine.set("S", f"A{i+1}", str(i + 1))
        self.engine.set("S", "B1", "=SUM(A1:A5)")
        self.engine.recalculate()
        assert self.engine.get("S", "B1") == 15.0

    def test_average(self):
        self.engine.set("S", "A1", "10")
        self.engine.set("S", "A2", "20")
        self.engine.set("S", "A3", "30")
        self.engine.set("S", "B1", "=AVERAGE(A1:A3)")
        self.engine.recalculate()
        assert self.engine.get("S", "B1") == 20.0

    def test_if_true(self):
        self.engine.set("S", "A1", "10")
        self.engine.set("S", "B1", "=IF(A1>5, \"yes\", \"no\")")
        self.engine.recalculate()
        assert self.engine.get("S", "B1") == "yes"

    def test_if_false(self):
        self.engine.set("S", "A1", "3")
        self.engine.set("S", "B1", "=IF(A1>5, \"yes\", \"no\")")
        self.engine.recalculate()
        assert self.engine.get("S", "B1") == "no"

    def test_division_by_zero(self):
        self.engine.set("S", "A1", "=1/0")
        self.engine.recalculate()
        result = self.engine.get("S", "A1")
        assert isinstance(result, CellError)
        assert result.type == ErrorType.DIV_ZERO

    def test_max_min(self):
        self.engine.set("S", "A1", "3")
        self.engine.set("S", "A2", "7")
        self.engine.set("S", "A3", "1")
        self.engine.set("S", "B1", "=MAX(A1:A3)")
        self.engine.set("S", "B2", "=MIN(A1:A3)")
        self.engine.recalculate()
        assert self.engine.get("S", "B1") == 7.0
        assert self.engine.get("S", "B2") == 1.0

    def test_count(self):
        self.engine.set("S", "A1", "1")
        self.engine.set("S", "A2", "hello")
        self.engine.set("S", "A3", "3")
        self.engine.set("S", "B1", "=COUNT(A1:A3)")
        self.engine.recalculate()
        assert self.engine.get("S", "B1") == 2.0

    def test_nested_functions(self):
        self.engine.set("S", "A1", "3")
        self.engine.set("S", "A2", "7")
        self.engine.set("S", "A3", "=IF(MAX(A1:A2)>5, A1+A2, 0)")
        self.engine.recalculate()
        assert self.engine.get("S", "A3") == 10.0

    def test_string_functions(self):
        self.engine.set("S", "A1", '=UPPER("hello")')
        self.engine.set("S", "A2", '=LEN("world")')
        self.engine.set("S", "A3", '=CONCAT("foo", "bar")')
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == "HELLO"
        assert self.engine.get("S", "A2") == 5.0
        assert self.engine.get("S", "A3") == "foobar"

    def test_and_or_not(self):
        self.engine.set("S", "A1", "TRUE")
        self.engine.set("S", "A2", "FALSE")
        self.engine.set("S", "B1", "=AND(A1:A2)")
        self.engine.set("S", "B2", "=OR(A1:A2)")
        self.engine.set("S", "B3", "=NOT(A2)")
        self.engine.recalculate()
        assert self.engine.get("S", "B1") is False
        assert self.engine.get("S", "B2") is True
        assert self.engine.get("S", "B3") is True


class TestCircularRef:
    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_direct_cycle(self):
        self.engine.set("S", "A1", "=B1")
        self.engine.set("S", "B1", "=A1")
        stats = self.engine.recalculate()
        assert stats["cycles"] >= 1
        a1 = self.engine.get("S", "A1")
        assert isinstance(a1, CellError)
        assert a1.type == ErrorType.CYCLE

    def test_self_cycle(self):
        self.engine.set("S", "A1", "=A1")
        stats = self.engine.recalculate()
        assert stats["cycles"] >= 1

    def test_indirect_cycle(self):
        self.engine.set("S", "A1", "=B1")
        self.engine.set("S", "B1", "=C1")
        self.engine.set("S", "C1", "=A1")
        stats = self.engine.recalculate()
        assert stats["cycles"] >= 1


class TestCrossSheet:
    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S1")
        self.engine.add_sheet("S2")

    def test_cross_sheet_ref(self):
        self.engine.set("S1", "A1", "42")
        self.engine.set("S2", "A1", "=S1!A1*2")
        self.engine.recalculate()
        assert self.engine.get("S2", "A1") == 84.0

    def test_missing_sheet(self):
        self.engine.set("S1", "A1", "=BadSheet!A1")
        self.engine.recalculate()
        result = self.engine.get("S1", "A1")
        assert isinstance(result, CellError)


class TestImportExport:
    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_csv_roundtrip(self):
        self.engine.set("S", "A1", "1")
        self.engine.set("S", "B1", "2")
        self.engine.set("S", "A2", "3")
        self.engine.set("S", "B2", "4")
        csv_text = self.engine.export_csv("S")
        assert "1" in csv_text

        # import into new sheet (no header row)
        self.engine.import_csv("S2", "1,2\n3,4\n")
        self.engine.recalculate()
        assert self.engine.get("S2", "A1") == 1.0
        assert self.engine.get("S2", "B2") == 4.0

    def test_json_roundtrip(self):
        self.engine.set("S", "A1", "42")
        self.engine.set("S", "A2", "=A1*2")
        data = self.engine.to_dict()
        assert "sheets" in data
        assert "S" in data["sheets"]

        new_engine = Engine()
        new_engine.from_dict(data)
        new_engine.recalculate()
        assert new_engine.get("S", "A1") == 42.0
        assert new_engine.get("S", "A2") == 84.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])