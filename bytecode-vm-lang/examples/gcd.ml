// gcd.ml — greatest common divisor using Euclid's algorithm
fn gcd(a: int, b: int) -> int {
    while b != 0 {
        let t = b;
        b = a % b;
        a = t;
    }
    return a;
}

print(gcd(48, 18));   // 6
print(gcd(1071, 462)); // 21