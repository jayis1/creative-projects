"""Comprehensive test suite for the Forth interpreter."""
import io
import pytest
from forth import ForthInterpreter, ForthError


@pytest.fixture
def interp():
    """Fresh interpreter with StringIO output."""
    return ForthInterpreter(output=io.StringIO())


def run(interp, code):
    """Run code and return output string."""
    interp.stack.clear()
    interp.return_stack.clear()
    interp._reset_state()
    out = io.StringIO()
    interp.output = out
    interp.eval(code)
    return out.getvalue()


class TestArithmetic:
    def test_add(self, interp):
        assert run(interp, "3 4 + . CR") == "7 \n"

    def test_sub(self, interp):
        assert run(interp, "10 3 - . CR") == "7 \n"

    def test_mul(self, interp):
        assert run(interp, "6 7 * . CR") == "42 \n"

    def test_div(self, interp):
        assert run(interp, "20 4 / . CR") == "5 \n"

    def test_div_truncates_toward_zero(self, interp):
        assert run(interp, "-7 2 / . CR") == "-3 \n"

    def test_mod(self, interp):
        assert run(interp, "17 5 MOD . CR") == "2 \n"

    def test_mod_negative(self, interp):
        assert run(interp, "-7 3 MOD . CR") == "-1 \n"

    def test_divmod(self, interp):
        assert run(interp, "17 5 /MOD . . CR") == "3 2 \n"

    def test_negate(self, interp):
        assert run(interp, "5 NEGATE . CR") == "-5 \n"

    def test_abs(self, interp):
        assert run(interp, "-5 ABS . CR") == "5 \n"

    def test_min(self, interp):
        assert run(interp, "3 5 MIN . CR") == "3 \n"

    def test_max(self, interp):
        assert run(interp, "3 5 MAX . CR") == "5 \n"

    def test_power(self, interp):
        assert run(interp, "2 10 ** . CR") == "1024 \n"

    def test_1plus(self, interp):
        assert run(interp, "5 1+ . CR") == "6 \n"

    def test_1minus(self, interp):
        assert run(interp, "5 1- . CR") == "4 \n"

    def test_2star(self, interp):
        assert run(interp, "5 2* . CR") == "10 \n"

    def test_2slash(self, interp):
        assert run(interp, "10 2/ . CR") == "5 \n"

    def test_div_by_zero(self, interp):
        with pytest.raises(ForthError):
            interp.eval("1 0 / .")

    def test_mod_by_zero(self, interp):
        with pytest.raises(ForthError):
            interp.eval("1 0 MOD .")


class TestFloat:
    def test_fadd(self, interp):
        assert run(interp, "3.14 2.0 F+ . CR") == "5.14 \n"

    def test_fsub(self, interp):
        assert run(interp, "10.0 3.0 F- . CR") == "7 \n"

    def test_fmul(self, interp):
        assert run(interp, "3.0 4.0 F* . CR") == "12 \n"

    def test_fdiv(self, interp):
        assert run(interp, "10.0 4.0 F/ . CR") == "2.5 \n"

    def test_fsqrt(self, interp):
        assert run(interp, "16.0 FSQRT . CR") == "4 \n"

    def test_fsin(self, interp):
        result = run(interp, "0.0 FSIN . CR")
        assert "0" in result

    def test_fdiv_by_zero(self, interp):
        with pytest.raises(ForthError):
            interp.eval("1.0 0.0 F/ .")


class TestStackOps:
    def test_dup(self, interp):
        assert run(interp, "5 DUP . . CR") == "5 5 \n"

    def test_drop(self, interp):
        assert run(interp, "5 3 DROP . CR") == "5 \n"

    def test_swap(self, interp):
        assert run(interp, "1 2 SWAP . . CR") == "1 2 \n"

    def test_over(self, interp):
        assert run(interp, "1 2 OVER . . . CR") == "1 2 1 \n"

    def test_rot(self, interp):
        assert run(interp, "1 2 3 ROT . . . CR") == "1 3 2 \n"

    def test_2dup(self, interp):
        assert run(interp, "1 2 2DUP . . . . CR") == "2 1 2 1 \n"

    def test_2drop(self, interp):
        assert run(interp, "1 2 3 2DROP . CR") == "1 \n"

    def test_depth(self, interp):
        assert run(interp, "1 2 3 DEPTH . CR") == "3 \n"

    def test_pick(self, interp):
        assert run(interp, "1 2 3 0 PICK . CR") == "3 \n"

    def test_pick_1(self, interp):
        assert run(interp, "1 2 3 1 PICK . CR") == "2 \n"

    def test_roll(self, interp):
        # 1 ROLL on [1,2,3]: removes item at index 1 (value 2), puts on top → [1,3,2]
        # . . . prints top first: 2 3 1
        assert run(interp, "1 2 3 1 ROLL . . . CR") == "2 3 1 \n"

    def test_qdup_zero(self, interp):
        assert run(interp, "0 ?DUP . CR") == "0 \n"

    def test_qdup_nonzero(self, interp):
        assert run(interp, "5 ?DUP . . CR") == "5 5 \n"

    def test_stack_underflow(self, interp):
        with pytest.raises(ForthError):
            interp.eval("DROP")


class TestComparison:
    def test_eq(self, interp):
        assert run(interp, "5 5 = . CR") == "-1 \n"

    def test_ne(self, interp):
        assert run(interp, "5 3 <> . CR") == "-1 \n"

    def test_lt(self, interp):
        assert run(interp, "3 4 < . CR") == "-1 \n"

    def test_gt(self, interp):
        assert run(interp, "5 3 > . CR") == "-1 \n"

    def test_le(self, interp):
        assert run(interp, "3 3 <= . CR") == "-1 \n"

    def test_ge(self, interp):
        assert run(interp, "3 3 >= . CR") == "-1 \n"

    def test_0eq(self, interp):
        assert run(interp, "0 0= . CR") == "-1 \n"

    def test_0gt(self, interp):
        assert run(interp, "5 0> . CR") == "-1 \n"

    def test_0lt(self, interp):
        assert run(interp, "-5 0< . CR") == "-1 \n"


class TestBitwise:
    def test_and(self, interp):
        assert run(interp, "12 10 AND . CR") == "8 \n"

    def test_or(self, interp):
        assert run(interp, "12 10 OR . CR") == "14 \n"

    def test_xor(self, interp):
        assert run(interp, "12 10 XOR . CR") == "6 \n"

    def test_invert(self, interp):
        assert run(interp, "0 INVERT . CR") == "-1 \n"

    def test_lshift(self, interp):
        assert run(interp, "1 4 LSHIFT . CR") == "16 \n"

    def test_rshift(self, interp):
        assert run(interp, "16 2 RSHIFT . CR") == "4 \n"


class TestVariables:
    def test_variable(self, interp):
        assert run(interp, "VARIABLE X 42 X ! X @ . CR") == "42 \n"

    def test_plus_store(self, interp):
        assert run(interp, "VARIABLE X 10 X ! 5 X +! X @ . CR") == "15 \n"

    def test_constant(self, interp):
        assert run(interp, "42 CONSTANT ANSWER ANSWER . CR") == "42 \n"

    def test_value(self, interp):
        assert run(interp, "99 VALUE V V . 42 TO V V . CR") == "99 42 \n"

    def test_array(self, interp):
        result = run(interp, "ARRAY ARR 5 99 2 ARR []! 2 ARR []@ . CR")
        assert result == "99 \n"


class TestControlFlow:
    def test_if_true(self, interp):
        assert run(interp, ": T 1 IF 99 . THEN ; T CR") == "99 \n"

    def test_if_false(self, interp):
        assert run(interp, ": T 0 IF 99 . THEN ; T CR") == "\n"

    def test_if_else_true(self, interp):
        assert run(interp, ": T 1 IF 1 . ELSE 2 . THEN ; T CR") == "1 \n"

    def test_if_else_false(self, interp):
        assert run(interp, ": T 0 IF 1 . ELSE 2 . THEN ; T CR") == "2 \n"

    def test_begin_until(self, interp):
        assert run(interp, ": T 0 BEGIN 1+ DUP 3 = UNTIL . ; T CR") == "3 \n"

    def test_begin_while_repeat(self, interp):
        assert run(interp, ": T 5 BEGIN DUP 0 > WHILE DUP . 1- REPEAT DROP ; T CR") == "5 4 3 2 1 \n"

    def test_do_loop(self, interp):
        assert run(interp, ": T 5 0 DO I . LOOP ; T CR") == "0 1 2 3 4 \n"

    def test_do_loop_sum(self, interp):
        assert run(interp, ": T 0 10 0 DO I + LOOP ; T . CR") == "45 \n"

    def test_plus_loop(self, interp):
        assert run(interp, ": T 5 0 DO I . 2 +LOOP ; T CR") == "0 2 4 \n"

    def test_leave(self, interp):
        assert run(interp, ": T 10 0 DO I . I 5 = IF LEAVE THEN LOOP ; T CR") == "0 1 2 3 4 5 \n"

    def test_exit(self, interp):
        assert run(interp, ": T 1 IF 99 . EXIT 0 . THEN ; T CR") == "99 \n"

    def test_recurse_factorial(self, interp):
        assert run(interp, ": FACT DUP 1 > IF DUP 1- RECURSE * THEN ; 5 FACT . CR") == "120 \n"

    def test_recurse_fibonacci(self, interp):
        assert run(interp, ": FIB DUP 2 < IF EXIT THEN DUP 1- RECURSE SWAP 2- RECURSE + ; 10 FIB . CR") == "55 \n"

    def test_nested_loops(self, interp):
        assert run(interp, ": T 3 0 DO 3 0 DO I J 10 * + . LOOP LOOP ; T CR") == "0 1 2 10 11 12 20 21 22 \n"

    def test_again(self, interp):
        # AGAIN creates infinite loop; use EXIT to break
        result = run(interp, ": T 3 BEGIN DUP . 1- DUP 0 = IF DROP EXIT THEN AGAIN ; T CR")
        assert result == "3 2 1 \n"


class TestStrings:
    def test_dot_quote(self, interp):
        assert run(interp, ': T ." Hello World" ; T CR') == "Hello World\n"

    def test_string_literal(self, interp):
        # String literals on stack
        result = run(interp, '"hello" . CR')
        assert "hello" in result

    def test_type(self, interp):
        assert run(interp, '"hello" TYPE CR') == "hello\n"


class TestErrors:
    def test_unknown_word(self, interp):
        with pytest.raises(ForthError, match="unknown word"):
            interp.eval("FOOBAR")

    def test_stack_underflow(self, interp):
        with pytest.raises(ForthError, match="stack underflow"):
            interp.eval("DROP DROP")

    def test_div_by_zero(self, interp):
        with pytest.raises(ForthError, match="division by zero"):
            interp.eval("1 0 /")

    def test_error_recovery(self, interp):
        """After an error, the interpreter should recover."""
        with pytest.raises(ForthError):
            interp.eval("DROP")  # underflow
        # Should work fine after error
        assert run(interp, "3 4 + . CR") == "7 \n"

    def test_bad_address(self, interp):
        with pytest.raises(ForthError, match="bad address"):
            interp.eval("42 @")


class TestUtility:
    def test_words(self, interp):
        result = run(interp, "WORDS")
        assert "DUP" in result
        assert "SWAP" in result

    def test_dot_s(self, interp):
        assert run(interp, "1 2 3 .S CR") == "<1 2 3>\n"

    def test_true_false(self, interp):
        assert run(interp, "TRUE . CR") == "-1 \n"
        assert run(interp, "FALSE . CR") == "0 \n"

    def test_see(self, interp):
        result = run(interp, ": SQ DUP * ; SEE SQ CR")
        assert "SQ" in result

    def test_dump(self, interp):
        result = run(interp, "255 16 DUMP CR")
        assert "0xff" in result


class TestPrimes:
    """Test the primes example."""
    def test_primes(self, interp):
        code = '''
        : PRIME?
            DUP 2 < IF DROP FALSE EXIT THEN
            DUP 2 = IF DROP TRUE EXIT THEN
            DUP 2 MOD 0 = IF DROP FALSE EXIT THEN
            DUP 3 BEGIN
                2DUP >
            WHILE
                2DUP MOD 0 =
                IF 2DROP FALSE EXIT THEN
                2 +
            REPEAT
            2DROP TRUE ;
        : .PRIMES 30 2 DO I PRIME? IF I . THEN LOOP ;
        .PRIMES CR
        '''
        result = run(interp, code)
        assert result == "2 3 5 7 11 13 17 19 23 29 \n"


class TestCaseOf:
    """Test CASE/OF/ENDOF/ENDCASE."""
    def test_case_match(self, interp):
        code = '''
        : GRADE
            CASE
                0 OF ." F" ENDOF
                1 OF ." D" ENDOF
                2 OF ." C" ENDOF
                3 OF ." B" ENDOF
                4 OF ." A" ENDOF
                ." ?"
            ENDCASE ;
        3 GRADE CR
        '''
        result = run(interp, code)
        assert "B" in result

    def test_case_default(self, interp):
        code = '''
        : GRADE
            CASE
                0 OF ." F" ENDOF
                1 OF ." D" ENDOF
                ." ?"
            ENDCASE ;
        99 GRADE CR
        '''
        result = run(interp, code)
        assert "?" in result

    def test_case_first_match(self, interp):
        code = '''
        : TEST
            CASE
                1 OF ." one" ENDOF
                2 OF ." two" ENDOF
            ENDCASE ;
        1 TEST CR
        '''
        result = run(interp, code)
        assert "one" in result