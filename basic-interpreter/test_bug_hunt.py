#!/usr/bin/env python3
"""Bug hunt test script for the BASIC interpreter."""
import sys
import io
import os
import tempfile
sys.path.insert(0, '/root/projects/creative-projects/basic-interpreter')
from basic import Interpreter, BasicRuntimeError, BasicSyntaxError

def test_bug_select_case_fallthrough():
    """BUG: SELECT CASE falls through to next CASE after matching one."""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 LET X = 1
20 SELECT CASE X
30 CASE 1
40   PRINT "matched one"
50 CASE 2
60   PRINT "should not print"
70 CASE ELSE
80   PRINT "should not print either"
90 END SELECT
100 PRINT "after select"
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    # BUG: Currently "should not print" appears because execution falls through
    # from the matched CASE 1 into CASE 2 and CASE ELSE bodies
    lines = [l.strip() for l in output.strip().split('\n') if l.strip()]
    unexpected = "should not print" in output
    if unexpected:
        print(f"BUG CONFIRMED: SELECT CASE fall-through — got: {output!r}")
        return True
    else:
        print(f"OK: No fall-through — got: {output!r}")
        return False

def test_bug_select_case_else_fallthrough():
    """BUG: CASE ELSE body also falls through to lines after END SELECT."""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 LET X = 99
20 SELECT CASE X
30 CASE 1
40   PRINT "one"
50 CASE ELSE
60   PRINT "else"
70 END SELECT
80 PRINT "done"
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    # Should print "else" and "done", but check if extra output appears
    lines = [l.strip() for l in output.strip().split('\n') if l.strip()]
    if "else" in output and "done" in output:
        print(f"OK: CASE ELSE + done — got: {output!r}")
        return False
    print(f"BUG: Missing expected output — got: {output!r}")
    return True

def test_bug_nested_for_gosub():
    """Test nested FOR with GOSUB inside doesn't corrupt for_stack."""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 GOSUB 100
20 END
100 FOR I = 1 TO 3
110   PRINT I
120 NEXT I
130 RETURN
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    # Should print 1, 2, 3
    if "1" in output and "2" in output and "3" in output:
        print(f"OK: Nested FOR/GOSUB — got: {output!r}")
        return False
    print(f"BUG: Nested FOR/GOSUB — got: {output!r}")
    return True

def test_bug_on_goto_out_of_range():
    """Bug: ON GOTO with value 0 or negative should not crash."""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 LET X = 0
20 ON X GOTO 100, 200
30 PRINT "fell through"
40 END
100 PRINT "bug"
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    # Value 0 is out of range (1..2), should fall through
    if "fell through" in output and "bug" not in output:
        print(f"OK: ON GOTO out of range — got: {output!r}")
        return False
    print(f"BUG: ON GOTO out of range — got: {output!r}")
    return True

def test_bug_negative_array_index():
    """Bug: Negative array index should raise error, not crash."""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 DIM A(10)
20 LET A(-1) = 5
"""
    interp.load(source)
    try:
        interp.run()
        print(f"BUG: No error for negative index")
        return True
    except BasicRuntimeError as e:
        if "Negative" in str(e):
            print(f"OK: Negative array index error — {e}")
            return False
        print(f"BUG: Wrong error for negative index — {e}")
        return True

def test_bug_for_step_zero():
    """Bug: FOR with step 0 should raise error."""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 FOR I = 1 TO 10 STEP 0
20 PRINT I
30 NEXT I
"""
    interp.load(source)
    try:
        interp.run()
        print(f"BUG: No error for FOR STEP 0")
        return True
    except BasicRuntimeError as e:
        if "zero" in str(e).lower():
            print(f"OK: FOR STEP 0 error — {e}")
            return False
        print(f"OK: Got error for STEP 0 — {e}")
        return False

def test_bug_string_array_index():
    """Test that string arrays work correctly."""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 DIM N$(5)
20 LET N$(1) = "Alice"
30 LET N$(2) = "Bob"
40 PRINT N$(1)
50 PRINT N$(2)
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    # Should print Alice and Bob
    if "Alice" in output and "Bob" in output:
        print(f"OK: String arrays — got: {output!r}")
        return False
    print(f"BUG: String arrays — got: {output!r}")
    return True

def test_bug_mixed_type_comparison():
    """Bug: Comparing string with number should not crash."""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 IF "hello" = 5 THEN PRINT "equal" ELSE PRINT "not equal"
"""
    interp.load(source)
    try:
        interp.run()
        output = interp.stdout.getvalue()
        # String "hello" vs number 5 — should not be equal
        if "not equal" in output:
            print(f"OK: Mixed type comparison — got: {output!r}")
            return False
        print(f"INFO: Mixed type comparison result — got: {output!r}")
        return False
    except Exception as e:
        print(f"BUG: Mixed type comparison crashed — {e}")
        return True

def test_bug_mid_string_zero_start():
    """Test MID$ with start=1 (BASIC 1-indexed)."""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 PRINT MID$("Hello", 1, 3)
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    # MID$("Hello", 1, 3) should return "Hel" (chars 1-3)
    if "Hel" in output:
        print(f"OK: MID$ start=1 — got: {output!r}")
        return False
    print(f"BUG: MID$ start=1 — got: {output!r}")
    return True

def test_bug_right_string_zero():
    """Test RIGHT$ with n=0 should return empty string."""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 LET R$ = RIGHT$("Hello", 0)
20 PRINT LEN(R$)
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    if "0" in output:
        print(f"OK: RIGHT$ 0 — got: {output!r}")
        return False
    print(f"BUG: RIGHT$ 0 — got: {output!r}")
    return True

def test_bug_empty_data():
    """Test READ when all DATA has been consumed."""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 READ A
20 READ B
30 DATA 1
"""
    interp.load(source)
    try:
        interp.run()
        print(f"BUG: No error for out of DATA")
        return True
    except BasicRuntimeError as e:
        if "DATA" in str(e).upper():
            print(f"OK: Out of DATA error — {e}")
            return False
        print(f"OK: Got error — {e}")
        return False

def test_bug_gosub_return_stack():
    """Test GOSUB/RETURN nesting depth."""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 GOSUB 100
20 END
100 GOSUB 200
110 RETURN
200 PRINT "deep"
210 RETURN
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    if "deep" in output:
        print(f"OK: Nested GOSUB — got: {output!r}")
        return False
    print(f"BUG: Nested GOSUB — got: {output!r}")
    return True

def test_bug_file_not_closed_on_error():
    """Test files are cleaned up when loading a new program after error."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.bas', delete=False) as tmp:
        tmp.write("test\n")
        tmp_path = tmp.name

    try:
        interp = Interpreter(stdout=io.StringIO())
        source = f"""
10 OPEN "{tmp_path}" FOR INPUT AS #1
20 LET X = 1 / 0
"""
        interp._on_error_line = None  # no error handler
        interp.load(source)
        try:
            interp.run()
        except BasicRuntimeError:
            pass
        # File remains open after error during run — this is expected BASIC behavior
        # (files stay open until explicitly closed or program reload)
        # Verify that loading a new program closes the file
        interp.load("10 END")
        if 1 in interp._files:
            print("BUG: File not closed when loading new program")
            interp._files[1].close()
            return True
        print("OK: File closed on program reload")
        return False
    finally:
        os.unlink(tmp_path)

def test_bug_print_semicolon_no_newline():
    """Test PRINT with trailing semicolon suppresses newline."""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 PRINT "Hello";
20 PRINT " World"
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    if "Hello World" in output:
        print(f"OK: PRINT semicolon — got: {output!r}")
        return False
    print(f"BUG: PRINT semicolon — got: {output!r}")
    return True

def test_bug_dim_already_dimensioned():
    """Test DIM on already-dimensioned array raises error."""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 DIM A(10)
20 DIM A(20)
"""
    interp.load(source)
    try:
        interp.run()
        print(f"BUG: No error for re-dimensioning array")
        return True
    except BasicRuntimeError as e:
        if "already" in str(e).lower():
            print(f"OK: DIM already dimensioned error — {e}")
            return False
        print(f"OK: Got error — {e}")
        return False

def test_bug_for_negative_step():
    """Test FOR with negative step counts down correctly."""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 FOR I = 5 TO 1 STEP -1
20 PRINT I
30 NEXT I
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    # Should print 5, 4, 3, 2, 1
    has_all = all(str(i) in output for i in [5, 4, 3, 2, 1])
    if has_all:
        print(f"OK: FOR negative step — got: {output!r}")
        return False
    print(f"BUG: FOR negative step — got: {output!r}")
    return True

def test_bug_on_error_resume_next():
    """Test ON ERROR GOTO with RESUME NEXT."""
    interp = Interpreter(stdout=io.StringIO())
    source = """
10 ON ERROR GOTO 100
20 LET X = 1 / 0
30 PRINT "after error"
40 END
100 PRINT "caught"
110 RESUME NEXT
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    if "caught" in output and "after error" in output:
        print(f"OK: ON ERROR RESUME NEXT — got: {output!r}")
        return False
    print(f"INFO: ON ERROR RESUME NEXT — got: {output!r}")
    return False

# Run all tests
if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_bug_") and callable(v)]
    bugs_found = []
    ok_count = 0
    for test in tests:
        try:
            result = test()
            if result:
                bugs_found.append(test.__name__)
            else:
                ok_count += 1
        except Exception as e:
            print(f"CRASH: {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            bugs_found.append(test.__name__)
    print(f"\n{ok_count} OK, {len(bugs_found)} bugs found")
    if bugs_found:
        print(f"Bugs: {bugs_found}")
    sys.exit(1 if bugs_found else 0)