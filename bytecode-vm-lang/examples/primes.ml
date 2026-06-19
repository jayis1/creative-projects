// primes.ml — sieve of Eratosthenes
fn sieve(n: int) -> array<int> {
    let is_prime = [];
    for i in 0..n {
        push(is_prime, 1);
    }

    for i in 2..n {
        if is_prime[i] == 1 {
            let j = i * i;
            while j < n {
                is_prime[j] = 0;
                j = j + i;
            }
        }
    }

    let primes = [];
    for i in 2..n {
        if is_prime[i] == 1 {
            push(primes, i);
        }
    }
    return primes;
}

let result = sieve(30);
let count = len(result);
print(count);  // 10 (primes below 30: 2,3,5,7,11,13,17,19,23,29)
print(result[0]);  // 2
print(result[9]);  // 29