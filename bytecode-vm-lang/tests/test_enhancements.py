import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from minilang.compiler import compile_program
from minilang.vm import VM

def run_code(code):
    program = compile_program(code)
    vm = VM(program)
    vm.run()
    return vm.output

# Test string concatenation
assert run_code('let a = "Hello, "; let b = "World!"; print(a + b);') == ["Hello, World!"]
print("Test: string concatenation passed")

# Test string comparison
assert run_code('print("apple" < "banana");') == ["true"]
assert run_code('print("zebra" > "apple");') == ["true"]
print("Test: string comparison passed")

# Test abs
assert run_code('print(abs(-42));') == ["42"]
assert run_code('print(abs(42));') == ["42"]
print("Test: abs() passed")

# Test max/min
assert run_code('print(max(10, 20));') == ["20"]
assert run_code('print(min(10, 20));') == ["10"]
assert run_code('print(max(-5, -10));') == ["-5"]
print("Test: max/min() passed")

# Test assert
assert run_code('assert(true); print(1);') == ["1"]
print("Test: assert(true) passed")

# Test assert with message
try:
    run_code('assert(false, "must be true");')
    assert False, "should have raised"
except Exception as e:
    assert "must be true" in str(e)
    print("Test: assert(false, msg) raised correctly passed")

# Test int() conversion
assert run_code('print(int("42"));') == ["42"]
assert run_code('print(int(true));') == ["1"]
print("Test: int() conversion passed")

# Test nested function calls with new builtins
assert run_code('print(abs(max(-10, -20)));') == ["10"]
print("Test: nested builtins passed")

# Test for loop with break/continue in complex pattern
result = run_code('''
let s = 0;
for i in 0..20 {
    if i % 2 == 0 { continue; }
    if i > 15 { break; }
    s = s + i;
}
print(s);
''')
# Odd numbers 1,3,5,7,9,11,13,15 = 64
assert result == ["64"], f"got {result}"
print("Test: complex break/continue passed")

print("\n=== ALL ENHANCEMENT TESTS PASSED ===")