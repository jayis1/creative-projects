// elif_demo.ml — demonstrate elif chains
fn classify(n: int) -> string {
    if n < 0 {
        return "negative";
    } elif n == 0 {
        return "zero";
    } elif n < 10 {
        return "small";
    } elif n < 100 {
        return "medium";
    } elif n < 1000 {
        return "large";
    } else {
        return "huge";
    }
}

print(classify(-5));    // negative
print(classify(0));     // zero
print(classify(7));     // small
print(classify(42));    // medium
print(classify(500));  // large
print(classify(9999)); // huge

// elif with typeof
fn describe(x: int) -> string {
    if x % 15 == 0 {
        return "FizzBuzz";
    } elif x % 3 == 0 {
        return "Fizz";
    } elif x % 5 == 0 {
        return "Buzz";
    } else {
        return str(x);
    }
}

for i in 1..16 {
    print(describe(i));
}