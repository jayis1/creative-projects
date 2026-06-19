// bubblesort.ml — sort an array using bubble sort
fn bubble_sort(arr: array<int>) -> unit {
    let n = len(arr);
    for i in 0..n {
        for j in 0..(n - i - 1) {
            if arr[j] > arr[j + 1] {
                let tmp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = tmp;
            }
        }
    }
}

let data = [64, 34, 25, 12, 22, 11, 90];
bubble_sort(data);
print(data[0]);  // 11
print(data[6]);  // 90