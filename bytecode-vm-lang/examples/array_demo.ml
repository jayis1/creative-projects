// array_demo.ml — showcase array manipulation builtins
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

let data = [3, 6, 1, 8, 2, 9, 4, 7, 5];
print("Original:");
for i in 0..len(data) { print(data[i]); }

let sorted = quicksort(data);
print("Sorted:");
for i in 0..len(sorted) { print(sorted[i]); }

// Use sort() builtin for comparison
let builtin_sorted = sort(data);
print("Builtin sort:");
for i in 0..len(builtin_sorted) { print(builtin_sorted[i]); }

// Array operations
let nums = [10, 20, 30, 40, 50];
print("Sum: " + str(sum(nums)));
print("Reversed:");
let rev = reverse(nums);
for i in 0..len(rev) { print(rev[i]); }

// Find an element
let idx = find(nums, 30);
print("Found 30 at index: " + str(idx));

// Pop the last element
let popped = pop(nums);
print("Popped: " + str(popped));
print("Remaining length: " + str(len(nums)));