"""Core language tests for the BASIC interpreter."""

import io
import pytest

from basic_interpreter.interpreter import Interpreter
from basic_interpreter.errors import BasicRuntimeError, BasicSyntaxError, BasicStopException
from conftest import run_basic


class TestArithmetic:
    """Test arithmetic operations and expressions."""

    def test_addition(self):
        assert "4" in run_basic('10 PRINT 2 + 2')

    def test_subtraction(self):
        assert "3" in run_basic('10 PRINT 5 - 2')

    def test_multiplication(self):
        assert "6" in run_basic('10 PRINT 2 * 3')

    def test_division(self):
        assert "2.5" in run_basic('10 PRINT 5 / 2')

    def test_integer_division_positive(self):
        assert "3" in run_basic('10 PRINT 7 \\ 2')

    def test_integer_division_negative(self):
        """Integer division should truncate toward zero (BASIC convention)."""
        assert "-3" in run_basic('10 PRINT -7 \\ 2')

    def test_mod_positive(self):
        assert "1" in run_basic('10 PRINT 7 MOD 2')

    def test_mod_negative(self):
        """MOD should follow dividend sign (BASIC convention)."""
        assert "-1" in run_basic('10 PRINT -7 MOD 2')

    def test_exponentiation(self):
        assert "1024" in run_basic('10 PRINT 2 ^ 10')

    def test_operator_precedence(self):
        """Multiplication should bind tighter than addition."""
        assert "7" in run_basic('10 PRINT 2 + 3 * 2 - 1')

    def test_parenthesized_expressions(self):
        assert "14" in run_basic('10 PRINT (2 + 3) * (3 - 1) + 4')


class TestVariables:
    """Test variable assignment and access."""

    def test_numeric_variable(self):
        output = run_basic('10 LET X = 42\n20 PRINT X')
        assert "42" in output

    def test_string_variable(self):
        output = run_basic('10 LET A$ = "Hello"\n20 PRINT A$')
        assert "Hello" in output

    def test_implicit_let(self):
        output = run_basic('10 X = 99\n20 PRINT X')
        assert "99" in output

    def test_swap(self):
        output = run_basic('10 LET A = 10\n20 LET B = 20\n30 SWAP A, B\n40 PRINT A; B')
        assert "20" in output and "10" in output

    def test_integer_suffix(self):
        output = run_basic('10 COUNT% = 5\n20 PRINT COUNT%')
        assert "5" in output


class TestControlFlow:
    """Test control flow statements."""

    def test_goto(self):
        output = run_basic('10 LET X = 10\n20 GOTO 40\n30 LET X = 999\n40 PRINT X')
        assert "10" in output and "999" not in output

    def test_gosub_return(self):
        output = run_basic('10 GOSUB 100\n20 PRINT "back"\n30 END\n100 PRINT "sub"\n110 RETURN')
        assert "sub" in output and "back" in output

    def test_if_then_else(self):
        output = run_basic('10 LET X = 5\n20 IF X > 3 THEN PRINT "big" ELSE PRINT "small"')
        assert "big" in output and "small" not in output

    def test_if_then_goto(self):
        output = run_basic('10 LET X = 5\n20 IF X > 3 THEN 40\n30 PRINT "no"\n40 PRINT "yes"')
        assert "yes" in output

    def test_for_next(self):
        output = run_basic('10 LET S = 0\n20 FOR I = 1 TO 5\n30 LET S = S + I\n40 NEXT I\n50 PRINT S')
        assert "15" in output

    def test_for_next_step(self):
        output = run_basic('10 LET S = 0\n20 FOR I = 10 TO 1 STEP -1\n30 LET S = S + I\n40 NEXT I\n50 PRINT S')
        assert "55" in output

    def test_nested_for(self):
        output = run_basic('10 LET S = 0\n20 FOR I = 1 TO 3\n30 FOR J = 1 TO 3\n40 LET S = S + I * J\n50 NEXT J\n60 NEXT I\n70 PRINT S')
        assert "36" in output

    def test_while_wend(self):
        output = run_basic('10 LET X = 1\n20 WHILE X < 5\n30 LET X = X + 1\n40 WEND\n50 PRINT X')
        assert "5" in output

    def test_do_while_loop(self):
        output = run_basic('10 LET X = 1\n20 DO WHILE X < 5\n30 LET X = X + 1\n40 LOOP\n50 PRINT X')
        assert "5" in output

    def test_do_until_loop(self):
        output = run_basic('10 LET X = 1\n20 DO UNTIL X >= 5\n30 LET X = X + 1\n40 LOOP\n50 PRINT X')
        assert "5" in output

    def test_do_loop_post_while(self):
        output = run_basic('10 LET X = 1\n20 DO\n30 LET X = X + 1\n40 LOOP WHILE X < 5\n50 PRINT X')
        assert "5" in output

    def test_do_loop_post_until(self):
        output = run_basic('10 LET X = 1\n20 DO\n30 LET X = X + 1\n40 LOOP UNTIL X >= 5\n50 PRINT X')
        assert "5" in output


class TestSelectCase:
    """Test SELECT CASE multi-way branching."""

    def test_select_case_basic(self):
        output = run_basic('''\
10 LET X = 3
20 SELECT CASE X
30 CASE 1
40   PRINT "one"
50 CASE 2
60   PRINT "two"
70 CASE 3
80   PRINT "three"
90 CASE ELSE
100   PRINT "other"
110 END SELECT
''')
        assert "three" in output
        assert "one" not in output
        assert "two" not in output

    def test_select_case_is(self):
        output = run_basic('''\
10 LET X = 75
20 SELECT CASE X
30 CASE IS < 50
40   PRINT "low"
50 CASE IS < 80
60   PRINT "medium"
70 CASE ELSE
80   PRINT "high"
90 END SELECT
''')
        assert "medium" in output and "low" not in output

    def test_select_case_range(self):
        output = run_basic('''\
10 LET X = 5
20 SELECT CASE X
30 CASE 1 TO 3
40   PRINT "small"
50 CASE 4 TO 6
60   PRINT "medium"
70 CASE ELSE
80   PRINT "large"
90 END SELECT
''')
        assert "medium" in output

    def test_select_case_else(self):
        output = run_basic('''\
10 LET X = 99
20 SELECT CASE X
30 CASE 1
40   PRINT "one"
50 CASE ELSE
60   PRINT "else"
70 END SELECT
80 PRINT "after"
''')
        assert "else" in output
        assert "one" not in output
        assert "after" in output

    def test_select_case_no_fallthrough(self):
        """Bug #1: SELECT CASE should NOT fall through to subsequent cases."""
        output = run_basic('''\
10 LET X = 1
20 SELECT CASE X
30 CASE 1
40   PRINT "one"
50 CASE 2
60   PRINT "two"
70 CASE ELSE
80   PRINT "other"
90 END SELECT
100 PRINT "done"
''')
        assert "one" in output
        assert "two" not in output
        assert "other" not in output


class TestFunctions:
    """Test built-in functions."""

    def test_abs(self):
        assert "5" in run_basic('10 PRINT ABS(-5)')

    def test_int(self):
        assert "3" in run_basic('10 PRINT INT(3.7)')

    def test_sqr(self):
        assert "4" in run_basic('10 PRINT SQR(16)')

    def test_sgn(self):
        output = run_basic('10 PRINT SGN(5)\n20 PRINT SGN(-3)\n30 PRINT SGN(0)')
        assert "1" in output and "-1" in output

    def test_fix(self):
        assert "3" in run_basic('10 PRINT FIX(3.7)')

    def test_string_functions(self):
        output = run_basic('''\
10 LET A$ = "Hello World"
20 PRINT LEN(A$)
30 PRINT LEFT$(A$, 5)
40 PRINT RIGHT$(A$, 5)
50 PRINT MID$(A$, 7, 5)
''')
        assert "11" in output
        assert "Hello" in output
        assert "World" in output

    def test_chr_asc(self):
        output = run_basic('10 PRINT CHR$(65)\n20 PRINT ASC("A")')
        assert "A" in output and "65" in output

    def test_str_val(self):
        output = run_basic('10 PRINT STR$(42)\n20 PRINT VAL("3.14")')
        assert "42" in output

    def test_lcase_ucase(self):
        output = run_basic('10 PRINT LCASE$("HELLO")\n20 PRINT UCASE$("hello")')
        assert "hello" in output and "HELLO" in output

    def test_ltrim_rtrim(self):
        output = run_basic('10 PRINT LTRIM$("  hi  ")\n20 PRINT RTRIM$("  hi  ")')
        assert "hi  " in output and "  hi" in output

    def test_string_repeat(self):
        output = run_basic('10 PRINT STRING$(5, "*")')
        assert "*****" in output

    def test_instr(self):
        output = run_basic('10 PRINT INSTR("Hello World", "World")')
        assert "7" in output

    def test_def_fn(self):
        output = run_basic('10 DEF FN DOUBLE(X) = X * 2\n20 PRINT FN DOUBLE(5)\n30 PRINT FN DOUBLE(10)')
        assert "10" in output and "20" in output

    def test_date_time(self):
        output = run_basic('10 LET D$ = DATE$\n20 LET T$ = TIME$\n30 PRINT LEN(D$)\n40 PRINT LEN(T$)')
        assert "10" in output and "8" in output


class TestArrays:
    """Test DIM and array operations."""

    def test_dim_1d(self):
        output = run_basic('10 DIM A(5)\n20 LET A(1) = 100\n30 LET A(3) = 300\n40 PRINT A(1); A(3)')
        assert "100" in output and "300" in output

    def test_dim_2d(self):
        output = run_basic('10 DIM M(3, 3)\n20 LET M(1, 1) = 5\n30 LET M(2, 3) = 7\n40 PRINT M(1, 1); M(2, 3)')
        assert "5" in output and "7" in output

    def test_erase(self):
        output = run_basic('10 DIM A(5)\n20 LET A(3) = 42\n30 ERASE A\n40 PRINT A(3)')
        assert "0" in output

    def test_auto_expand_array(self):
        output = run_basic('10 LET X(20) = 99\n20 PRINT X(20)')
        assert "99" in output


class TestDataRead:
    """Test READ/DATA/RESTORE."""

    def test_read_data(self):
        output = run_basic('10 READ A, B, C\n20 PRINT A; B; C\n30 DATA 10, 20, 30')
        assert "10" in output and "20" in output and "30" in output

    def test_restore(self):
        output = run_basic('10 READ A\n20 READ B\n30 RESTORE\n40 READ C\n50 PRINT A; B; C\n60 DATA 1, 2, 3')
        assert "1" in output and "2" in output


class TestFileIO:
    """Test file I/O operations."""

    def test_write_and_read(self, tmp_path):
        filepath = str(tmp_path / "test.txt")
        source1 = f'10 OPEN "{filepath}" FOR OUTPUT AS #1\n20 PRINT# 1, "Hello from file"\n30 CLOSE #1'
        interp = Interpreter(stdout=io.StringIO())
        interp.load(source1)
        interp.run()

        source2 = f'10 OPEN "{filepath}" FOR INPUT AS #1\n20 INPUT# 1, A$\n30 CLOSE #1\n40 PRINT A$'
        interp2 = Interpreter(stdout=io.StringIO())
        interp2.load(source2)
        interp2.run()
        assert "Hello from file" in interp2.stdout.getvalue()

    def test_append_mode(self, tmp_path):
        filepath = str(tmp_path / "test_append.txt")
        source = f'10 OPEN "{filepath}" FOR OUTPUT AS #1\n20 PRINT# 1, "first"\n30 CLOSE #1\n'
        source += f'40 OPEN "{filepath}" FOR APPEND AS #2\n50 PRINT# 2, "second"\n60 CLOSE #2'
        interp = Interpreter(stdout=io.StringIO())
        interp.load(source)
        interp.run()

        with open(filepath) as f:
            content = f.read()
        assert "first" in content and "second" in content


class TestLogicalOperators:
    """Test logical operators."""

    def test_and(self):
        output = run_basic('10 IF (5 > 3) AND (2 < 4) THEN PRINT "both"')
        assert "both" in output

    def test_or(self):
        output = run_basic('10 IF (5 > 3) OR (2 > 4) THEN PRINT "either"')
        assert "either" in output

    def test_not(self):
        output = run_basic('10 IF NOT (3 > 5) THEN PRINT "not"')
        assert "not" in output

    def test_xor(self):
        output = run_basic('10 LET A = -1\n20 LET B = 0\n30 PRINT (A XOR B)\n40 PRINT (A XOR A)')
        assert "-1" in output

    def test_eqv(self):
        output = run_basic('10 LET A = -1\n20 LET B = -1\n30 PRINT (A EQV B)')
        assert "-1" in output

    def test_imp(self):
        output = run_basic('10 PRINT (0 IMP 0)\n20 PRINT (-1 IMP -1)')
        assert "-1" in output

    def test_comparison_returns_minus1(self):
        output = run_basic('10 PRINT (5 > 3)\n20 PRINT (3 > 5)')
        assert "-1" in output and "0" in output


class TestOnError:
    """Test ON ERROR GOTO / RESUME error handling."""

    def test_on_error_goto(self):
        output = run_basic('''\
10 ON ERROR GOTO 100
20 LET X = 1 / 0
30 PRINT "after error"
40 END
100 PRINT "error caught"
110 RESUME 30
''')
        assert "error caught" in output


class TestOneLiner:
    """Test immediate/one-liner mode."""

    def test_one_liner_print(self):
        output = run_basic('PRINT 2+2')
        assert "4" in output

    def test_colon_separator(self):
        output = run_basic('10 LET A = 1 : LET B = 2 : PRINT A + B')
        assert "3" in output


class TestEdgeCases:
    """Test edge cases and bug fixes."""

    def test_integer_division_truncates_toward_zero(self):
        """Bug #3: \\ should truncate toward zero, not floor."""
        assert "-3" in run_basic('10 PRINT -7 \\ 2')

    def test_mod_follows_dividend_sign(self):
        """Bug #4: MOD should follow dividend sign."""
        assert "-1" in run_basic('10 PRINT -7 MOD 2')

    def test_format_value_handles_int(self):
        """Bug #5: _format_value should handle Python int from logical ops."""
        output = run_basic('10 PRINT 5 = 5')
        assert "-1" in output

    def test_file_cleanup_on_reload(self, tmp_path):
        """Bug #2: Files should be closed when loading a new program."""
        filepath = str(tmp_path / "test_cleanup.txt")
        with open(filepath, "w") as f:
            f.write("hello\n")
        interp = Interpreter(stdout=io.StringIO())
        source = f'10 OPEN "{filepath}" FOR INPUT AS #1'
        interp.load(source)
        interp.run()
        assert 1 in interp._files
        interp.load("10 END")
        assert 1 not in interp._files

    def test_line_to_idx_performance(self):
        """Bug #6: Line number lookup should be O(1) via _line_to_idx dict."""
        interp = Interpreter(stdout=io.StringIO())
        lines = [f"{i * 10} LET X = {i}" for i in range(1, 1000)]
        lines.append("10000 GOTO 10")
        source = "\n".join(lines)
        interp.load(source)
        assert len(interp._line_to_idx) == 1000

    def test_empty_program(self):
        """Running an empty program should not crash."""
        interp = Interpreter(stdout=io.StringIO())
        interp.load("")
        interp.run()  # Should not raise

    def test_string_concatenation(self):
        output = run_basic('10 LET A$ = "Hello" + " " + "World"\n20 PRINT A$')
        assert "Hello World" in output

    def test_immediate_mode_let(self):
        output = run_basic('LET X = 42 : PRINT X')
        assert "42" in output