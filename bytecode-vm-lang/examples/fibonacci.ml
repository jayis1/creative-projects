// fibonacci.ml — compute the Nth Fibonacci number recursively
fn fib(n: int) -> int {
    if n < 2 {
        return n;
    }
    return fib(n - 1) + fib(n - 2);
}

print(fib(10));  // 55
print(fib(20));  // 6765