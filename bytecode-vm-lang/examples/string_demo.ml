// string_demo.ml — showcase string manipulation builtins
fn greet(name: string) -> string {
    return "Hello, " + name + "!";
}

fn capitalize(s: string) -> string {
    // Capitalize the first letter: upper(first char) + lower(rest)
    if len(s) == 0 { return ""; }
    return upper(charAt(s, 0)) + lower(slice(s, 1, len(s)));
}

let names = split("alice,bob,charlie", ",");
for i in 0..len(names) {
    print(capitalize(names[i]));
}

// Check if a string contains a substring
if contains("The quick brown fox", "brown") {
    print("Found 'brown' in the string");
}

// String slicing
let sentence = "Hello, World!";
print(slice(sentence, 0, 5));   // "Hello"
print(slice(sentence, 7, 12));  // "World"
print(slice(sentence, 7, len(sentence)));  // "World!"

print(greet(upper("world")));