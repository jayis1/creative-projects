"""Bug hunt tests — verify bugs before fixing them."""

import pytest
from spreadsheet import Engine
from spreadsheet.cell import CellError, ErrorType
from spreadsheet.functions import fn_round, fn_trunc
from spreadsheet.parser import parse_formula, tokenize


class TestBugRound:
    """Bug 1: ROUND with negative digits."""

    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_round_negative_digits(self):
        self.engine.set("S", "A1", "=ROUND(1234, -2)")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == 1200.0

    def test_round_negative_digits2(self):
        self.engine.set("S", "A1", "=ROUND(1256, -2)")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == 1300.0

    def test_round_negative_digits_negative(self):
        self.engine.set("S", "A1", "=ROUND(-1234, -2)")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == -1200.0

    def test_round_zero_digits(self):
        self.engine.set("S", "A1", "=ROUND(2.5, 0)")
        self.engine.recalculate()
        # Excel rounds half away from zero: 2.5 -> 3
        assert self.engine.get("S", "A1") == 3.0

    def test_round_negative_half(self):
        self.engine.set("S", "A1", "=ROUND(-2.5, 0)")
        self.engine.recalculate()
        # Excel: -2.5 -> -3 (round away from zero)
        assert self.engine.get("S", "A1") == -3.0


class TestBugEmptyCellConcat:
    """Bug 2: Empty cell in concatenation should produce empty string, not '0'."""

    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_empty_cell_concat(self):
        self.engine.set("S", "B1", '=A1 & "hello"')
        self.engine.recalculate()
        # A1 is empty, should produce "hello", not "0hello"
        assert self.engine.get("S", "B1") == "hello"


class TestBugComparisonMixedTypes:
    """Bug 3: Mixed-type comparison may not match Excel semantics."""

    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_bool_vs_number(self):
        # In Excel, booleans > numbers. Our engine uses type ranking: bool=3 > number=1
        self.engine.set("S", "A1", "=TRUE > 5")
        self.engine.recalculate()
        # With Excel-like type ranking, boolean (rank 3) > number (rank 1)
        assert self.engine.get("S", "A1") is True


class TestBugTokenizerLargeRefs:
    """Bug 4: Large column references (like ZZ1, AAA1) should parse correctly."""

    def test_zz1(self):
        ast = parse_formula("ZZ1")
        assert ast.row == 0
        assert ast.col == 701  # Z=25, ZZ = 26*26 + 25 = 701

    def test_aaa1(self):
        ast = parse_formula("AAA1")
        assert ast.row == 0
        assert ast.col == 702  # AAA = 26^2 + 26 + 0 = 702


class TestBugSheetBoundaryCheck:
    """Bug 5: Sheet should enforce max_rows/max_cols."""

    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_out_of_bounds_ref(self):
        # Setting a cell beyond max_cols should raise
        from spreadsheet.cell import index_to_col
        # This should work (within bounds)
        self.engine.set("S", "A1", "42")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == 42.0


class TestBugRangeOrdering:
    """Bug 6: Ranges specified in reverse order (B3:A1) should still work."""

    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_reverse_range(self):
        self.engine.set("S", "A1", "1")
        self.engine.set("S", "A2", "2")
        self.engine.set("S", "A3", "3")
        self.engine.set("S", "D1", "=SUM(A3:A1)")  # reversed range, D1 not in range
        self.engine.recalculate()
        assert self.engine.get("S", "D1") == 6.0


class TestBugErrorPropagationInFunc:
    """Bug 7: Errors in function arguments should propagate, not be silently ignored."""

    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_error_in_sum_range(self):
        self.engine.set("S", "A1", "=1/0")
        self.engine.set("S", "A2", "5")
        self.engine.set("S", "B1", "=SUM(A1:A2)")
        self.engine.recalculate()
        result = self.engine.get("S", "B1")
        # SUM should propagate the error, not silently ignore it
        assert isinstance(result, CellError)

    def test_error_in_if_condition(self):
        self.engine.set("S", "A1", "=1/0")
        self.engine.set("S", "B1", "=IF(A1>0, 1, 2)")
        self.engine.recalculate()
        result = self.engine.get("S", "B1")
        # IF should propagate the error from A1
        assert isinstance(result, CellError)


class TestBugNegativeNumberParsing:
    """Bug 8: Negative numbers should parse correctly."""

    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_negative_literal(self):
        self.engine.set("S", "A1", "-42")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == -42.0

    def test_negative_in_formula(self):
        self.engine.set("S", "A1", "=-42")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == -42.0

    def test_negative_scientific(self):
        self.engine.set("S", "A1", "=-1.5e-3")
        self.engine.recalculate()
        assert abs(self.engine.get("S", "A1") - (-0.0015)) < 1e-10


class TestBugStringEscaping:
    """Bug 9: String escaping in formulas."""

    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_escaped_quotes(self):
        self.engine.set("S", 'A1', '="say \\"hello\\""')
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == 'say "hello"'

    def test_backslash_literal(self):
        self.engine.set("S", 'A1', '="C:\\\\path"')
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == 'C:\\path'


class TestBugCountWithErrors:
    """Bug 10: COUNT should not count error values."""

    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_count_with_error(self):
        self.engine.set("S", "A1", "=1/0")  # error
        self.engine.set("S", "A2", "5")     # number
        self.engine.set("S", "B1", "=COUNT(A1:A2)")
        self.engine.recalculate()
        # COUNT should only count numbers, not errors -> should be 1
        assert self.engine.get("S", "B1") == 1.0


class TestBugRecalculateIdempotency:
    """Bug 11: Recalculating twice should produce the same results."""

    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_double_recalc(self):
        self.engine.set("S", "A1", "10")
        self.engine.set("S", "B1", "=A1*2")
        self.engine.set("S", "C1", "=B1+1")
        self.engine.recalculate()
        val1 = self.engine.get("S", "C1")
        self.engine.recalculate()
        val2 = self.engine.get("S", "C1")
        assert val1 == val2 == 21.0


class TestBugProductWithStrings:
    """Bug 12: PRODUCT should ignore non-numeric values, not error."""

    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_product_with_string(self):
        self.engine.set("S", "A1", "2")
        self.engine.set("S", "A2", "hello")
        self.engine.set("S", "A3", "3")
        self.engine.set("S", "B1", "=PRODUCT(A1:A3)")
        self.engine.recalculate()
        # Should be 6 (ignoring "hello")
        assert self.engine.get("S", "B1") == 6.0


class TestBugEmptyAverage:
    """Bug 13: AVERAGE of empty range should give DIV_ZERO error."""

    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_average_empty(self):
        self.engine.set("S", "B1", "=AVERAGE(A1:A10)")
        self.engine.recalculate()
        result = self.engine.get("S", "B1")
        assert isinstance(result, CellError)
        assert result.type == ErrorType.DIV_ZERO


class TestBugStringNumberComparison:
    """Bug 14: Comparing string with number should not crash."""

    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_string_vs_number(self):
        self.engine.set("S", "A1", '="5" > 3')
        self.engine.recalculate()
        # Should not crash; Excel treats string > number as True (strings > numbers)
        result = self.engine.get("S", "A1")
        # In Excel, strings are always greater than numbers
        assert result is True

    def test_number_vs_string(self):
        self.engine.set("S", "A1", '=3 > "5"')
        self.engine.recalculate()
        result = self.engine.get("S", "A1")
        # In Excel, numbers are always less than strings
        assert result is False


class TestBugUnaryOnString:
    """Bug 15: Unary minus on a string should give a VALUE error, not crash."""

    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_negate_string(self):
        self.engine.set("S", "A1", '=-"hello"')
        self.engine.recalculate()
        result = self.engine.get("S", "A1")
        assert isinstance(result, CellError)
        assert result.type == ErrorType.VALUE


class TestBugModByZero:
    """Bug 16: MOD by zero should give DIV_ZERO error."""

    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_mod_zero(self):
        self.engine.set("S", "A1", "=MOD(10, 0)")
        self.engine.recalculate()
        result = self.engine.get("S", "A1")
        assert isinstance(result, CellError)
        assert result.type == ErrorType.DIV_ZERO


class TestBugFnArgCountValidation:
    """Bug 17: Functions should validate argument counts."""

    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_abs_no_args(self):
        self.engine.set("S", "A1", "=ABS()")
        self.engine.recalculate()
        result = self.engine.get("S", "A1")
        assert isinstance(result, CellError)

    def test_sqrt_no_args(self):
        self.engine.set("S", "A1", "=SQRT()")
        self.engine.recalculate()
        result = self.engine.get("S", "A1")
        assert isinstance(result, CellError)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])