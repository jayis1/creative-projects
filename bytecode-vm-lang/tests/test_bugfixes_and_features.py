"""Comprehensive tests for MiniLang bug fixes and new features.

Covers:
- Bug fixes: nested loop break/continue, integer division truncation,
  call depth limit
- New builtins: string ops, array ops, typeof, time, randint
- New language features: elif keyword
- CLI: config file support, benchmark, explain
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from minilang.compiler import compile_program
from minilang.vm import VM
from minilang.errors import MiniLangError, VMError


def run_code(code: str, **vm_kwargs) -> list[str]:
    """Compile and run *code*, returning the VM's output list."""
    program = compile_program(code)
    vm = VM(program, **vm_kwargs)
    vm.run()
    return vm.output


# --------------------------------------------------------------------------- #
# Bug fix tests                                                                #
# --------------------------------------------------------------------------- #
class TestNestedLoopBreakContinue:
    """Bug 1: Nested loop break/continue targets were lost when an inner loop
    reset the flat break/continue target lists."""

    def test_nested_for_break(self):
        # Inner break should only break the inner loop, not the outer.
        code = """
let result = 0;
for i in 0..3 {
    for j in 0..3 {
        if j == 2 { break; }
        result = result + 1;
    }
}
print(result);
"""
        assert run_code(code) == ["6"]  # 3 * 2

    def test_nested_for_continue(self):
        code = """
let result = 0;
for i in 0..3 {
    for j in 0..5 {
        if j == 2 { continue; }
        result = result + 1;
    }
}
print(result);
"""
        assert run_code(code) == ["12"]  # 3 * 4

    def test_nested_while_break(self):
        code = """
let result = 0;
let i = 0;
while i < 3 {
    let j = 0;
    while j < 3 {
        if j == 1 { break; }
        result = result + 1;
        j = j + 1;
    }
    i = i + 1;
}
print(result);
"""
        assert run_code(code) == ["3"]  # 3 * 1

    def test_outer_break_from_inner(self):
        # Breaking from the outer loop after the inner loop completes.
        code = """
let result = 0;
for i in 0..10 {
    for j in 0..3 {
        result = result + 1;
    }
    if i == 2 { break; }
}
print(result);
"""
        assert run_code(code) == ["9"]  # 3 * 3

    def test_triple_nested_break(self):
        code = """
let result = 0;
for i in 0..3 {
    for j in 0..3 {
        for k in 0..3 {
            if k == 1 { break; }
            result = result + 1;
        }
    }
}
print(result);
"""
        assert run_code(code) == ["9"]  # 3 * 3 * 1

    def test_continue_with_break_nested(self):
        code = """
let result = 0;
for i in 0..5 {
    if i == 3 { break; }
    for j in 0..3 {
        if j == 1 { continue; }
        result = result + 1;
    }
}
print(result);
"""
        assert run_code(code) == ["6"]  # 3 * 2


class TestIntegerDivisionTruncation:
    """Bug 2: Python's // floors toward -inf, but MiniLang truncates toward zero."""

    def test_positive_division(self):
        assert run_code("print(7 / 2);") == ["3"]
        assert run_code("print(20 / 4);") == ["5"]

    def test_negative_division(self):
        # -7 / 2 should be -3 (truncate toward zero), not -4 (floor)
        assert run_code("print(-7 / 2);") == ["-3"]
        assert run_code("print(7 / -2);") == ["-3"]
        assert run_code("print(-7 / -2);") == ["3"]

    def test_positive_modulo(self):
        assert run_code("print(17 % 5);") == ["2"]

    def test_negative_modulo(self):
        # -7 % 2 should be -1 (sign of dividend), not 1 (Python's behavior)
        assert run_code("print(-7 % 2);") == ["-1"]
        assert run_code("print(7 % -2);") == ["1"]

    def test_division_identity(self):
        # a == (a / b) * b + (a % b) should hold
        code = """
let a = -17;
let b = 5;
let q = a / b;
let r = a % b;
print(q);
print(r);
print(q * b + r);
"""
        result = run_code(code)
        assert result == ["-3", "-2", "-17"]


class TestCallDepthLimit:
    """Bug 3: Deep recursion caused Python stack overflow before step limit."""

    def test_infinite_recursion_raises(self):
        with pytest.raises(VMError, match="call depth"):
            run_code("fn inf() -> int { return inf(); } inf();")

    def test_deep_recursion_raises(self):
        with pytest.raises(VMError, match="call depth"):
            run_code("fn f(n: int) -> int { return f(n - 1); } f(10000);")

    def test_shallow_recursion_ok(self):
        assert run_code(
            "fn fact(n: int) -> int { if n <= 1 { return 1; } return n * fact(n - 1); } print(fact(10));"
        ) == ["3628800"]

    def test_custom_call_depth(self):
        # With a very small call depth, even shallow recursion should fail.
        with pytest.raises(VMError, match="call depth"):
            program = compile_program(
                "fn f(n: int) -> int { if n <= 1 { return 1; } return f(n - 1); } print(f(5));"
            )
            vm = VM(program, max_call_depth=3)
            vm.run()


# --------------------------------------------------------------------------- #
# New builtin tests                                                            #
# --------------------------------------------------------------------------- #
class TestStringBuiltins:
    def test_upper(self):
        assert run_code('print(upper("hello"));') == ["HELLO"]

    def test_lower(self):
        assert run_code('print(lower("WORLD"));') == ["world"]

    def test_contains_true(self):
        assert run_code('print(contains("hello world", "world"));') == ["true"]

    def test_contains_false(self):
        assert run_code('print(contains("hello world", "xyz"));') == ["false"]

    def test_slice(self):
        assert run_code('print(slice("hello world", 0, 5));') == ["hello"]
        assert run_code('print(slice("hello world", 6, 11));') == ["world"]

    def test_slice_out_of_bounds(self):
        assert run_code('print(slice("hello", 0, 100));') == ["hello"]

    def test_slice_negative_range(self):
        assert run_code('print(slice("hello", 3, 1));') == [""]

    def test_charAt(self):
        assert run_code('print(charAt("hello", 0));') == ["h"]
        assert run_code('print(charAt("hello", 4));') == ["o"]

    def test_charAt_out_of_bounds(self):
        with pytest.raises(MiniLangError):
            run_code('print(charAt("hello", 10));')

    def test_split(self):
        result = run_code('let parts = split("a,b,c", ","); print(len(parts));')
        assert result == ["3"]

    def test_split_no_separator(self):
        result = run_code('let parts = split("hello", ","); print(len(parts));')
        assert result == ["1"]


class TestArrayBuiltins:
    def test_pop(self):
        result = run_code("let a = [1, 2, 3]; print(pop(a)); print(len(a));")
        assert result == ["3", "2"]

    def test_pop_empty(self):
        with pytest.raises(MiniLangError):
            run_code("let a = []; print(pop(a));")

    def test_reverse(self):
        result = run_code("let a = [1, 2, 3]; let r = reverse(a); print(r[0]); print(r[2]);")
        assert result == ["3", "1"]

    def test_concat(self):
        result = run_code("let a = [1, 2]; let b = [3, 4]; let c = concat(a, b); print(len(c)); print(c[2]);")
        assert result == ["4", "3"]

    def test_find_found(self):
        assert run_code("let a = [10, 20, 30]; print(find(a, 20));") == ["1"]

    def test_find_not_found(self):
        assert run_code("let a = [10, 20, 30]; print(find(a, 99));") == ["-1"]

    def test_sort(self):
        result = run_code("let a = [3, 1, 2]; let s = sort(a); print(s[0]); print(s[1]); print(s[2]);")
        assert result == ["1", "2", "3"]

    def test_sort_does_not_mutate(self):
        result = run_code("let a = [3, 1, 2]; let s = sort(a); print(a[0]);")
        assert result == ["3"]  # original still [3, 1, 2]

    def test_sum(self):
        assert run_code("let a = [1, 2, 3, 4, 5]; print(sum(a));") == ["15"]

    def test_sum_empty(self):
        assert run_code("let a = []; print(sum(a));") == ["0"]


class TestTypeofBuiltin:
    def test_typeof_int(self):
        assert run_code("print(typeof(42));") == ["int"]

    def test_typeof_string(self):
        assert run_code('print(typeof("hi"));') == ["string"]

    def test_typeof_bool(self):
        assert run_code("print(typeof(true));") == ["bool"]

    def test_typeof_array(self):
        assert run_code("print(typeof([1, 2]));") == ["array"]

    def test_typeof_nil(self):
        assert run_code("print(typeof(nil));") == ["unit"]


class TestUtilityBuiltins:
    def test_time_returns_int(self):
        result = run_code("let t = time(); print(t >= 0);")
        assert result == ["true"]

    def test_randint_in_range(self):
        code = """
let r = randint(1, 10);
assert(r >= 1 && r <= 10, "randint out of range");
print(1);
"""
        assert run_code(code) == ["1"]


# --------------------------------------------------------------------------- #
# New language feature tests                                                   #
# --------------------------------------------------------------------------- #
class TestElifKeyword:
    def test_elif_basic(self):
        code = """
let x = 5;
if x < 3 { print(1); }
elif x < 7 { print(2); }
elif x < 10 { print(3); }
else { print(4); }
"""
        assert run_code(code) == ["2"]

    def test_elif_no_else(self):
        code = """
let x = 100;
if x < 3 { print(1); }
elif x < 7 { print(2); }
"""
        assert run_code(code) == []

    def test_elif_first_branch(self):
        code = """
let x = 1;
if x < 3 { print(1); }
elif x < 7 { print(2); }
else { print(3); }
"""
        assert run_code(code) == ["1"]

    def test_elif_else_branch(self):
        code = """
let x = 99;
if x < 3 { print(1); }
elif x < 7 { print(2); }
else { print(3); }
"""
        assert run_code(code) == ["3"]

    def test_elif_nested(self):
        code = """
let x = 5;
let y = 10;
if x > 3 {
    if y > 15 { print(1); }
    elif y > 5 { print(2); }
    else { print(3); }
} else {
    print(4);
}
"""
        assert run_code(code) == ["2"]

    def test_elif_fizzbuzz(self):
        code = """
for i in 1..16 {
    if i % 15 == 0 { print(15); }
    elif i % 3 == 0 { print(3); }
    elif i % 5 == 0 { print(5); }
    else { print(i); }
}
"""
        result = run_code(code)
        # i=1..15 (range is exclusive on end, so 1..16 = 1..15)
        # 1: 1, 2: 2, 3: Fizz(3), 4: 4, 5: Buzz(5), 6: Fizz(3), 7: 7, 8: 8,
        # 9: Fizz(3), 10: Buzz(5), 11: 11, 12: Fizz(3), 13: 13, 14: 14, 15: FizzBuzz(15)
        assert result == ["1", "2", "3", "4", "5", "3", "7", "8", "3", "5",
                          "11", "3", "13", "14", "15"]


# --------------------------------------------------------------------------- #
# CLI tests                                                                    #
# --------------------------------------------------------------------------- #
class TestCLI:
    def test_run_subcommand(self):
        from minilang.cli import main
        rc = main(["run", "examples/fibonacci.ml"])
        assert rc == 0

    def test_check_subcommand(self):
        from minilang.cli import main
        rc = main(["check", "examples/fibonacci.ml"])
        assert rc == 0

    def test_dis_subcommand(self):
        from minilang.cli import main
        rc = main(["dis", "examples/fibonacci.ml"])
        assert rc == 0

    def test_benchmark_subcommand(self):
        from minilang.cli import main
        rc = main(["benchmark", "examples/fibonacci.ml", "-n", "3"])
        assert rc == 0

    def test_config_file(self):
        from minilang.cli import main
        rc = main(["run", "examples/fibonacci.ml", "--config",
                   "examples/minilang.json"])
        assert rc == 0

    def test_no_opt_flag(self):
        from minilang.cli import main
        rc = main(["run", "examples/fibonacci.ml", "--no-opt"])
        assert rc == 0


# --------------------------------------------------------------------------- #
# Integration / end-to-end tests                                               #
# --------------------------------------------------------------------------- #
class TestEndToEnd:
    def test_quicksort(self):
        code = """
fn quicksort(arr: array<int>) -> array<int> {
    if len(arr) <= 1 { return arr; }
    let pivot = arr[0];
    let less = [];
    let greater = [];
    for i in 1..len(arr) {
        if arr[i] < pivot {
            push(less, arr[i]);
        } else {
            push(greater, arr[i]);
        }
    }
    return concat(quicksort(less), concat([pivot], quicksort(greater)));
}
let data = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3];
let sorted = quicksort(data);
print(sorted[0]);
print(sorted[9]);
"""
        result = run_code(code)
        assert result == ["1", "9"]

    def test_string_processing(self):
        code = """
fn capitalize(s: string) -> string {
    if len(s) == 0 { return ""; }
    return upper(charAt(s, 0)) + lower(slice(s, 1, len(s)));
}
print(capitalize("HELLO"));
print(capitalize("world"));
"""
        assert run_code(code) == ["Hello", "World"]

    def test_mixed_types_and_builtins(self):
        code = """
let nums = [5, 3, 8, 1, 9, 2, 7];
let s = sum(nums);
let avg = s / len(nums);
let mx = sort(nums);
print("sum: " + str(s));
print("max: " + str(mx[len(mx) - 1]));
print("contains 8: " + str(contains("hello world", "o w")));
"""
        result = run_code(code)
        assert "sum: 35" in result
        assert "max: 9" in result

    def test_nested_function_with_builtins(self):
        code = """
fn is_palindrome(s: string) -> bool {
    let n = len(s);
    for i in 0..(n / 2) {
        if charAt(s, i) != charAt(s, n - 1 - i) {
            return false;
        }
    }
    return true;
}
print(is_palindrome("racecar"));
print(is_palindrome("hello"));
"""
        assert run_code(code) == ["true", "false"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])