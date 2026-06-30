# Reed-Solomon Codec

A from-scratch implementation of Reed-Solomon error-correcting codes over **GF(2⁸)**, featuring systematic encoding, Berlekamp-Massey error locating, Chien search, and Forney magnitude computation — all built from the ground up with no external dependencies.

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

## How It Works

### 1. Galois Field Arithmetic (`gf.py`)

GF(2⁸) is a finite field with 256 elements. All arithmetic uses the irreducible polynomial 0x11D:
- **Addition/Subtraction:** XOR (same operation in characteristic-2 fields)
- **Multiplication:** Via precomputed log/exp tables — `mul(a,b) = exp[log[a] + log[b]]`
- **Division:** `div(a,b) = exp[(log[a] - log[b]) % 255]`
- **Inversion:** `inv(a) = exp[255 - log[a]]`

The log and exp (antilog) tables are precomputed at import time, making all field operations O(1).

### 2. Encoding (`rs_codec.py`)

Systematic encoding preserves the original message in the codeword and appends parity symbols:

```
codeword = [parity (nsym symbols)] + [message (k symbols)]
```

The encoder:
1. Computes the generator polynomial `g(x) = ∏(x - αⁱ)` for `i = 0..nsym-1`
2. Computes `parity = (message × x^nsym) mod g(x)` via polynomial division
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
Finds the error locator polynomial Λ(x) from the syndrome sequence. This is an iterative algorithm that finds the shortest LFSR capable of generating the syndrome sequence, which corresponds to the error locator polynomial.

**Step 3 — Chien Search:**  
Brute-force evaluation of Λ(x) at all field elements α⁻⁰, α⁻¹, ..., α⁻ⁿ. Each root of Λ identifies an error position.

**Step 4 — Forney Algorithm:**  
Computes error magnitudes using:
```
eⱼ = α^pos × Ω(α⁻ᵖᵒˢ) / Λ'(α⁻ᵖᵒˢ)
```
where Ω(x) = (S(x) × Λ(x)) mod x^nsym is the error evaluator polynomial, and Λ'(x) is the formal derivative of Λ.

### 4. Erasure Correction

Erasures (errors with known positions) are easier to correct than unknown errors. The decoder builds the erasure locator polynomial directly from the known positions, bypassing Berlekamp-Massey.

## Usage

### Python API

```python
from rs_codec import encode_message, decode_message

# Encode
data = b"Hello, World!"
encoded = encode_message(data, nsym=10)  # 10 parity bytes
print(f"Original: {len(data)} bytes, Encoded: {len(encoded)} bytes")

# Simulate corruption
corrupted = bytearray(encoded)
corrupted[5] ^= 0xFF
corrupted[10] ^= 0xAA
corrupted[20] ^= 0x42

# Decode and correct
recovered = decode_message(bytes(corrupted), nsym=10)
print(recovered)  # b"Hello, World!"
```

### Error + Erasure Correction

```python
from rs_codec import rs_decode

# Mark certain positions as erased (value unknown)
corrupted = list(encoded)
erasures = [3, 7, 15, 22]
for p in erasures:
    corrupted[p] = 0  # value doesn't matter, position is known
corrected = rs_decode(corrupted, nsym=10, erasures=erasures)
```

### Command-Line Interface

```bash
# Encode a file
python3 cli.py encode myfile.txt encoded.rs --nsym 16

# Decode and correct
python3 cli.py decode encoded.rs recovered.txt --nsym 16

# Run interactive demo
python3 cli.py demo

# Show code parameters
python3 cli.py info --nsym 10
```

## Files

| File | Description |
|------|-------------|
| `gf.py` | GF(2⁸) finite field arithmetic and polynomial operations |
| `rs_codec.py` | RS encoder, decoder, Berlekamp-Massey, Chien search, Forney |
| `cli.py` | Command-line interface (encode, decode, demo, info) |
| `test_run.py` | Basic functional tests |

## Examples

### Correcting Maximum Errors (5 errors with nsym=10)

```python
from rs_codec import rs_encode, rs_decode

msg = list(b"Hello World!")  # 12 bytes
encoded = rs_encode(list(msg), nsym=10)  # 22-byte codeword

# Corrupt 5 positions (the maximum for nsym=10)
corrupted = list(encoded)
for pos in [0, 4, 8, 12, 16]:
    corrupted[pos] ^= 99

decoded = rs_decode(corrupted, nsym=10)
assert decoded == encoded  # ✓ Perfectly recovered
```

### Erasure-Only Correction (10 erasures with nsym=10)

```python
encoded = rs_encode(list(msg), nsym=10)
corrupted = list(encoded)
erasures = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
for p in erasures:
    corrupted[p] = 0

decoded = rs_decode(corrupted, nsym=10, erasures=erasures)
assert decoded == encoded  # ✓ Perfectly recovered
```

## Algorithm References

- Reed, I. S.; Solomon, G. (1960). "Polynomial Codes Over Certain Finite Fields"
- Berlekamp, E. R. (1968). "Algebraic Coding Theory"
- Forney, G. D. (1965). "On Decoding BCH Codes"
- Lin, S.; Costello, D. (2004). "Error Control Coding", 2nd Edition