"""Test new features added in the comprehensive improvement."""
import io
import pytest
from forth import ForthInterpreter, ForthError, ForthThrow


@pytest.fixture
def interp():
    return ForthInterpreter(output=io.StringIO())


def run(interp, code):
    interp.stack.clear()
    interp.return_stack.clear()
    interp._reset_state()
    out = io.StringIO()
    interp.output = out
    interp.eval(code)
    return out.getvalue()


class TestNewStringOps:
    def test_strlen(self, interp):
        assert run(interp, '"hello" STRLEN . CR') == "5 \n"

    def test_strcat(self, interp):
        # STRCAT ( str2 str1 -- str1+str2 )  str1 on top, str2 below
        assert run(interp, '"world" "hello " STRCAT . CR') == "hello world \n"

    def test_cmp_str_equal(self, interp):
        assert run(interp, '"abc" "abc" CMP-STR . CR') == "-1 \n"

    def test_cmp_str_not_equal(self, interp):
        assert run(interp, '"abc" "xyz" CMP-STR . CR') == "0 \n"

    def test_substr(self, interp):
        # Extract "llo" from "hello": start=2, len=3
        assert run(interp, '2 3 "hello" SUBSTR . CR') == "llo \n"

    def test_char(self, interp):
        assert run(interp, 'CHAR A . CR') == "65 \n"

    def test_bracket_char_compiled(self, interp):
        result = run(interp, ': T [CHAR] A . ; T CR')
        assert "65" in result

    def test_c_quote(self, interp):
        result = run(interp, ': T C" hello" . ; T CR')
        assert "hello" in result


class TestWithin:
    def test_within_true(self, interp):
        assert run(interp, '5 1 10 WITHIN . CR') == "-1 \n"

    def test_within_false_low(self, interp):
        assert run(interp, '0 1 10 WITHIN . CR') == "0 \n"

    def test_within_false_high(self, interp):
        assert run(interp, '10 1 10 WITHIN . CR') == "0 \n"

    def test_within_boundary(self, interp):
        assert run(interp, '1 1 10 WITHIN . CR') == "-1 \n"


class TestNewFloatOps:
    def test_fabs(self, interp):
        result = run(interp, '-3.14 FABS . CR')
        assert "3.14" in result

    def test_fnegate(self, interp):
        result = run(interp, '3.14 FNEGATE . CR')
        assert "-3.14" in result

    def test_pi(self, interp):
        result = run(interp, 'PI . CR')
        assert "3.14159" in result

    def test_fpow(self, interp):
        result = run(interp, '3.0 2.0 F** . CR')
        assert "9" in result


class TestExceptions:
    def test_throw_catch(self, interp):
        # Define a word that throws, catch it
        code = ': THROWER 42 THROW ; CATCH THROWER . CR'
        result = run(interp, code)
        assert "42" in result  # CATCH pushes the throw code

    def test_catch_no_throw(self, interp):
        code = ': SAFE 99 . ; CATCH SAFE . CR'
        result = run(interp, code)
        assert "99" in result
        assert "0" in result  # CATCH pushes 0 when no throw

    def test_abort(self, interp):
        with pytest.raises(ForthError, match="ABORT"):
            interp.eval("1 2 3 ABORT")


class TestMemoryOps:
    def test_erase(self, interp):
        # ERASE ( addr len -- )  addr deeper, len on top
        code = 'ARRAY ARR 5 99 0 ARR []! 99 1 ARR []! ARR 5 ERASE 0 ARR []@ . CR'
        assert run(interp, code) == "0 \n"

    def test_fill(self, interp):
        # FILL ( addr len val -- )  addr deepest, val on top
        code = 'ARRAY ARR 5 ARR 5 7 FILL 3 ARR []@ . CR'
        assert run(interp, code) == "7 \n"

    def test_move(self, interp):
        # MOVE ( src dst len -- )  src deepest, len on top
        code = '''ARRAY SRC 3 10 0 SRC []! 20 1 SRC []! 30 2 SRC []!
        ARRAY DST 3 SRC DST 3 MOVE 0 DST []@ . 1 DST []@ . 2 DST []@ . CR'''
        result = run(interp, code)
        assert "10" in result and "20" in result and "30" in result


class TestArraySize:
    def test_array_size(self, interp):
        assert run(interp, 'ARRAY ARR 42 ARR ARRAY-SIZE . CR') == "42 \n"


class TestUtility:
    def test_words_count(self, interp):
        result = run(interp, 'WORDS-COUNT . CR')
        assert int(result.strip()) > 50

    def test_version(self, interp):
        result = run(interp, 'VERSION')
        assert "3.0" in result

    def test_dot_s_detailed(self, interp):
        result = run(interp, '1 2 "hello" .S! CR')
        assert "1" in result and "2" in result and '"hello"' in result

    def test_dot_r(self, interp):
        result = run(interp, '42 5 .R CR')
        assert "42" in result

    def test_spaces(self, interp):
        result = run(interp, '3 SPACES 42 . CR')
        assert "   " in result and "42" in result

    def test_seed_random(self, interp):
        result = run(interp, '42 SEED 10 RANDOM . CR')
        assert result.strip().isdigit()
        # Should be in [0, 10)
        val = int(result.strip())
        assert 0 <= val < 10

    def test_reset(self, interp):
        result = run(interp, '1 2 3 RESET DEPTH . CR')
        assert "0" in result


class TestCreateWord:
    def test_create(self, interp):
        assert run(interp, 'CREATE MYVAR 42 MYVAR ! MYVAR @ . CR') == "42 \n"

    def test_2variable(self, interp):
        # 2VARIABLE creates a 2-cell array-like; use []! and []@
        code = '2VARIABLE D 10 0 D []! 20 1 D []! 0 D []@ . 1 D []@ . CR'
        result = run(interp, code)
        assert "10" in result and "20" in result


class TestUnloop:
    def test_unloop_with_exit(self, interp):
        code = ': T 10 0 DO I . I 5 = IF UNLOOP EXIT THEN LOOP ; T CR'
        result = run(interp, code)
        assert "0" in result and "5" in result


class TestRecursionLimit:
    def test_recursion_limit(self, interp):
        code = ': RECURSE-INF DUP 0 > IF DUP 1- RECURSE DROP THEN ; 10000 RECURSE-INF'
        with pytest.raises(ForthError, match="recursion limit"):
            interp.eval(code)

    def test_stack_overflow_limit(self, interp):
        i = ForthInterpreter(output=io.StringIO(), max_stack=100)
        # Push 101 items to trigger stack overflow
        code = ": FILL 1 FILL ; 0 FILL"
        with pytest.raises(ForthError, match="stack overflow"):
            i.eval(code)


class TestInclude:
    def test_include_file(self, interp, tmp_path):
        forth_file = tmp_path / "test.fs"
        forth_file.write_text("42 . CR\n")
        result = run(interp, f'INCLUDE {forth_file}')
        assert "42" in result


class TestDotParen:
    def test_dot_paren(self, interp):
        result = run(interp, '.( hello world) CR')
        assert "hello world" in result


class TestBracketChar:
    def test_bracket_char_in_definition(self, interp):
        result = run(interp, ': T [CHAR] X EMIT ; T CR')
        assert "X" in result