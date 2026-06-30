# Reed-Solomon Codec

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)
![Tests: 126](https://img.shields.io/badge/tests-126%20passing-brightgreen.svg)
![Version: 2.0.0](https://img.shields.io/badge/version-2.0.0-orange.svg)
![Pure Python](https://img.shields.io/badge/pure%20Python-stdlib%20only-yellow.svg)

A from-scratch implementation of **Reed-Solomon error-correcting codes** over **GF(2⁸)**, featuring systematic encoding, Berlekamp-Massey error locating, Chien search, Forney magnitude computation, interleaving for burst-error resilience, erasure correction, a configuration system (JSON/YAML/TOML), structured logging, a 9-subcommand CLI, and a comprehensive test suite — all built from the ground up with no external dependencies.

---

## Table of Contents

- [Overview](#overview)
- [Correction Capabilities](#correction-capabilities)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [Class-Based API](#class-based-api-recommended)
  - [Byte-Oriented API](#byte-oriented-api)
  - [Erasure Correction](#erasure-correction)
  - [Burst-Error Correction with Interleaving](#burst-error-correction-with-interleaving)
  - [Command-Line Interface](#command-line-interface)
  - [Configuration Files](#configuration-files)
  - [Stream Mode (Pipelines)](#stream-mode-pipelines)
  - [Benchmarking](#benchmarking)
- [Architecture](#architecture)
- [Examples](#examples)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Known Issues (Resolved)](#known-issues-resolved)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Changelog](#changelog)
- [Algorithm References](#algorithm-references)
- [License](#license)

---

## Overview

Reed-Solomon (RS) codes are block-based error-correcting codes widely used in CDs, DVDs, QR codes, data transmission, and deep-space communication. They are **maximum distance separable (MDS)** codes, meaning they achieve the best possible error correction for a given amount of redundancy.

This implementation works over the Galois field GF(2⁸) using:
- **Primitive polynomial:** `x⁸ + x⁴ + x³ + x² + 1` (0x11D)
- **Primitive element (generator):** α = 2
- **Symbol size:** 8 bits (one byte)

### Key Features

| Feature | Description |
|---------|-------------|
| **Systematic encoding** | Original message preserved in codeword; parity prepended |
| **Error correction** | Berlekamp-Massey + Chien search + Forney algorithm |
| **Erasure correction** | Known-position errors — up to nsym erasures correctable |
| **Interleaving** | Block interleaving for burst-error resilience |
| **RSCode class** | Object-oriented API with fixed parameters |
| **DecodeResult** | Decoder statistics (error count, positions, success flag) |
| **Configuration** | JSON / YAML / TOML config files with auto-detection |
| **Logging** | Structured logging via Python `logging` module |
| **CLI** | 9 subcommands: encode/decode/demo/burst-demo/info/bench/config/stream/version |
| **Pip-installable** | `pip install -e .` with `rsc` entry point |
| **Pure stdlib** | No external dependencies for core functionality |
| **126 tests** | Comprehensive pytest suite with coverage of all features |

## Correction Capabilities

| Parameter | Formula | With nsym=10 |
|-----------|---------|-------------|
| Correctable errors | `⌊nsym/2⌋` | 5 |
| Correctable erasures | `nsym` | 10 |
| Combined (errors + erasures) | `2·e + s ≤ nsym` | varies |
| Burst errors (interleaved, depth d) | `d · ⌊nsym/2⌋` | d×5 |

## Installation

### From source (recommended for development)

```bash
git clone https://github.com/jayis1/creative-projects
cd creative-projects/reed-solomon-codec

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"
```

This installs the `rsc` command-line tool and all test dependencies.

### As a library (no install needed)

Since the project is pure Python with no external dependencies, you can
simply add the `reed-solomon-codec` directory to your `PYTHONPATH` and
import directly:

```python
import sys
sys.path.insert(0, "/path/to/reed-solomon-codec")
from reed_solomon import RSCode
```

### Optional dependencies

```bash
pip install pyyaml      # For YAML config file support
pip install tomli       # For TOML support on Python < 3.11
pip install pytest      # For running tests
```

## Quick Start

```python
from reed_solomon import RSCode

# Create a codec with 10 parity symbols
rs = RSCode(nsym=10)

# Encode a message
message = b"Hello, World!"
encoded = rs.encode_bytes(message)

# Simulate channel corruption (up to 5 errors with nsym=10)
corrupted = bytearray(encoded)
corrupted[3] ^= 0xFF
corrupted[7] ^= 0xAA
corrupted[15] ^= 0x42

# Decode and correct
recovered = rs.decode_data(bytes(corrupted))
assert recovered == message  # ✓ Perfect recovery!
```

## Usage

### Class-Based API (Recommended)

```python
from reed_solomon import RSCode

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
print(f"Success: {result.success}")
```

### Byte-Oriented API

```python
from reed_solomon import encode_message, decode_message

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

Erasures are errors with **known positions** (e.g., a scratched CD where
the read head knows which sectors failed). They are "cheaper" to correct:
`nsym` erasures vs `nsym/2` unknown errors.

```python
from reed_solomon import rs_decode

# ... encode as above ...
corrupted = list(encoded)
erasures = [3, 7, 15, 22]  # known bad positions
for p in erasures:
    corrupted[p] = 0  # value doesn't matter, position is known
corrected = rs_decode(corrupted, nsym=10, erasures=erasures)
```

### Burst-Error Correction with Interleaving

Block interleaving spreads a contiguous burst of errors across multiple
RS codewords, so each individual codeword sees at most one error.

```python
from reed_solomon import encode_interleaved, decode_interleaved

data = b"Interleaving protects against burst errors!"
nsym, depth = 6, 5  # depth=5 → bursts of up to 15 symbols correctable
encoded = encode_interleaved(data, nsym, depth)

# Inject a burst of 10 corrupted bytes (would fail without interleaving)
corrupted = bytearray(encoded)
for i in range(10):
    corrupted[5 + i] ^= 0xFF

recovered = decode_interleaved(bytes(corrupted), nsym, depth, original_len=len(data))
assert recovered == data
```

### Command-Line Interface

The CLI provides 9 subcommands with full `--help` text:

```bash
# Encode a file
rsc encode myfile.txt encoded.rs --nsym 16

# Encode with interleaving for burst-error protection
rsc encode myfile.txt encoded.rs --nsym 16 --interleave 4

# Decode and correct
rsc decode encoded.rs recovered.txt --nsym 16

# Decode interleaved data
rsc decode encoded.rs recovered.txt --nsym 16 --interleave 4

# Run interactive demo
rsc demo

# Demonstrate burst-error correction via interleaving
rsc burst-demo --nsym 6 --depth 4

# Show code parameters
rsc info --nsym 16

# Benchmark throughput
rsc bench --nsym 10 --size 200 --iterations 100

# Generate a configuration file
rsc config --generate config.json --nsym 16

# Validate a configuration file
rsc config --validate config.json

# Stream mode (pipeline)
echo "Hello" | rsc stream encode --nsym 10 | rsc stream decode --nsym 10

# Version info
rsc version
```

Global options (before the subcommand):

```bash
rsc --config config.json --log-level DEBUG demo
rsc --log-level INFO encode data.txt --nsym 16
```

### Configuration Files

The codec supports JSON, YAML, and TOML configuration files for setting
default parameters. Format is auto-detected from the file extension.

**JSON example (`config.json`):**
```json
{
  "nsym": 16,
  "interleaving_depth": 4,
  "log_level": "INFO",
  "log_file": null,
  "log_format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
}
```

**YAML example (`config.yaml`):**
```yaml
nsym: 16
interleaving_depth: 4
log_level: INFO
```

**TOML example (`config.toml`):**
```toml
nsym = 16
interleaving_depth = 4
log_level = "INFO"
```

**Python API:**
```python
from reed_solomon import CodecConfig, load_config

# Create and save
config = CodecConfig(nsym=16, interleaving_depth=4, log_level="INFO")
config.save("config.json")

# Load and use
config = load_config("config.json")
config.validate()
config.setup_logging()
```

### Stream Mode (Pipelines)

Encode/decode data through stdin/stdout for use in shell pipelines:

```bash
# Encode data
echo "Hello, World!" | rsc stream encode --nsym 10 > encoded.bin

# Decode data
cat encoded.bin | rsc stream decode --nsym 10 > recovered.txt

# Chain with other tools
rsc stream encode --nsym 16 < data.txt | gzip > protected.rs.gz
```

### Benchmarking

```bash
rsc bench --nsym 10 --size 200 --iterations 1000
```

```
============================================================
Reed-Solomon Benchmark
============================================================
  nsym: 10, data size: 200 bytes
  Codeword size: 210 bytes
  Max correctable errors: 5

  Encode: 1000 iterations in 0.12s
    Throughput: 1638.4 KB/s
  Decode (no errors): 1000 iterations in 0.08s
    Throughput: 2625.0 KB/s
  Decode (5 errors): 1000 iterations in 0.25s
    Throughput: 840.0 KB/s
```

## Architecture

```
reed-solomon-codec/
├── reed_solomon/               # Main package (pip-installable)
│   ├── __init__.py             # Public API re-exports
│   ├── __main__.py             # python -m reed_solomon entry point
│   ├── gf.py                   # GF(2^8) arithmetic & polynomial operations
│   ├── codec.py                # RS encoder, decoder, interleaving, RSCode class
│   ├── config.py               # Configuration system (JSON/YAML/TOML)
│   └── cli.py                  # argparse CLI (9 subcommands)
├── tests/                      # pytest test suite (126 tests)
│   ├── test_rs_codec.py       # Core codec tests (78 tests)
│   ├── test_bug_hunt.py        # Bug regression tests (11 tests)
│   ├── test_config.py         # Config system tests (22 tests)
│   └── test_cli.py            # CLI integration tests (15 tests)
├── examples/                   # Usage example scripts
│   ├── basic_encode_decode.py  # Simple encode → corrupt → decode
│   ├── erasure_correction.py   # Erasure (known-position) correction
│   ├── burst_error.py          # Interleaving for burst errors
│   ├── file_protection.py      # File-level protection demo
│   └── config_example.py       # Config file load/save demo
├── .github/workflows/
│   └── ci.yml                  # GitHub Actions CI (Python 3.10–3.13)
├── pyproject.toml              # Package metadata & build config
├── config.sample.json          # Sample configuration file
├── gf.py                       # Backward-compat shim → reed_solomon.gf
├── rs_codec.py                 # Backward-compat shim → reed_solomon.codec
├── cli.py                      # Backward-compat CLI shim → reed_solomon.cli
├── CONTRIBUTING.md             # Development guidelines
├── LICENSE                     # MIT License
└── README.md                   # This file
```

### How It Works

#### 1. Galois Field Arithmetic (`gf.py`)

GF(2⁸) is a finite field with 256 elements. All arithmetic uses the irreducible polynomial 0x11D:
- **Addition/Subtraction:** XOR (same operation in characteristic-2 fields)
- **Multiplication:** Via precomputed log/exp tables — `mul(a,b) = exp[log[a] + log[b]]`
- **Division:** `div(a,b) = exp[(log[a] - log[b]) % 255]`
- **Inversion:** `inv(a) = exp[255 - log[a]]`

The log and exp (antilog) tables are precomputed at import time, making all field operations O(1). Polynomial operations (add, mul, div, eval, scale) use the **lowest-degree-first** convention: `poly[0]` is the constant term.

#### 2. Encoding (`codec.py`)

Systematic encoding preserves the original message in the codeword and prepends parity symbols:

```
codeword = [parity (nsym symbols)] + [message (k symbols)]
```

The encoder:
1. Computes the generator polynomial `g(x) = ∏(x - αⁱ)` for `i = 0..nsym-1` (cached for performance)
2. Computes `parity = (message × x^nsym) mod g(x)` via polynomial long division
3. Returns `parity + message` as the codeword

A valid codeword has all-zero syndromes because it's a multiple of g(x), which has roots at α⁰, α¹, ..., α^(nsym-1).

#### 3. Decoding Pipeline

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

#### 4. Erasure Correction

Erasures (errors with known positions) are easier to correct than unknown errors. The decoder builds the erasure locator polynomial directly from the known positions, bypassing Berlekamp-Massey. Each erasure at position p contributes a factor `(x - α⁻ᵖ)` to Λ(x).

#### 5. Interleaving for Burst Errors

Block interleaving spreads burst errors across multiple RS codewords. With interleaving depth `d`, a burst of length `d × ⌊nsym/2⌋` can be corrected — each codeword sees at most `⌊nsym/2⌋` errors from the burst.

#### 6. Configuration System (`config.py`)

The `CodecConfig` dataclass provides a typed, validated configuration with
serialisation to JSON, YAML, and TOML. It supports file load/save with
format auto-detection from the file extension, and integrates with Python's
`logging` module for log level and handler configuration.

## Examples

Five runnable example scripts are included in `examples/`:

```bash
python3 examples/basic_encode_decode.py    # Simple encode → corrupt → decode
python3 examples/erasure_correction.py     # Erasure (known-position) correction
python3 examples/burst_error.py             # Interleaving for burst errors
python3 examples/file_protection.py        # File-level protection demo
python3 examples/config_example.py         # Config file load/save demo
```

### Correcting Maximum Errors (5 errors with nsym=10)

```python
from reed_solomon import rs_encode, rs_decode

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

| Method / Property | Description |
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

### Configuration

| Class / Function | Description |
|--------|-------------|
| `CodecConfig` | Configuration dataclass with validation |
| `CodecConfig.load(path)` | Load config from file (auto-detect format) |
| `CodecConfig.save(path)` | Save config to file (auto-detect format) |
| `CodecConfig.validate()` | Validate all config values |
| `CodecConfig.setup_logging()` | Configure Python logging |
| `load_config(path)` | Convenience: load config from file |

## Testing

```bash
# Run the full test suite (126 tests)
python -m pytest tests/ -v

# Run a specific test file
python -m pytest tests/test_rs_codec.py -v

# Run a specific test class
python -m pytest tests/test_rs_codec.py::TestErrorCorrection -v

# With coverage
python -m pytest tests/ --cov=reed_solomon --cov-report=term-missing
```

The test suite covers:
- **GF(2⁸) arithmetic properties** (17 tests) — addition, multiplication, division, inversion, powers, distributivity
- **Polynomial operations** (10 tests) — add, multiply, divide, evaluate, scale, empty edge cases
- **Generator polynomial properties** (3 tests) — degree, roots, caching
- **Encoding correctness** (8 tests) — systematic structure, parity, syndrome verification
- **Error correction** (6 tests) — various error counts, randomized round-trips
- **Erasure correction** (5 tests) — single, max, too many, out of range, randomized
- **RSCode class API** (8 tests) — encode/decode, properties, repr, str
- **Interleaving & burst correction** (5 tests) — round-trip, invalid rows, burst correction, padding
- **Byte API** (3 tests) — encode/decode with no errors, errors, erasures
- **Edge cases** (9 tests) — empty, single symbol, all-zero, all-ones, large nsym, duplicates
- **Stress tests** (2 tests) — 150+ random round-trips
- **Bug hunt regressions** (11 tests) — all 7 bugs from Phase 3
- **Config system** (22 tests) — defaults, validation, JSON/YAML/TOML, file I/O, logging
- **CLI integration** (15 tests) — all subcommands, round-trips, error handling

## Known Issues (Resolved)

The following bugs were found during systematic code review and fixed:

1. **`gf_poly_mul` crash on empty inputs** — Calling `gf_poly_mul([], [1])` returned `[]` (empty list) instead of `[0]`, because `len([]) + len([1]) - 1 = 0` and `[0] * 0 = []`. **Fix:** Added an early return `[0]` when either input is empty.

2. **`GF256.pow` accepts negative exponents** — Passing a negative exponent `e` to `GF256.pow()` silently produced incorrect results instead of raising an error. **Fix:** Added validation that raises `ValueError` for negative exponents and `TypeError` for non-integer exponents.

3. **`decode_interleaved` missing minimum data length validation** — When given data shorter than `nsym * depth` bytes, the function would compute a negative `msg_len` and produce incorrect output instead of raising a clear error. **Fix:** Added explicit length validation with a descriptive error message.

4. **`encode_interleaved` missing block size validation** — When `block_size + nsym > 255`, the underlying `rs_encode` would raise, but with a confusing error message that didn't mention the interleaving context. **Fix:** Added explicit validation with a clear error message explaining the interleaving constraint.

5. **CLI `decode` command replaces all `.rs` occurrences in path** — The `cmd_decode` function used `args.input.replace(".rs", "")` which replaces ALL occurrences of ".rs" in the path, not just the file extension. For example, `path/to.rs/file.rs` would become `path/to/file` (losing a directory name). **Fix:** Changed to check `args.input.endswith(".rs")` and strip only the trailing extension.

6. **`gf_poly_div` incorrect remainder extraction** — The original polynomial division algorithm used an incorrect separator index (`-(len(rev_divisor) - 1)`) for extracting the remainder, which caused wrong results for degree-0 divisors (like `[1]`) and self-division. **Fix:** Rewrote the division algorithm to properly track the quotient length and extract the remainder from the correct position, with a precomputed divisor leading coefficient inverse for efficiency.

7. **`deinterleave` function was identical to `interleave`** — The `deinterleave` function used the same formula as `interleave` (mapping `data[i]` to `result[r*cols + c]`), making it NOT the inverse of interleaving. **Fix:** Changed `deinterleave` to use the inverse mapping: `result[i] = data[(i%rows)*cols + (i//rows)]`.

## Roadmap

Future development plans:

- [ ] **Extended GF support** — GF(2^m) for m ≠ 8 (e.g., GF(2^4), GF(2^16))
- [ ] **Euclidean algorithm decoder** — Alternative to Berlekamp-Massey
- [ ] **Soft-decision decoding** — Utilize confidence information for better correction
- [ ] **Convolutional interleaving** — Alternative to block interleaving
- [ ] **Multi-threaded encoding** — Parallel block encoding for large data
- [ ] **C extension** — Optional C-accelerated field arithmetic
- [ ] **QR code integration** — Demonstrate RS codes in a real QR encoder
- [ ] **Product codes** — 2D RS codes for even stronger correction
- [ ] **Erasure-only mode optimization** — Skip Berlekamp-Massey when only erasures
- [ ] **Progressive decoding** — Report partial results for near-uncorrectable cases

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for
development setup, coding conventions, and the pull request checklist.

Key guidelines:
1. All public functions must have type hints and docstrings
2. Every new feature or bug fix must include tests
3. Keep the core library dependency-free (stdlib only)
4. Use absolute imports (`from reed_solomon.codec import ...`)

## Changelog

### v2.0.0 (2026-06-30) — Comprehensive Improvement

**Architecture:**
- Refactored from flat scripts to modular `reed_solomon` Python package
- Split monolithic code into `gf.py`, `codec.py`, `config.py`, `cli.py` modules
- Added backward-compatibility shims (`gf.py`, `rs_codec.py`, `cli.py` at root)
- Made pip-installable with `pyproject.toml` and `rsc` entry point

**New Features:**
- **Configuration system** — `CodecConfig` dataclass with JSON/YAML/TOML serialisation
- **Structured logging** — Python `logging` module integration throughout
- **Enhanced CLI** — Expanded from 5 to 9 subcommands (added `bench`, `config`, `stream`, `version`)
- **Stream mode** — stdin/stdout pipeline encode/decode
- **Config file support** — `--config` flag for loading parameters from files
- **Interleaving in CLI** — `--interleave` flag for encode/decode subcommands
- **Benchmark subcommand** — Throughput measurement for encode/decode

**Code Quality:**
- Type hints throughout all modules
- Comprehensive docstrings (Google style)
- Input validation with clear error messages
- Logging at DEBUG/INFO/WARNING levels

**Testing:**
- Expanded from 89 to **126 tests** (37 new tests)
- Added `test_config.py` — 22 config system tests
- Added `test_cli.py` — 15 CLI integration tests
- Updated existing tests for package imports

**Documentation:**
- Dramatically improved README with badges, TOC, architecture diagram
- Added CONTRIBUTING.md with development guidelines
- Added LICENSE (MIT)
- Added sample config file (`config.sample.json`)
- Added 5 example scripts in `examples/` directory
- Added GitHub Actions CI (Python 3.10–3.13)

### v1.0.0 (2026-06-30) — Initial Release

- GF(2⁸) arithmetic with precomputed log/exp tables
- Systematic RS encoding via polynomial division
- Berlekamp-Massey error locator polynomial
- Chien search for error positions
- Forney algorithm for error magnitudes
- Error + erasure correction
- Block interleaving for burst errors
- RSCode class API
- DecodeResult statistics
- 89 tests
- 7 bugs found and fixed

## Algorithm References

- Reed, I. S.; Solomon, G. (1960). "Polynomial Codes over Certain Finite Fields"
- Berlekamp, E. R. (1968). "Algebraic Coding Theory"
- Forney, G. D. (1965). "On Decoding BCH Codes"
- Lin, S.; Costello, D. (2004). "Error Control Coding", 2nd Edition

## License

MIT License — see [LICENSE](LICENSE) for details.