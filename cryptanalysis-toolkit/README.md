# 🔐 Cryptanalysis Toolkit

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests: 194](https://img.shields.io/badge/tests-194%20passing-brightgreen.svg)](tests/)
[![Version: 2.0](https://img.shields.io/badge/version-2.0.0-orange.svg)](pyproject.toml)

A comprehensive Python framework for **implementing, analyzing, and breaking classical ciphers** using statistical methods including frequency analysis, Kasiski examination, index of coincidence, Friedman test, pattern matching, hill climbing, and matrix algebra.

> *"The art of breaking ciphers is the art of finding the weak point.*"  
> — Friedrich Kasiski

---

## 📋 Table of Contents

- [Features](#-features)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Usage](#-usage)
  - [Python Library](#python-library)
  - [Command Line Interface](#command-line-interface)
  - [Pipeline (Chained Operations)](#pipeline-chained-operations)
  - [Structured Analysis (JSON)](#structured-analysis-json)
- [Cipher Implementations](#-cipher-implementations)
- [Analysis Tools](#-analysis-tools)
- [Automatic Cipher Breaking](#-automatic-cipher-breaking)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [Testing](#-testing)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [License](#-license)
- [Changelog](#-changelog)

---

## ✨ Features

### 15 Classical Cipher Implementations
| Cipher | Type | Key Space | Self-Inverse |
|--------|------|-----------|-------------|
| Caesar | Monoalphabetic shift | 26 | No |
| ROT13 | Caesar (shift=13) | 1 | Yes |
| Atbash | Reciprocal substitution | 1 | Yes |
| Substitution | Monoalphabetic | 26! | No |
| Vigenère | Polyalphabetic | 26^k | No |
| Affine | Monoalphabetic linear | 312 | No |
| Hill | Polygraphic matrix | 26^(n²) | No |
| Playfair | Digraph substitution | ~25! | No |
| Autokey | Polyalphabetic + plaintext key | 26^k | No |
| Beaufort | Reciprocal polyalphabetic | 26^k | Yes |
| Porta | Digraphic polyalphabetic | 26^k | Yes |
| Rail Fence | Transposition | text_len | No |
| Columnar Transposition | Transposition | key_perm | No |
| XOR | Byte-level XOR | 2^(8×k) | Yes |
| Enigma | Rotor machine | ~10^16 | Yes |

### Analysis Tools
- **Frequency Analyzer** — Letter, bigram, trigram frequencies; χ² statistics; Pearson correlation; shift detection; formatted reports
- **Index of Coincidence** — IC calculation; key length estimation; **Friedman test**; language identification
- **Kasiski Examiner** — Repeated sequence detection; distance factoring; key length scoring; formatted reports
- **N-gram Scorer** — Monogram & bigram log-probability scoring; weighted combined scoring for hill climbing
- **Pattern Matcher** — Word pattern matching against dictionary; powerful for substitution cipher solving

### Automatic Cipher Breaking
- **Caesar Breaker** — Scores all 26 shifts by frequency correlation
- **Affine Breaker** — Tests all 312 valid (a, b) key pairs
- **Vigenère Breaker** — Kasiski + IC key length estimation, per-position frequency analysis
- **Substitution Breaker** — Simulated annealing hill climbing with frequency-based initial key
- **XOR Single-byte Breaker** — English frequency scoring with space ratio bonus
- **Cipher Type Identifier** — IC, χ², and frequency statistics to classify unknown ciphertexts

### Pipeline & Batch Processing
- **CipherPipeline** — Chain multiple cipher operations in sequence
- **Config File Support** — Define pipelines in YAML/JSON
- **File Processing** — Read from / write to files
- **Structured Analysis** — JSON output for programmatic use

---

## 🚀 Quick Start

```python
from cryptanalysis_toolkit import CaesarCipher, VigenereCipher, CipherBreaker

# Encrypt
cipher = VigenereCipher(keyword="SECRET")
ciphertext = cipher.encrypt("ATTACK AT DAWN")
print(ciphertext)  # SXVRGD SX FRAG

# Break automatically
breaker = CipherBreaker()
results = breaker.break_caesar(ciphertext)
print(f"Best guess: shift={results[0]['shift']}, text={results[0]['plaintext'][:30]}")
```

---

## 📦 Installation

```bash
# Clone and install
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/cryptanalysis-toolkit

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install with dev dependencies
pip install -e ".[dev]"

# Verify installation
cryptanalysis list
python -c "import cryptanalysis_toolkit; print(cryptanalysis_toolkit.__version__)"
```

### Requirements
- Python 3.10+
- PyYAML (for pipeline config files)
- pytest, pytest-cov (for development)

---

## 📖 Usage

### Python Library

#### Basic Cipher Operations

```python
from cryptanalysis_toolkit import (
    CaesarCipher, VigenereCipher, SubstitutionCipher,
    AffineCipher, ROT13Cipher, AtbashCipher, HillCipher,
    XORCipher, EnigmaCipher,
)

# Caesar cipher
caesar = CaesarCipher(shift=3)
ct = caesar.encrypt("HELLO WORLD")    # "KHOOR ZRUOG"
pt = caesar.decrypt(ct)                # "HELLO WORLD"

# ROT13 (self-inverse: encrypt = decrypt)
rot13 = ROT13Cipher()
ct = rot13.encrypt("Hello World")      # "Uryyb Jbeyq"
pt = rot13.decrypt(ct)                 # "Hello World"

# Atbash cipher (self-inverse, A↔Z, B↔Y, ...)
atbash = AtbashCipher()
ct = atbash.encrypt("HELLO")           # "SVOOL"

# Hill cipher (3×3 matrix)
hill = HillCipher(key_matrix=[
    [6, 24, 1],
    [13, 16, 10],
    [20, 17, 15]
])
ct = hill.encrypt("ACT")               # "POH"

# Vigenère cipher
vig = VigenereCipher(keyword="SECRET")
ct = vig.encrypt("ATTACK AT DAWN")     # "SXVRGD SX FRAG"

# Substitution cipher from keyword
sub = SubstitutionCipher.from_keyword("ZEBRA")
ct = sub.encrypt("HELLO")              # "CDBBO"

# Affine cipher: E(x) = (ax + b) mod 26
aff = AffineCipher(a=5, b=8)
ct = aff.encrypt("HELLO")              # "RCLLA"

# XOR cipher (works on bytes)
xor = XORCipher(key=b"secret")
encrypted = xor.encrypt(b"Hello World")
decrypted = xor.decrypt(encrypted)

# Enigma machine
enigma = EnigmaCipher(
    rotor_order=[2, 4, 1],
    initial_positions=[0, 0, 0],
    plugboard_pairs=[("A", "B"), ("S", "Z")],
)
ct = enigma.encrypt("SECRETMESSAGE")
pt = enigma.decrypt(ct)  # "SECRETMESSAGE"
```

#### Frequency Analysis

```python
from cryptanalysis_toolkit import FrequencyAnalyzer, IndexOfCoincidence

analyzer = FrequencyAnalyzer()

# Letter frequencies
freqs = analyzer.letter_frequencies("SOME CIPHERTEXT")
print(freqs)  # {'A': 7.5, 'B': 0.0, ...}

# Chi-squared vs English
chi = analyzer.chi_squared("SOME CIPHERTEXT")

# Correlation with English (-1 to 1)
corr = analyzer.frequency_correlation("SOME CIPHERTEXT")

# Find most likely Caesar shift
shift, score = analyzer.most_likely_shift("SOME CIPHERTEXT")

# Human-readable report
report = analyzer.frequency_report("SOME CIPHERTEXT", top_n=10)
print(report)
```

#### Index of Coincidence & Friedman Test

```python
from cryptanalysis_toolkit import IndexOfCoincidence

ic = IndexOfCoincidence()

# Calculate IC
ic_value = ic.calculate("SOME CIPHERTEXT")
# English ≈ 0.0667, random ≈ 0.0385

# Friedman test for key length estimation
key_len = ic.friedman_test("SOME CIPHERTEXT")
print(f"Estimated key length: {key_len:.1f}")

# IC-based key length estimation
candidates = ic.estimated_key_length("SOME CIPHERTEXT", max_length=20)
for kl, avg_ic in candidates[:5]:
    print(f"Key length {kl}: average IC = {avg_ic:.6f}")

# Language identification
langs = ic.identify_language("SOME PLAINTEXT")
```

#### Kasiski Examination

```python
from cryptanalysis_toolkit import KasiskiExaminer

kasiski = KasiskiExaminer(min_sequence_length=3)

# Find repeated sequences
sequences = kasiski.find_repeated_sequences("CIPHERTEXT")

# Analyze key length candidates
results = kasiski.analyze("CIPHERTEXT", max_key_length=20)
for kl, score in results[:5]:
    print(f"Key length {kl}: score {score}")

# Human-readable report
report = kasiski.kasiski_report("CIPHERTEXT")
```

#### Pattern Matching

```python
from cryptanalysis_toolkit import PatternMatcher, word_pattern

matcher = PatternMatcher()

# Get letter pattern of a word
pat = word_pattern("HELLO")  # "0.1.2.2.3"

# Find matching dictionary words
matches = matcher.find_matches("XLLQ")
# Returns words with same pattern as "XLLQ" (e.g., "ALL", "ILL", ...)
```

### Command Line Interface

```bash
# List available ciphers
cryptanalysis list

# Encrypt
cryptanalysis encrypt caesar "HELLO WORLD" --shift 3
cryptanalysis encrypt vigenere "HELLO WORLD" --key SECRET
cryptanalysis encrypt affine "HELLO WORLD" --a 5 --b 8
cryptanalysis encrypt playfair "HELLO" --key KEYWORD
cryptanalysis encrypt railfence "HELLO" --rails 3
cryptanalysis encrypt rot13 "Hello World"
cryptanalysis encrypt atbash "HELLO"
cryptanalysis encrypt hill "ACT"
cryptanalysis encrypt substitution "HELLO" --key QWERTYUIOPASDFGHJKLZXCVBNM
cryptanalysis encrypt xor "HELLO" --key secret
cryptanalysis encrypt enigma "HELLO" --rotors 1 2 3 --positions 0 0 0

# Decrypt
cryptanalysis decrypt vigenere "RIJVS" --key KEY
cryptanalysis decrypt caesar "KHOOR" --shift 3
cryptanalysis decrypt enigma "CIPHERTEXT" --rotors 1 2 3 --positions 0 0 0 --plugboard AB,CD

# Read from / write to files
cryptanalysis encrypt caesar --file input.txt --output encrypted.txt --shift 7

# Break ciphers automatically
cryptanalysis break caesar "KHOOR ZRUOG"
cryptanalysis break vigenere "ciphertext" --max-key-length 10
cryptanalysis break affine "ciphertext"
cryptanalysis break substitution "ciphertext" --iterations 5000
cryptanalysis break auto "ciphertext"

# Analyze ciphertext
cryptanalysis analyze "ciphertext" --top-n 15

# Structured JSON analysis
cryptanalysis analyze "ciphertext" --json

# Verbose / quiet modes
cryptanalysis --verbose encrypt caesar "HELLO" --shift 3
cryptanalysis --quiet break caesar "KHOOR"
```

### Pipeline (Chained Operations)

Chain multiple cipher operations using a YAML or JSON config file:

```yaml
# pipeline_config.yaml
operations:
  - cipher: caesar
    action: encrypt
    params:
      shift: 7
  - cipher: vigenere
    action: encrypt
    params:
      key: SECRET
```

```bash
# Run the pipeline
cryptanalysis pipeline pipeline_config.yaml "ATTACK AT DAWN"
# Output: ZECYNK ZE MYHN

# With file I/O
cryptanalysis pipeline pipeline_config.yaml --file input.txt --output encrypted.txt
```

Or use the Python API:

```python
from cryptanalysis_toolkit import CipherPipeline

pipeline = CipherPipeline([
    {"cipher": "caesar", "action": "encrypt", "params": {"shift": 7}},
    {"cipher": "vigenere", "action": "encrypt", "params": {"key": "SECRET"}},
])
encrypted = pipeline.run("ATTACK AT DAWN")
```

### Structured Analysis (JSON)

```python
from cryptanalysis_toolkit import analyze_text
import json

result = analyze_text("VPT XYZES QYSNP NDE NLOXH VZVT BWL PRBG SVK")
print(json.dumps(result, indent=2))
# {
#   "letter_frequencies": {"V": 11.43, "N": 8.57, ...},
#   "index_of_coincidence": 0.037,
#   "friedman_key_length": 2.9,
#   "chi_squared": 320.43,
#   "correlation": 0.025,
#   "ic_key_length_candidates": [[3, 0.065], [6, 0.058], ...],
#   "kasiski_candidates": [[6, 15], [3, 12], ...]
# }
```

---

## 🔤 Cipher Implementations

### Caesar / ROT13
The Caesar cipher shifts each letter by a fixed amount (default 3). ROT13 is the special case with shift 13, where encrypt = decrypt. Brute-force breaking is trivial — try all 26 shifts and score by frequency correlation.

### Atbash
A reciprocal substitution cipher mapping A↔Z, B↔Y, C↔X, etc. Originally used with the Hebrew alphabet. No key is needed; encryption = decryption.

### Vigenère
A polyalphabetic cipher using a keyword to determine different shift values for each letter position. Vulnerable to Kasiski examination and IC-based key length estimation.

### Hill Cipher
A polygraphic substitution cipher using matrix multiplication over Z_26. The key is an n×n invertible matrix. Requires the matrix determinant to be coprime with 26. Supports 2×2, 3×3, and larger key matrices.

### Enigma Machine
A simplified 3-rotor Enigma simulation with plugboard, reflector B, and rotor stepping. Features 5 standard rotors (I–V), turnover positions, and double-stepping logic. Reciprocal: encryption = decryption with the same settings.

### XOR Cipher
Byte-level XOR encryption with a repeating key. The single-byte breaker uses English letter frequency scoring combined with space ratio and printable ASCII analysis to identify the correct key.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│              CLI (cli.py)                 │
│  encrypt / decrypt / break / analyze /   │
│  pipeline / list                         │
├─────────────────────────────────────────┤
│           Pipeline (pipeline.py)          │
│  CipherPipeline · build_cipher ·         │
│  load_config · process_file · analyze    │
├──────────────────┬──────────────────────┤
│   Ciphers/        │   Analysis/          │
│   caesar          │   frequency          │
│   vigenere        │   ic                 │
│   substitution    │   kasiski            │
│   affine          │   ngram              │
│   playfair        │   pattern            │
│   railfence       │                      │
│   columnar        │                      │
│   autokey         ├──────────────────────┤
│   beaufort        │   Breaker            │
│   porta           │   break_caesar       │
│   xor             │   break_affine       │
│   enigma          │   break_vigenere     │
│   rot13           │   break_substitution │
│   atbash          │   identify_type      │
│   hill            │                      │
│   base (ABC)      │                      │
└──────────────────┴──────────────────────┘
```

**Design Principles:**
- Each cipher is a standalone class with `encrypt()` and `decrypt()` methods
- All ciphers validate their parameters on construction
- Non-alphabetic characters pass through unchanged (except XOR)
- Analysis tools are stateless (except cached frequency data)
- The breaker orchestrates analysis tools for automated cryptanalysis
- The pipeline enables composable, config-driven workflows

---

## 📁 Project Structure

```
cryptanalysis-toolkit/
├── README.md                    # This file
├── LICENSE                      # MIT License
├── CONTRIBUTING.md              # Contributing guide
├── pyproject.toml               # Package config (setuptools)
├── .gitignore                   # Git ignore rules
├── .github/
│   └── workflows/
│       └── ci.yml               # GitHub Actions CI
├── cryptanalysis_toolkit/
│   ├── __init__.py              # Package exports (v2.0.0)
│   ├── __main__.py              # python -m entry point
│   ├── py.typed                 # PEP 561 marker
│   ├── cli.py                   # CLI (argparse, 7 subcommands)
│   ├── breaker.py               # Automatic cipher breaking
│   ├── pipeline.py              # Pipeline, batch, config, analyze_text
│   ├── ciphers/
│   │   ├── __init__.py          # Cipher exports
│   │   ├── base.py              # Abstract base class
│   │   ├── caesar.py            # Caesar cipher
│   │   ├── rot13.py             # ROT13 cipher
│   │   ├── atbash.py            # Atbash cipher
│   │   ├── substitution.py      # Monoalphabetic substitution
│   │   ├── vigenere.py          # Vigenère cipher
│   │   ├── affine.py            # Affine cipher
│   │   ├── hill.py              # Hill cipher (matrix-based)
│   │   ├── playfair.py          # Playfair digraph cipher
│   │   ├── autokey.py           # Autokey cipher
│   │   ├── beaufort.py          # Beaufort cipher
│   │   ├── porta.py             # Porta cipher
│   │   ├── railfence.py         # Rail fence cipher
│   │   ├── columnar.py         # Columnar transposition
│   │   ├── xor.py              # XOR cipher
│   │   └── enigma.py           # Enigma machine
│   └── analysis/
│       ├── __init__.py          # Analysis exports
│       ├── frequency.py         # Frequency analysis
│       ├── ic.py                # Index of Coincidence
│       ├── kasiski.py           # Kasiski examination
│       ├── ngram.py            # N-gram scoring
│       └── pattern.py          # Pattern matching
├── examples/
│   ├── quickstart.py           # Interactive examples
│   ├── pipeline_config.yaml    # Pipeline config example
│   └── break_vigenere.yaml     # Vigenère break config
└── tests/
    ├── test_affine.py
    ├── test_analysis.py
    ├── test_atbash.py
    ├── test_breaker.py
    ├── test_caesar.py
    ├── test_cli.py
    ├── test_hill.py
    ├── test_enigma.py
    ├── test_more_ciphers.py
    ├── test_pattern.py
    ├── test_pipeline.py
    ├── test_playfair.py
    ├── test_railfence.py
    ├── test_rot13.py
    ├── test_substitution.py
    ├── test_vigenere.py
    ├── test_xor.py
    └── test_xor_break.py
```

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=cryptanalysis_toolkit --cov-report=term-missing

# Run specific test file
pytest tests/test_hill.py -v

# Run examples
python examples/quickstart.py
```

**194 tests** covering all ciphers, analysis tools, breaker, pipeline, and CLI.

---

## 🗺️ Roadmap

- [ ] **Trigram scorer** — Add trigram log-probability data for better substitution breaking
- [ ] **Bifid cipher** — Another classic polygraphic cipher
- [ ] **ADFGVX cipher** — WWI-era fractionating transposition cipher
- [ ] **One-time pad** — Demonstration of perfect secrecy
- [ ] **Web UI** — Streamlit or Flask interface for interactive exploration
- [ ] **Performance** — Cython/Numba acceleration for brute-force attacks
- [ ] **Dictionary attack** — Word-list based Vigenère key breaking
- [ ] **Crib dragging** — Known-plaintext attack for Vigenère/Enigma
- [ ] **Multi-language** — Frequency data for French, German, Spanish, etc.
- [ ] **RSA basics** — Simple RSA key generation and encryption for educational purposes

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:

- Reporting bugs
- Adding new ciphers
- Adding analysis tools
- Code style and testing requirements
- Pull request process

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

## 📝 Changelog

### v2.0.0 (2026-06-15) — Comprehensive Improvement
- **3 new ciphers**: ROT13, Atbash, Hill (matrix-based)
- **CipherPipeline**: Chain multiple cipher operations from YAML/JSON config
- **Pipeline CLI**: New `pipeline` subcommand
- **Config file support**: YAML/JSON pipeline configurations
- **Structured analysis**: JSON output via `analyze_text()` and `--json` flag
- **File I/O**: `--output` flag to write results to files
- **Stdin support**: Read input from piped stdin
- **Batch processing**: `process_file()` for file-based operations
- **Cipher registry**: `build_cipher()` factory and `CIPHER_REGISTRY`
- **Abstract base class**: `BaseCipher` for consistent interface
- **CLI fixes**: Added `--rotors`/`--positions` to decrypt; input validation; `--plugboard` support
- **XOR break scoring**: Improved from printable-ASCII-only to English frequency analysis
- **GitHub Actions CI**: Multi-version Python testing
- **LICENSE, CONTRIBUTING.md**: Open-source best practices
- **Examples**: `quickstart.py`, pipeline configs
- **194 tests** (up from 115): CLI, pipeline, new ciphers, XOR break, batch processing
- **Comprehensive README**: Badges, TOC, architecture, roadmap, changelog

### v1.1.0 — Enhanced
- Added XOR cipher and Enigma machine
- Added Friedman test and Pattern Matcher
- Fixed Caesar decrypt shift=0 bug
- 115 tests passing

### v1.0.0 — Initial Release
- 10 classical ciphers
- 4 analysis modules
- Automatic cipher breaker
- Full CLI
- 89 tests passing