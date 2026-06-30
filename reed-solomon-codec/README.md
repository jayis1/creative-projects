# Reed-Solomon Codec

A from-scratch implementation of Reed-Solomon error-correcting codes over **GF(2⁸)**, featuring systematic encoding, Berlekamp-Massey error locating, Chien search, Forney magnitude computation, interleaving for burst-error resilience, and a class-based API with decoder statistics — all built from the ground up with no external dependencies.

## Overview

Reed-Solomon (RS) codes are block-based error-correcting codes widely used in CDs, DVDs, QR codes, data transmission, and deep-space communication. They are **maximum distance separable (MDS)** codes, meaning they achieve the best possible error correction for a given amount of redundancy.

This implementation works over the Galois field GF(2⁸) using:
- **Primitive polynomial:** `x⁸ + x⁴ + x³ + x² + 1` (0x11D)
- **Primitive element (generator):** α = 2
- **Symbol size:** 8 bits (one byte)

### Correction Capabilities

| Parameter | Formula | With nsym=10 |
|-----------|---------|-------------|
| Correctable errors | `⌊nsym/2⌋` | 5 |
| Correctable erasures | `nsym` | 10 |
| Combined (errors + erasures) | `2·e + s ≤ nsym` | varies |
| Burst errors (interleaved, depth d) | `d · ⌊nsym/2⌋` | d×5 |

## How It Works

### 1. Galois Field Arithmetic (`gf.py`)

GF(2⁸) is a finite field with 256 elements. All arithmetic uses the irreducible polynomial 0x11D:
- **Addition/Subtraction:** XOR (same operation in characteristic-2 fields)
- **Multiplication:** Via precomputed log/exp tables — `mul(a,b) = exp[log[a] + log[b]]`
- **Division:** `div(a,b) = exp[(log[a] - log[b]) % 255]`
- **Inversion:** `inv(a) = exp[255 - log[a]]`

The log and exp (antilog) tables are precomputed at import time, making all field operations O(1). Polynomial operations (add, mul, div, eval, scale) use the **lowest-degree-first** convention: `poly[0]` is the constant term.

### 2. Encoding (`rs_codec.py`)

Systematic encoding preserves the original message in the codeword and prepends parity symbols:

```
codeword = [parity (nsym symbols)] + [message (k symbols)]
```

The encoder:
1. Computes the generator polynomial `g(x) = ∏(x - αⁱ)` for `i = 0..nsym-1` (cached for performance)
2. Computes `parity = (message × x^nsym) mod g(x)` via polynomial long division
3. Returns `parity + message` as the codeword

A valid codeword has all-zero syndromes because it's a multiple of g(x), which has roots at α⁰, α¹, ..., α^(nsym-1).

### 3. Decoding Pipeline

The decoder follows the classical RS decoding pipeline:

```
Received → Syndromes → Berlekamp-Massey → Chien Search → Forney → Corrected
```

**Step 1 — Syndrome Calculation:**  
Compute `Sᵢ = R(αⁱ)` for `i = 0..nsym-1`. If all syndromes are zero, no errors are present.

**Step 2 — Berlekamp-Massey Algorithm:**  
Finds the error locator polynomial Λ(x) from the syndrome sequence. This iterative algorithm finds the shortest LFSR capable of generating the syndrome sequence, which corresponds to the error locator polynomial.

**Step 3 — Chien Search:**  
Brute-force evaluation of Λ(x) at all field elements α⁻⁰, α⁻¹, ..., α⁻ⁿ. Each root of Λ identifies an error position.

**Step 4 — Forney Algorithm:**  
Computes error magnitudes using:
```
eⱼ = α^pos × Ω(α⁻ᵖᵒˢ) / Λ'(α⁻ᵖᵒˢ)
```
where Ω(x) = (S(x) × Λ(x)) mod x^nsym is the error evaluator polynomial, and Λ'(x) is the formal derivative of Λ (in characteristic 2, even-degree terms vanish).

### 4. Erasure Correction

Erasures (errors with known positions) are easier to correct than unknown errors. The decoder builds the erasure locator polynomial directly from the known positions, bypassing Berlekamp-Massey. Each erasure at position p contributes a factor `(x - α⁻ᵖ)` to Λ(x).

### 5. Interleaving for Burst Errors

Block interleaving spreads burst errors across multiple RS codewords. With interleaving depth `d`, a burst of length `d × ⌊nsym/2⌋` can be corrected — each codeword sees at most `⌊nsym/2⌋` errors from the burst.

## Usage

### Class-Based API (Recommended)

```python
from rs_codec import RSCode

rs = RSCode(nsym=10)
print(rs)  # Print code parameters

# Encode
msg = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
encoded = rs.encode(msg)

# Correct errors
corrupted = list(encoded)
corrupted[3] ^= 42
corrupted[7] ^= 99
corrected = rs.decode(corrupted)
assert corrected == encoded

# Get detailed statistics
result = rs.decode_detailed(corrupted)
print(f"Errors corrected: {result.errors_corrected}")
print(f"Error positions: {result.error_positions}")
```

### Byte-Oriented API

```python
from rs_codec import encode_message, decode_message

data = b"Hello, World!"
encoded = encode_message(data, nsym=10)

# Simulate corruption
corrupted = bytearray(encoded)
corrupted[5] ^= 0xFF
corrupted[10] ^= 0xAA
corrupted[20] ^= 0x42

recovered = decode_message(bytes(corrupted), nsym=10)
assert recovered == data
```

### Erasure Correction

```python
from rs_codec import rs_decode

corrupted = list(encoded)
erasures = [3, 7, 15, 22]  # known bad positions
for p in erasures:
    corrupted[p] = 0  # value doesn't matter, position is known
corrected = rs_decode(corrupted, nsym=10, erasures=erasures)
```

### Burst-Error Correction with Interleaving

```python
from rs_codec import encode_interleaved, decode_interleaved

data = b"Interleaving protects against burst errors!"
nsym, depth = 6, 5  # depth=5 means bursts of up to 15 symbols are correctable
encoded = encode_interleaved(data, nsym, depth)

# Inject a burst of 10 corrupted bytes (would fail without interleaving)
corrupted = bytearray(encoded)
for i in range(10):
    corrupted[5 + i] ^= 0xFF

recovered = decode_interleaved(bytes(corrupted), nsym, depth, original_len=len(data))
assert recovered == data
```

### Command-Line Interface

```bash
# Encode a file
python3 cli.py encode myfile.txt encoded.rs --nsym 16

# Decode and correct
python3 cli.py decode encoded.rs recovered.txt --nsym 16

# Run interactive demo
python3 cli.py demo

# Demonstrate burst-error correction via interleaving
python3 cli.py burst-demo --nsym 6 --depth 4

# Show code parameters
python3 cli.py info --nsym 16
```

## Files

| File | Description |
|------|-------------|
| `gf.py` | GF(2⁸) finite field arithmetic and polynomial operations |
| `rs_codec.py` | RS encoder, decoder, Berlekamp-Massey, Chien search, Forney, interleaving, RSCode class |
| `cli.py` | Command-line interface (encode, decode, demo, burst-demo, info) |
| `tests/test_rs_codec.py` | Comprehensive pytest test suite (78 tests) |

## API Reference

### Core Functions

| Function | Description |
|----------|-------------|
| `rs_encode(message, nsym)` | Systematic RS encoding (list-based) |
| `rs_decode(received, nsym, erasures=None)` | RS decoding with error/erasure correction |
| `rs_decode_detailed(received, nsym, erasures=None)` | Decode with `DecodeResult` statistics |
| `generator_poly(nsym)` | Get the generator polynomial (cached) |
| `calc_syndromes(poly, nsym)` | Calculate syndrome values |
| `berlekamp_massey(syndromes)` | Find error locator polynomial Λ(x) |
| `chien_search(sigma, n)` | Find error positions |
| `forney(syndromes, err_positions, sigma)` | Compute error magnitudes |

### Convenience API

| Function | Description |
|----------|-------------|
| `encode(data, nsym)` | Encode bytes → bytes |
| `decode(data, nsym, erasures=None)` | Decode bytes → bytes |
| `encode_message(data, nsym)` | Encode data bytes → codeword bytes |
| `decode_message(data, nsym, erasures=None)` | Decode codeword bytes → data bytes (parity stripped) |

### Interleaving

| Function | Description |
|----------|-------------|
| `interleave(data, rows)` | Block-interleave symbols |
| `deinterleave(data, rows)` | Reverse block-interleaving |
| `encode_interleaved(data, nsym, depth)` | Encode with interleaving for burst-error resilience |
| `decode_interleaved(data, nsym, depth, original_len=None)` | Decode interleaved data |

### RSCode Class

| Method | Description |
|--------|-------------|
| `RSCode(nsym)` | Create RS code instance |
| `.encode(message)` | Encode message (list) |
| `.decode(received, erasures=None)` | Decode and correct (list) |
| `.decode_detailed(received, erasures=None)` | Decode with statistics |
| `.encode_bytes(data)` | Encode bytes |
| `.decode_bytes(data, erasures=None)` | Decode bytes |
| `.encode_data(data)` | Encode data → full codeword |
| `.decode_data(data, erasures=None)` | Decode → data only (parity stripped) |
| `.max_errors` | Max correctable errors (nsym // 2) |
| `.max_erasures` | Max correctable erasures (nsym) |
| `.max_message_length` | Max message length (255 - nsym) |

## Examples

### Correcting Maximum Errors (5 errors with nsym=10)

```python
from rs_codec import rs_encode, rs_decode

msg = list(b"Hello World!")
encoded = rs_encode(msg, nsym=10)

corrupted = list(encoded)
for pos in [0, 4, 8, 12, 16]:
    corrupted[pos] ^= 99

decoded = rs_decode(corrupted, nsym=10)
assert decoded == encoded  # ✓ Perfectly recovered
```

### Erasure-Only Correction (10 erasures with nsym=10)

```python
encoded = rs_encode(msg, nsym=10)
corrupted = list(encoded)
erasures = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
for p in erasures:
    corrupted[p] = 0

decoded = rs_decode(corrupted, nsym=10, erasures=erasures)
assert decoded == encoded  # ✓ Perfectly recovered
```

## Testing

```bash
# Run the full test suite
python3 -m pytest tests/test_rs_codec.py -v

# Run specific test class
python3 -m pytest tests/test_rs_codec.py::TestErrorCorrection -v
```

The test suite covers:
- GF(2⁸) arithmetic properties (17 tests)
- Polynomial operations (10 tests)
- Generator polynomial properties (3 tests)
- Encoding correctness (8 tests)
- Error correction including randomized tests (6 tests)
- Erasure correction including randomized tests (5 tests)
- RSCode class API (8 tests)
- Interleaving and burst-error correction (5 tests)
- Byte API (3 tests)
- Edge cases and boundary conditions (9 tests)
- Stress tests with 150+ random round-trips (2 tests)

## Known Issues (Resolved)

The following bugs were found during systematic code review and fixed:

1. **`gf_poly_mul` crash on empty inputs** — Calling `gf_poly_mul([], [1])` returned `[]` (empty list) instead of `[0]`, because `len([]) + len([1]) - 1 = 0` and `[0] * 0 = []`. **Fix:** Added an early return `[0]` when either input is empty.

2. **`GF256.pow` accepts negative exponents** — Passing a negative exponent `e` to `GF256.pow()` silently produced incorrect results instead of raising an error. **Fix:** Added validation that raises `ValueError` for negative exponents and `TypeError` for non-integer exponents.

3. **`decode_interleaved` missing minimum data length validation** — When given data shorter than `nsym * depth` bytes, the function would compute a negative `msg_len` and produce incorrect output instead of raising a clear error. **Fix:** Added explicit length validation with a descriptive error message.

4. **`encode_interleaved` missing block size validation** — When `block_size + nsym > 255`, the underlying `rs_encode` would raise, but with a confusing error message that didn't mention the interleaving context. **Fix:** Added explicit validation with a clear error message explaining the interleaving constraint.

5. **CLI `decode` command replaces all `.rs` occurrences in path** — The `cmd_decode` function used `args.input.replace(".rs", "")` which replaces ALL occurrences of ".rs" in the path, not just the file extension. For example, `path/to.rs/file.rs` would become `path/to/file` (losing a directory name). **Fix:** Changed to check `args.input.endswith(".rs")` and strip only the trailing extension.

6. **`gf_poly_div` incorrect remainder extraction** — The original polynomial division algorithm used an incorrect separator index (`-(len(rev_divisor) - 1)`) for extracting the remainder, which caused wrong results for degree-0 divisors (like `[1]`) and self-division. **Fix:** Rewrote the division algorithm to properly track the quotient length and extract the remainder from the correct position, with a precomputed divisor leading coefficient inverse for efficiency.

7. **`deinterleave` function was identical to `interleave`** — The `deinterleave` function used the same formula as `interleave` (mapping `data[i]` to `result[r*cols + c]`), making it NOT the inverse of interleaving. **Fix:** Changed `deinterleave` to use the inverse mapping: `result[i] = data[(i%rows)*cols + (i//rows)]`.

## Algorithm References

- Reed, I. S.; Solomon, G. (1960). "Polynomial Codes Over Certain Finite Fields"
- Berlekamp, E. R. (1968). "Algebraic Coding Theory"
- Forney, G. D. (1965). "On Decoding BCH Codes"
- Lin, S.; Costello, D. (2004). "Error Control Coding", 2nd Edition