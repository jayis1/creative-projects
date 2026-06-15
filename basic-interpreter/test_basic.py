#!/usr/bin/env python3
"""Test script for the BASIC interpreter."""
import sys
import io
sys.path.insert(0, '/root/projects/creative-projects/basic-interpreter')
from basic import Interpreter

def test_one_liner():
    interp = Interpreter(stdout=io.StringIO())
    interp.load('PRINT 2+2')
    interp.run()
    output = interp.stdout.getvalue()
    assert "4" in output, f"Expected 4 in output, got: {output!r}"
    print("PASS: test_one_liner")

def test_hello():
    interp = Interpreter(stdout=io.StringIO())
    interp.load('10 PRINT "Hello, World!"')
    interp.run()
    output = interp.stdout.getvalue()
    assert "Hello, World!" in output, f"Expected Hello in output, got: {output!r}"
    print("PASS: test_hello")

def test_for_next():
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 LET S = 0
20 FOR I = 1 TO 5
30 LET S = S + I
40 NEXT I
50 PRINT S
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "15" in output, f"Expected 15 in output, got: {output!r}"
    print("PASS: test_for_next")

def test_for_next_step():
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 LET S = 0
20 FOR I = 10 TO 1 STEP -1
30 LET S = S + I
40 NEXT I
50 PRINT S
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "55" in output, f"Expected 55 in output, got: {output!r}"
    print("PASS: test_for_next_step")

def test_goto():
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 LET X = 10
20 GOTO 40
30 LET X = 999
40 PRINT X
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "10" in output and "999" not in output, f"Expected 10 in output, got: {output!r}"
    print("PASS: test_goto")

def test_gosub():
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 GOSUB 100
20 PRINT "back"
30 END
100 PRINT "sub"
110 RETURN
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "sub" in output and "back" in output, f"Expected 'sub' and 'back', got: {output!r}"
    print("PASS: test_gosub")

def test_if_then_else():
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 LET X = 5
20 IF X > 3 THEN PRINT "big" ELSE PRINT "small"
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "big" in output and "small" not in output, f"Expected 'big', got: {output!r}"
    print("PASS: test_if_then_else")

def test_data_read():
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 READ A, B, C
20 PRINT A; B; C
30 DATA 10, 20, 30
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "10" in output and "20" in output and "30" in output, f"Expected 10, 20, 30, got: {output!r}"
    print("PASS: test_data_read")

def test_dim_array():
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 DIM A(5)
20 LET A(1) = 100
30 LET A(3) = 300
40 PRINT A(1); A(3)
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "100" in output and "300" in output, f"Expected 100, 300, got: {output!r}"
    print("PASS: test_dim_array")

def test_def_fn():
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 DEF FN DOUBLE(X) = X * 2
20 PRINT FN DOUBLE(5)
30 PRINT FN DOUBLE(10)
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "10" in output and "20" in output, f"Expected 10, 20, got: {output!r}"
    print("PASS: test_def_fn")

def test_string_functions():
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 LET A$ = "Hello"
20 PRINT LEN(A$)
30 PRINT LEFT$(A$, 3)
40 PRINT RIGHT$(A$, 2)
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "5" in output and "Hel" in output and "lo" in output, f"Expected 5, Hel, lo, got: {output!r}"
    print("PASS: test_string_functions")

def test_while_wend():
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 LET X = 1
20 WHILE X < 5
30 LET X = X + 1
40 WEND
50 PRINT X
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "5" in output, f"Expected 5, got: {output!r}"
    print("PASS: test_while_wend")

def test_comparison_returns_minus1():
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 PRINT (5 > 3)
20 PRINT (3 > 5)
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "-1" in output and "0" in output, f"Expected -1 and 0, got: {output!r}"
    print("PASS: test_comparison_returns_minus1")

def test_logical_operators():
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 IF (5 > 3) AND (2 < 4) THEN PRINT "both"
20 IF (5 > 3) OR (2 > 4) THEN PRINT "either"
30 IF NOT (3 > 5) THEN PRINT "not"
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "both" in output and "either" in output and "not" in output, f"Expected all three, got: {output!r}"
    print("PASS: test_logical_operators")

def test_nested_for():
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 LET S = 0
20 FOR I = 1 TO 3
30   FOR J = 1 TO 3
40     LET S = S + I * J
50   NEXT J
60 NEXT I
70 PRINT S
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    # Sum of i*j for i=1..3, j=1..3 = (1+2+3)*(1+2+3) = 36
    assert "36" in output, f"Expected 36, got: {output!r}"
    print("PASS: test_nested_for")

def test_on_goto():
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 LET X = 2
20 ON X GOTO 100, 200, 300
30 END
100 PRINT "one"
110 END
200 PRINT "two"
210 END
300 PRINT "three"
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "two" in output and "one" not in output and "three" not in output, f"Expected 'two' only, got: {output!r}"
    print("PASS: test_on_goto")

def test_swap():
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 LET A = 10
20 LET B = 20
30 SWAP A, B
40 PRINT A; B
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "20" in output and "10" in output, f"Expected 20, 10, got: {output!r}"
    print("PASS: test_swap")

def test_math_functions():
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 PRINT ABS(-5)
20 PRINT INT(3.7)
30 PRINT SQR(16)
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "5" in output and "3" in output and "4" in output, f"Expected 5, 3, 4, got: {output!r}"
    print("PASS: test_math_functions")

def test_string_concat():
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 LET A$ = "Hello" + " " + "World"
20 PRINT A$
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "Hello World" in output, f"Expected 'Hello World', got: {output!r}"
    print("PASS: test_string_concat")

def test_restore():
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 READ A
20 READ B
30 RESTORE
40 READ C
50 PRINT A; B; C
60 DATA 1, 2, 3
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "1" in output and "2" in output, f"Expected 1, 2, got: {output!r}"
    print("PASS: test_restore")

def test_immediate_mode():
    interp = Interpreter(stdout=io.StringIO())
    interp.load('LET X = 42 : PRINT X')
    interp.run()
    output = interp.stdout.getvalue()
    assert "42" in output, f"Expected 42, got: {output!r}"
    print("PASS: test_immediate_mode")

def test_colon_separator():
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 LET A = 1 : LET B = 2 : PRINT A + B
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "3" in output, f"Expected 3, got: {output!r}"
    print("PASS: test_colon_separator")

def test_exponentiation():
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 PRINT 2 ^ 10
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "1024" in output, f"Expected 1024, got: {output!r}"
    print("PASS: test_exponentiation")

def test_integer_division():
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 PRINT 7 \\ 2
20 PRINT 7 MOD 2
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "3" in output and "1" in output, f"Expected 3 and 1, got: {output!r}"
    print("PASS: test_integer_division")

# Run all tests
if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed out of {passed + failed}")
    sys.exit(1 if failed else 0)