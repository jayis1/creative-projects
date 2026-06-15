#!/usr/bin/env python3
"""Test script for the BASIC interpreter - Phase 2 enhanced features."""
import sys
import io
import os
import tempfile
sys.path.insert(0, '/root/projects/creative-projects/basic-interpreter')
from basic import Interpreter

def test_do_loop_while():
    """DO WHILE...LOOP"""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 LET X = 1
20 DO WHILE X < 5
30 LET X = X + 1
40 LOOP
50 PRINT X
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "5" in output, f"Expected 5, got: {output!r}"
    print("PASS: test_do_loop_while")

def test_do_loop_until():
    """DO UNTIL...LOOP"""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 LET X = 1
20 DO UNTIL X >= 5
30 LET X = X + 1
40 LOOP
50 PRINT X
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "5" in output, f"Expected 5, got: {output!r}"
    print("PASS: test_do_loop_until")

def test_do_loop_post_while():
    """DO...LOOP WHILE"""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 LET X = 1
20 DO
30 LET X = X + 1
40 LOOP WHILE X < 5
50 PRINT X
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "5" in output, f"Expected 5, got: {output!r}"
    print("PASS: test_do_loop_post_while")

def test_do_loop_post_until():
    """DO...LOOP UNTIL"""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 LET X = 1
20 DO
30 LET X = X + 1
40 LOOP UNTIL X >= 5
50 PRINT X
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "5" in output, f"Expected 5, got: {output!r}"
    print("PASS: test_do_loop_post_until")

def test_select_case():
    """SELECT CASE basic"""
    interp = Interpreter(stdout=io.StringIO())
    source = """
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
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "three" in output and "one" not in output and "two" not in output, f"Expected 'three' only, got: {output!r}"
    print("PASS: test_select_case")

def test_select_case_is():
    """SELECT CASE with IS conditions"""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 LET X = 75
20 SELECT CASE X
30 CASE IS < 50
40   PRINT "low"
50 CASE IS < 80
60   PRINT "medium"
70 CASE ELSE
80   PRINT "high"
90 END SELECT
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "medium" in output and "low" not in output, f"Expected 'medium', got: {output!r}"
    print("PASS: test_select_case_is")

def test_select_case_range():
    """SELECT CASE with TO range"""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 LET X = 5
20 SELECT CASE X
30 CASE 1 TO 3
40   PRINT "small"
50 CASE 4 TO 6
60   PRINT "medium"
70 CASE ELSE
80   PRINT "large"
90 END SELECT
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "medium" in output and "small" not in output, f"Expected 'medium', got: {output!r}"
    print("PASS: test_select_case_range")

def test_erase():
    """ERASE statement"""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 DIM A(5)
20 LET A(3) = 42
30 ERASE A
40 PRINT A(3)
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    # After erase, A(3) should be 0 (default)
    assert "0" in output, f"Expected 0 after ERASE, got: {output!r}"
    print("PASS: test_erase")

def test_xor_operator():
    """XOR logical operator"""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 LET A = -1
20 LET B = 0
30 PRINT (A XOR B)
40 PRINT (A XOR A)
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    # -1 XOR 0 = -1 (true), -1 XOR -1 = 0 (false)
    assert "-1" in output and output.count("0") >= 1, f"Expected -1 and 0, got: {output!r}"
    print("PASS: test_xor_operator")

def test_eqv_operator():
    """EQV logical operator"""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 LET A = -1
20 LET B = -1
30 PRINT (A EQV B)
40 PRINT (A EQV 0)
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    # -1 EQV -1 = -1, -1 EQV 0 = 0
    assert "-1" in output, f"Expected -1, got: {output!r}"
    print("PASS: test_eqv_operator")

def test_imp_operator():
    """IMP logical operator"""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 PRINT (0 IMP 0)
20 PRINT (0 IMP -1)
30 PRINT (-1 IMP 0)
40 PRINT (-1 IMP -1)
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    # IMP: T IMP T=T, T IMP F=F, F IMP T=T, F IMP F=T
    assert "-1" in output, f"Expected -1 values, got: {output!r}"
    print("PASS: test_imp_operator")

def test_line_input():
    """LINE INPUT statement"""
    interp = Interpreter(stdin=io.StringIO("Hello World\n"), stdout=io.StringIO())
    source = """
10 LINE INPUT A$
20 PRINT A$
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "Hello World" in output, f"Expected 'Hello World', got: {output!r}"
    print("PASS: test_line_input")

def test_date_time_functions():
    """DATE$ and TIME$ functions"""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 LET D$ = DATE$
20 LET T$ = TIME$
30 PRINT LEN(D$)
40 PRINT LEN(T$)
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    # DATE$ format: "mm-dd-yyyy" (10 chars), TIME$ format: "hh:mm:ss" (8 chars)
    assert "10" in output and "8" in output, f"Expected 10 and 8, got: {output!r}"
    print("PASS: test_date_time_functions")

def test_lcase_ucase():
    """LCASE$ and UCASE$ functions"""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 PRINT LCASE$("HELLO")
20 PRINT UCASE$("hello")
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "hello" in output and "HELLO" in output, f"Expected hello and HELLO, got: {output!r}"
    print("PASS: test_lcase_ucase")

def test_sgn_fix():
    """SGN and FIX functions"""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 PRINT SGN(5)
20 PRINT SGN(-3)
30 PRINT SGN(0)
40 PRINT FIX(3.7)
50 PRINT FIX(-3.7)
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "1" in output and "-1" in output and "0" in output and "3" in output, f"Expected various values, got: {output!r}"
    print("PASS: test_sgn_fix")

def test_file_io():
    """OPEN, PRINT#, CLOSE, INPUT# file I/O"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.bas', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        interp = Interpreter(stdout=io.StringIO())
        # Write to file
        source1 = f"""
10 OPEN "{tmp_path}" FOR OUTPUT AS #1
20 PRINT# 1, "Hello from file"
30 CLOSE #1
"""
        interp.load(source1)
        interp.run()

        # Read from file
        interp2 = Interpreter(stdout=io.StringIO())
        source2 = f"""
10 OPEN "{tmp_path}" FOR INPUT AS #1
20 INPUT# 1, A$
30 CLOSE #1
40 PRINT A$
"""
        interp2.load(source2)
        interp2.run()
        output = interp2.stdout.getvalue()
        assert "Hello from file" in output, f"Expected 'Hello from file', got: {output!r}"
        print("PASS: test_file_io")
    finally:
        os.unlink(tmp_path)

def test_file_append():
    """File append mode"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.bas', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        interp = Interpreter(stdout=io.StringIO())
        source1 = f"""
10 OPEN "{tmp_path}" FOR OUTPUT AS #1
20 PRINT# 1, "first"
30 CLOSE #1
40 OPEN "{tmp_path}" FOR APPEND AS #2
50 PRINT# 2, "second"
60 CLOSE #2
"""
        interp.load(source1)
        interp.run()

        with open(tmp_path, 'r') as f:
            content = f.read()
        assert "first" in content and "second" in content, f"Expected both lines, got: {content!r}"
        print("PASS: test_file_append")
    finally:
        os.unlink(tmp_path)

def test_beep():
    """BEEP statement (should not crash)"""
    interp = Interpreter(stdout=io.StringIO())
    source = '10 BEEP'
    interp.load(source)
    interp.run()
    print("PASS: test_beep")

def test_environ_function():
    """ENVIRON$ function"""
    interp = Interpreter(stdout=io.StringIO())
    os.environ['BASIC_TEST_VAR'] = 'test_value'
    source = '10 PRINT ENVIRON$("BASIC_TEST_VAR")'
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "test_value" in output, f"Expected 'test_value', got: {output!r}"
    del os.environ['BASIC_TEST_VAR']
    print("PASS: test_environ_function")

def test_fre_function():
    """FRE function"""
    interp = Interpreter(stdout=io.StringIO())
    source = '10 PRINT FRE(0)'
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "655360" in output, f"Expected 655360, got: {output!r}"
    print("PASS: test_fre_function")

def test_ltrim_rtrim():
    """LTRIM$ and RTRIM$ functions"""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 PRINT LTRIM$("  hello  ")
20 PRINT RTRIM$("  hello  ")
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "hello  " in output and "  hello" in output, f"Expected trimmed strings, got: {output!r}"
    print("PASS: test_ltrim_rtrim")

def test_on_error_goto():
    """ON ERROR GOTO error handling"""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 ON ERROR GOTO 100
20 LET X = 1 / 0
30 PRINT "after error"
40 END
100 PRINT "error caught"
110 RESUME 30
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    # Should catch the division by zero error and resume at line 30
    assert "error caught" in output, f"Expected 'error caught', got: {output!r}"
    print("PASS: test_on_error_goto")

def test_mandelbrot_still_works():
    """Mandelbrot example still works after refactor"""
    interp = Interpreter(stdout=io.StringIO())
    with open('/root/projects/creative-projects/basic-interpreter/examples/mandelbrot.bas') as f:
        source = f.read()
    interp.max_iterations = 500000
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "Mandelbrot" in output, f"Expected Mandelbrot in output"
    # Should have multiple lines of ASCII art
    lines = output.strip().split('\n')
    assert len(lines) > 5, f"Expected many lines of output, got {len(lines)}"
    print("PASS: test_mandelbrot_still_works")

def test_print_col_tracking():
    """Print column tracking with comma separator"""
    interp = Interpreter(stdout=io.StringIO())
    source = '10 PRINT "a", "b"'
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    # With column tracking, comma should tab to next zone
    assert "a" in output and "b" in output, f"Expected a and b, got: {output!r}"
    print("PASS: test_print_col_tracking")

def test_nested_do_loop():
    """Nested DO loops"""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 LET S = 0
20 LET I = 1
30 DO WHILE I <= 3
40   LET J = 1
50   DO WHILE J <= 3
60     LET S = S + I * J
70     LET J = J + 1
80   LOOP
90   LET I = I + 1
100 LOOP
110 PRINT S
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "36" in output, f"Expected 36, got: {output!r}"
    print("PASS: test_nested_do_loop")

# Run all tests
if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed out of {passed + failed}")
    sys.exit(1 if failed else 0)