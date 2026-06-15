# Cryptanalysis Toolkit

A comprehensive Python framework for implementing, analyzing, and breaking classical ciphers using statistical methods including frequency analysis, Kasiski examination, index of coincidence, Friedman test, pattern matching, and hill climbing.

## Features

### 12 Classical Cipher Implementations
- **Caesar Cipher** — Simple shift cipher with brute-force capability
- **Monoalphabetic Substitution** — Arbitrary letter-to-letter mapping with keyword derivation
- **Vigenère Cipher** — Polyalphabetic cipher with keyword
- **Affine Cipher** — E(x) = (ax + b) mod 26 with brute-force over all valid keys
- **Playfair Cipher** — Digraph substitution using a 5×5 key square
- **Rail Fence Cipher** — Zigzag transposition
- **Columnar Transposition** — Column-reordering transposition with keyword
- **Autokey Cipher** — Vigenère variant using plaintext as key extension
- **Beaufort Cipher** — Reciprocal polyalphabetic cipher (encrypt = decrypt)
- **Porta Cipher** — Reciprocal digraphic polyalphabetic cipher
- **XOR Cipher** — Byte-level XOR encryption with single-byte key breaking
- **Enigma Machine** — Simplified 3-rotor Enigma simulation with plugboard

### Analysis Tools
- **Frequency Analyzer** — Letter, bigram, and trigram frequency computation; chi-squared statistics; Pearson correlation with English; automatic Caesar shift detection; formatted reports
- **Index of Coincidence** — IC calculation for cipher type identification; key length estimation for polyalphabetic ciphers; language identification; **Friedman test** for key length estimation
- **Kasiski Examiner** — Repeated sequence detection; distance computation; key length candidate scoring; formatted reports
- **N-gram Scorer** — Monogram and bigram log-probability scoring for English-ness; combined weighted scoring for hill climbing
- **Pattern Matcher** — Word pattern matching against a dictionary of common English words; useful for substitution cipher solving

### Automatic Cipher Breaking
- **Caesar Breaker** — Scores all 26 shifts by frequency correlation
- **Affine Breaker** — Tests all 312 valid (a, b) key pairs
- **Vigenère Breaker** — Kasiski + IC key length estimation, per-position frequency analysis
- **Substitution Breaker** — Simulated annealing hill climbing with frequency-based initial key
- **XOR Single-byte Breaker** — Tries all 256 keys and scores by printable ASCII ratio
- **Cipher Type Identifier** — Uses IC, chi-squared, and frequency statistics to classify unknown ciphertexts

## How It Works

### Cipher Implementations
Each cipher provides `encrypt()` and `decrypt()` methods that handle mixed case and pass through non-alphabetic characters unchanged (except XOR which operates on bytes). Ciphers validate their keys on construction and raise `ValueError` for invalid parameters.

### Frequency Analysis
The `FrequencyAnalyzer` computes letter/bigram/trigram frequency distributions and compares them against known English distributions using:
- **Chi-squared test**: Measures statistical deviation from English frequencies (lower = closer to English)
- **Pearson correlation**: Linear correlation between observed and expected frequencies (-1 to 1, higher = more English-like)

### Index of Coincidence
The IC measures the probability that two randomly chosen letters are the same. For monoalphabetic ciphers, IC ≈ 0.0667 (same as English). For polyalphabetic ciphers, IC drops toward 0.0385 (random). The **Friedman test** uses IC to estimate key length via: k ≈ 0.0266n / (IC(n-1) - 0.0279n + 0.0385)

### Kasiski Examination
Finds repeated substrings in ciphertext, computes distances between repetitions, and factors those distances. Common factors of many distances are likely key lengths.

### Pattern Matching
`PatternMatcher` converts words to letter patterns (e.g., "HELLO" → "0.1.2.2.3") and matches against a built-in dictionary of common English words. This is powerful for breaking substitution ciphers when you can identify partial words.

### Hill Climbing (Substitution Breaking)
Starts with a frequency-matched initial key, then iteratively swaps pairs of letters in the key, accepting improvements (or accepting worse keys with decreasing probability via simulated annealing). Multiple random restarts help avoid local optima.

## Installation

```bash
cd cryptanalysis-toolkit
pip install -e .
```

## Usage

### As a Python Library

```python
from cryptanalysis_toolkit import (
    CaesarCipher, VigenereCipher, SubstitutionCipher, XORCipher, EnigmaCipher,
    FrequencyAnalyzer, IndexOfCoincidence, KasiskiExaminer, NgramScorer,
    PatternMatcher, CipherBreaker
)

# Encrypt/decrypt
cipher = VigenereCipher(keyword="SECRET")
ciphertext = cipher.encrypt("ATTACK AT DAWN")
plaintext = cipher.decrypt(ciphertext)

# XOR cipher (works on bytes)
xor = XORCipher(key=b"secret")
encrypted = xor.encrypt(b"Hello World")
decrypted = xor.decrypt(encrypted)

# Enigma machine
enigma = EnigmaCipher(rotor_order=[1, 2, 3], initial_positions=[0, 0, 0])
ct = enigma.encrypt("ENIGMA")

# Frequency analysis
analyzer = FrequencyAnalyzer()
report = analyzer.frequency_report(ciphertext)

# Index of Coincidence and Friedman test
ic = IndexOfCoincidence()
ic_value = ic.calculate(ciphertext)
friedman_estimate = ic.friedman_test(ciphertext)
key_lengths = ic.estimated_key_length(ciphertext)

# Pattern matching
matcher = PatternMatcher()
matches = matcher.find_matches("XLLQ")  # Find words matching pattern

# Break ciphers
breaker = CipherBreaker()
results = breaker.break_caesar(ciphertext)
results = breaker.break_vigenere(ciphertext)
results = breaker.break_affine(ciphertext)
result = breaker.break_substitution(ciphertext)
```

### Command Line Interface

```bash
# Encrypt
cryptanalysis encrypt caesar "HELLO WORLD" --shift 3
cryptanalysis encrypt vigenere "HELLO WORLD" --key SECRET
cryptanalysis encrypt affine "HELLO WORLD" --a 5 --b 8
cryptanalysis encrypt playfair "HELLO" --key KEYWORD
cryptanalysis encrypt railfence "HELLO" --rails 3
cryptanalysis encrypt substitution "HELLO" --key QWERTYUIOPASDFGHJKLZXCVBNM
cryptanalysis encrypt xor "HELLO" --key secret
cryptanalysis encrypt enigma "HELLO" --rotors 1 2 3

# Decrypt
cryptanalysis decrypt vigenere "RIJVS" --key KEY
cryptanalysis decrypt caesar "KHOOR" --shift 3

# Break ciphers
cryptanalysis break caesar "KHOOR ZRUOG"
cryptanalysis break vigenere "ciphertext" --max-key-length 10
cryptanalysis break affine "ciphertext"
cryptanalysis break substitution "ciphertext" --iterations 5000
cryptanalysis break auto "ciphertext"

# Analyze
cryptanalysis analyze "ciphertext" --top-n 15
```

## Project Structure

```
cryptanalysis-toolkit/
├── README.md
├── pyproject.toml
├── .gitignore
├── cryptanalysis_toolkit/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── breaker.py
│   ├── ciphers/
│   │   ├── __init__.py
│   │   ├── caesar.py
│   │   ├── substitution.py
│   │   ├── vigenere.py
│   │   ├── affine.py
│   │   ├── playfair.py
│   │   ├── railfence.py
│   │   ├── columnar.py
│   │   ├── autokey.py
│   │   ├── beaufort.py
│   │   ├── porta.py
│   │   ├── xor.py
│   │   └── enigma.py
│   └── analysis/
│       ├── __init__.py
│       ├── frequency.py
│       ├── ic.py
│       ├── kasiski.py
│       ├── ngram.py
│       └── pattern.py
└── tests/
    ├── test_caesar.py
    ├── test_substitution.py
    ├── test_vigenere.py
    ├── test_affine.py
    ├── test_playfair.py
    ├── test_railfence.py
    ├── test_more_ciphers.py
    ├── test_xor.py
    ├── test_enigma.py
    ├── test_analysis.py
    ├── test_pattern.py
    └── test_breaker.py
```

## Test Results

115 tests covering all ciphers, analysis tools, and breaker functionality.

## License

MIT