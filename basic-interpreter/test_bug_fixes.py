#!/usr/bin/env python3
"""Tests for bugs found and fixed in Phase 3 bug hunt."""
import sys
import io
import os
import tempfile
sys.path.insert(0, '/root/projects/creative-projects/basic-interpreter')
from basic import Interpreter, BasicRuntimeError, BasicSyntaxError


def test_select_case_no_fallthrough():
    """Bug #1: SELECT CASE fell through to subsequent CASE branches after matching."""
    interp = Interpreter(stdout=io.StringIO())
    source = """\
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
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "one" in output, f"Expected 'one' in output, got: {output!r}"
    assert "two" not in output, f"Bug: 'two' should not appear (fall-through), got: {output!r}"
    assert "other" not in output, f"Bug: 'other' should not appear (fall-through), got: {output!r}"
    assert "done" in output, f"Expected 'done' in output, got: {output!r}"


def test_select_case_else_no_fallthrough():
    """Bug #1 variant: CASE ELSE body should not fall through after END SELECT."""
    interp = Interpreter(stdout=io.StringIO())
    source = """\
10 LET X = 99
20 SELECT CASE X
30 CASE 1
40   PRINT "one"
50 CASE ELSE
60   PRINT "else"
70 END SELECT
80 PRINT "after"
"""
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "else" in output, f"Expected 'else', got: {output!r}"
    assert "one" not in output, f"Bug: 'one' should not appear, got: {output!r}"
    assert "after" in output, f"Expected 'after', got: {output!r}"


def test_integer_division_truncates_toward_zero():
    """Bug #3: Integer division (\\) used Python floor division instead of truncation."""
    interp = Interpreter(stdout=io.StringIO())
    source = '10 PRINT -7 \\ 2'
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    # -7 \ 2 should be -3 (truncate toward zero), not -4 (floor division)
    assert "-3" in output, f"Expected -3 (truncation toward zero), got: {output!r}"


def test_integer_division_positive():
    """Bug #3 variant: Positive integer division should still work correctly."""
    interp = Interpreter(stdout=io.StringIO())
    source = '10 PRINT 7 \\ 2'
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "3" in output, f"Expected 3, got: {output!r}"


def test_mod_follows_dividend_sign():
    """Bug #4: MOD used Python modulo (divisor sign) instead of BASIC modulo (dividend sign)."""
    interp = Interpreter(stdout=io.StringIO())
    source = '10 PRINT -7 MOD 2'
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    # -7 MOD 2 should be -1 (same sign as dividend), not 1 (Python modulo)
    assert "-1" in output, f"Expected -1 (BASIC MOD), got: {output!r}"


def test_mod_positive():
    """Bug #4 variant: Positive MOD should still work correctly."""
    interp = Interpreter(stdout=io.StringIO())
    source = '10 PRINT 7 MOD 2'
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    assert "1" in output, f"Expected 1, got: {output!r}"


def test_format_value_int():
    """Bug #5: _format_value didn't handle Python int values (from logical operators)."""
    interp = Interpreter(stdout=io.StringIO())
    source = '10 PRINT 5 = 5'
    interp.load(source)
    interp.run()
    output = interp.stdout.getvalue()
    # 5 = 5 returns -1 (int), which should be formatted with leading/trailing spaces
    assert "-1" in output, f"Expected -1, got: {output!r}"


def test_file_cleanup_on_reload():
    """Bug #2: Files were leaked when loading a new program."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
        tmp.write("hello\n")
        tmp_path = tmp.name
    try:
        interp = Interpreter(stdout=io.StringIO())
        source = f'10 OPEN "{tmp_path}" FOR INPUT AS #1'
        interp.load(source)
        interp.run()
        assert 1 in interp._files, "File should be open"
        # Loading a new program should close the file
        interp.load("10 END")
        assert 1 not in interp._files, "File should be closed after loading new program"
    finally:
        os.unlink(tmp_path)


def test_line_to_idx_performance():
    """Bug #7: sorted_lines.index() was O(n); replaced with O(1) dict lookup."""
    interp = Interpreter(stdout=io.StringIO())
    # Build a program with many lines to test performance
    lines = []
    for i in range(1, 1000):
        lines.append(f"{i * 10} LET X = {i}")
    lines.append("10000 GOTO 10")
    source = "\n".join(lines)
    interp.load(source)
    # Verify _line_to_idx is populated
    assert len(interp._line_to_idx) == 1000, f"Expected 1000 entries, got {len(interp._line_to_idx)}"
    # Verify GOTO works
    interp.max_iterations = 100  # Limit to avoid long run
    try:
        interp.run()
    except BasicRuntimeError:
        pass  # Expected: max iterations exceeded


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"PASS: {test.__name__}")
        except AssertionError as e:
            print(f"FAIL: {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {test.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    print(f"\n{len(tests) - failed} passed, {failed} failed")
    sys.exit(1 if failed else 0)