"""Quick test script for the Forth interpreter."""
import io
from forth import ForthInterpreter

out = io.StringIO()
interp = ForthInterpreter(output=out)

tests = [
    ("3 4 + . CR", "7 \n", "basic add"),
    (": SQUARE DUP * ; 5 SQUARE . CR", "25 \n", "square word"),
    (": COUNTDOWN 10 0 DO I . LOOP CR ; COUNTDOWN", "0 1 2 3 4 5 6 7 8 9 \n", "do loop"),
    (": FACT DUP 1 > IF DUP 1 - RECURSE * THEN ; 5 FACT . CR", "120 \n", "factorial"),
    ("VARIABLE COUNTER 42 COUNTER ! COUNTER @ . CR", "42 \n", "variable"),
    (": TEST-IF 5 0 > IF 99 . THEN ; TEST-IF CR", "99 \n", "if true"),
    (": TEST-ELSE 5 3 > IF 1 . ELSE 2 . THEN ; TEST-ELSE CR", "1 \n", "if-else"),
    (": TEST-BEGIN 0 BEGIN 1 + DUP 3 = UNTIL . ; TEST-BEGIN CR", "3 \n", "begin-until"),
    (": TEST-WHILE 5 BEGIN DUP 0 > WHILE DUP . 1 - REPEAT DROP ; TEST-WHILE CR", "5 4 3 2 1 \n", "begin-while-repeat"),
    (": SUM 0 10 0 DO I + LOOP ; SUM . CR", "45 \n", "sum 0..9"),
    ("10 3 / . CR", "3 \n", "integer div"),
    ("10 3 MOD . CR", "1 \n", "modulo"),
    ("-10 3 / . CR", "-3 \n", "neg div trunc"),
    ("-10 3 MOD . CR", "-1 \n", "neg mod"),
    ("3 4 < . CR", "-1 \n", "less than"),
    ("3 4 > . CR", "0 \n", "greater than"),
    ("5 .S DROP CR", "<5>\n", "stack display"),
    # +LOOP: count down from 4 to 0 (5 0 DO → start=0, limit=5; -1 +LOOP: 0 -1 crosses 0 boundary)
    # Actually: 0 DO with -1 +LOOP: index starts at 0, first iteration prints 0,
    # then 0+(-1) = -1 < 0 so loop ends. Only prints 0.
    # For counting down we want: 5 0 DO → start=0 limit=5, that's wrong direction.
    # Correct: 5 1 DO I . -1 +LOOP → start=1, limit=5, prints 1, then 0 >= 0 so continue,
    # prints 0, then -1 < 0, loop ends. → "1 0 "
    # Actually let's use a simpler test:
    (": COUNTUP 5 0 DO I . 2 +LOOP ; COUNTUP CR", "0 2 4 \n", "plus loop +2"),
    # LEAVE test
    (": LEAVETEST 10 0 DO I . I 5 = IF LEAVE THEN LOOP ; LEAVETEST CR", "0 1 2 3 4 5 \n", "leave"),
    # Constants
    ("42 CONSTANT MEANING MEANING . CR", "42 \n", "constant"),
    # Nested DO loops
    (": NESTED 3 0 DO 3 0 DO I J 10 * + . LOOP LOOP ; NESTED CR", "0 1 2 10 11 12 20 21 22 \n", "nested loops"),
    # Value and TO
    ("99 VALUE MYVAL MYVAL . 42 TO MYVAL MYVAL . CR", "99 42 \n", "value and TO"),
    # Float
    ("3.14 2.0 F+ . CR", "5.14 \n", "float add"),
    # Bitwise
    ("12 10 AND . CR", "8 \n", "bitwise and"),
    ("12 10 OR . CR", "14 \n", "bitwise or"),
    ("255 4 LSHIFT . CR", "4080 \n", "left shift"),
    # Recursion: fib
    (": FIB DUP 2 < IF EXIT THEN DUP 1 - RECURSE SWAP 2 - RECURSE + ; 0 FIB . 1 FIB . 10 FIB . CR", "0 1 55 \n", "fibonacci"),
]

passed = 0
failed = 0
for code, expected, desc in tests:
    # Reset state before each test
    interp.stack.clear()
    interp.return_stack.clear()
    out.truncate(0)
    out.seek(0)
    try:
        interp.eval(code)
        result = out.getvalue()
        if result == expected:
            passed += 1
            print(f"  PASS: {desc}")
        else:
            failed += 1
            print(f"  FAIL: {desc} — got {repr(result)}, expected {repr(expected)}")
    except Exception as e:
        failed += 1
        print(f"  ERROR: {desc} — {e}")
        interp._reset_state()

print(f"\n{passed}/{passed+failed} passed")