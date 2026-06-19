# MiniLang Language Reference

This document describes the full MiniLang language syntax, types, and
semantics.

## Lexical Structure

### Comments

```minilang
// Line comment

/* Block comment
   spanning multiple lines */
```

### Keywords

`let`, `const`, `fn`, `if`, `elif`, `else`, `while`, `for`, `in`,
`return`, `break`, `continue`, `true`, `false`, `nil`, `and`, `or`

### Operators

| Category    | Operators                                    |
|-------------|----------------------------------------------|
| Arithmetic  | `+  -  *  /  %`                              |
| Comparison  | `<  <=  >  >=  ==  !=`                       |
| Logical     | `&&  \|\|  !` (or `and`, `or` keywords)     |
| Assignment  | `=`                                          |
| Unary       | `-` (negation), `!` (logical not)            |
| Other       | `->` (function return type), `..` (range)    |

### Literals

- **Integers**: `42`, `0`, `123`
- **Strings**: `"hello"`, `"with\nescape"`
- **Booleans**: `true`, `false`
- **Nil**: `nil` (represents the unit/empty value)
- **Arrays**: `[1, 2, 3]`, `[]`

### Escape Sequences in Strings

| Sequence | Meaning          |
|----------|------------------|
| `\n`     | Newline          |
| `\t`     | Tab              |
| `\r`     | Carriage return  |
| `\\`     | Backslash        |
| `\"`     | Double quote     |
| `\0`     | Null character   |

## Types

| Type           | Description                              |
|----------------|------------------------------------------|
| `int`          | 64-bit signed integer                    |
| `string`       | UTF-8 string                             |
| `bool`         | Boolean (`true` / `false`)              |
| `unit`         | The empty type (like `void` in C)        |
| `array<T>`     | Array of elements of type T              |
| `fn(P...) -> R`| Function type (params → return type)    |

## Variable Declarations

```minilang
// Mutable variable
let x: int = 42;
let y = 10;           // type inferred

// Immutable constant
const PI = 31415;     // type inferred as int
const name: string = "MiniLang";
```

## Functions

```minilang
fn add(a: int, b: int) -> int {
    return a + b;
}

fn greet(name: string) -> string {
    return "Hello, " + name + "!";
}

// Recursive function
fn factorial(n: int) -> int {
    if n <= 1 { return 1; }
    return n * factorial(n - 1);
}
```

## Control Flow

### If / Elif / Else

```minilang
if x < 0 {
    print("negative");
} elif x == 0 {
    print("zero");
} elif x < 10 {
    print("small");
} else {
    print("large");
}
```

### While Loop

```minilang
let i = 0;
while i < 10 {
    print(i);
    i = i + 1;
}
```

### For Loop (Range-based)

```minilang
for i in 0..10 {
    print(i);
}
// Range is exclusive on the end: 0..10 → 0,1,...,9
```

### Break and Continue

```minilang
for i in 0..100 {
    if i == 5 { break; }
    if i % 2 == 0 { continue; }
    print(i);
}
```

## Expressions

### Arithmetic

```minilang
let a = 1 + 2 * 3;      // 7 (operator precedence)
let b = (1 + 2) * 3;    // 9
let c = 10 / 3;         // 3 (integer division, truncates toward zero)
let d = -7 / 2;         // -3 (not -4)
let e = 10 % 3;         // 1
```

### Comparison

```minilang
let a = 5 < 10;         // true
let b = 5 > 10;         // false
let c = 5 == 5;         // true
let d = 5 != 5;         // false
let e = "abc" < "abd";  // true (lexicographic string comparison)
```

### Logical (with short-circuit evaluation)

```minilang
let a = true && false;   // false
let b = true || false;    // true
let c = !true;             // false

// && short-circuits: right side not evaluated if left is false
let d = false && (1 / 0 == 0);  // false (no division by zero)
```

### String Concatenation

```minilang
let greeting = "Hello" + ", " + "World" + "!";
```

### Array Operations

```minilang
let arr = [1, 2, 3];
let x = arr[0];         // Indexing (0-based)
arr[0] = 42;            // Index assignment
push(arr, 4);           // Append element
let n = len(arr);       // Length
```

## Built-in Functions

### General

| Function          | Signature                          | Description                        |
|-------------------|------------------------------------|------------------------------------|
| `print(x)`        | `T -> unit`                       | Print value to stdout              |
| `len(x)`          | `array<T> / string -> int`        | Length of array or string          |
| `str(x)`          | `T -> string`                     | Convert to string                  |
| `int(x)`          | `int/string/bool -> int`           | Convert to int                     |
| `typeof(x)`       | `T -> string`                     | Get type name as string             |
| `assert(c, msg?)` | `bool, string? -> unit`           | Assert condition (with optional msg)|

### Math

| Function       | Signature             | Description                    |
|----------------|-----------------------|--------------------------------|
| `abs(x)`       | `int -> int`         | Absolute value                 |
| `max(a, b)`    | `int, int -> int`    | Maximum of two ints            |
| `min(a, b)`    | `int, int -> int`    | Minimum of two ints            |
| `randint(a,b)` | `int, int -> int`    | Random int in [a, b]           |
| `time()`       | `-> int`             | Unix timestamp                 |

### String

| Function              | Signature                          | Description                     |
|-----------------------|------------------------------------|---------------------------------|
| `upper(s)`            | `string -> string`                | Uppercase                       |
| `lower(s)`            | `string -> string`                | Lowercase                       |
| `contains(s, sub)`    | `string, string -> bool`          | Check if s contains sub          |
| `slice(s, start, end)`| `string, int, int -> string`      | Substring [start, end)           |
| `charAt(s, i)`        | `string, int -> string`           | Character at index              |
| `split(s, sep)`       | `string, string -> array<string>` | Split string by separator       |

### Array

| Function            | Signature                         | Description                      |
|---------------------|-----------------------------------|----------------------------------|
| `push(arr, x)`      | `array<T>, T -> unit`            | Append to array                  |
| `pop(arr)`          | `array<T> -> T`                  | Remove and return last element   |
| `reverse(arr)`      | `array<T> -> array<T>`           | Reversed copy                    |
| `concat(a, b)`      | `array<T>, array<T> -> array<T>` | Concatenate two arrays            |
| `find(arr, x)`      | `array<T>, T -> int`             | Find index of x (-1 if not found)|
| `sort(arr)`         | `array<T> -> array<T>`           | Sorted copy                      |
| `sum(arr)`          | `array<int> -> int`              | Sum of int array                 |