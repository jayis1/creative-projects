# Rune Cipher 🗝️ᚱᚢᚾᛖ

A terminal cryptography playground that encodes messages with historical ciphers, renders output in **Elder Futhark runic Unicode**, cracks ciphertext using frequency analysis and hill-climbing attacks, and provides detailed text analytics.

## Features

### 7 Ciphers
- **Caesar** — Classic shift cipher with configurable key
- **Vigenère** — Polyalphabetic cipher with keyword
- **Atbash** — Mirror alphabet cipher (self-inverse)
- **ROT13** — Caesar with key 13 (self-inverse)
- **Substitution** — Simple substitution with keyword-based key generation
- **Affine** — Modular arithmetic cipher with two keys (a, b)
- **XOR** — Binary XOR cipher with hex output (symmetric)

### Runic Rendering
All output can be displayed in Elder Futhark runes (ᚨᛒᚲᛞᛖᚠ...). Spaces render as `᛬`. Supports full round-trip conversion (text → runes → text).

### Frequency Analysis
Built-in `analyze` command provides:
- Letter frequency chart with comparison to English
- Index of Coincidence (IoC) calculation
- Chi-squared distance from English
- Top bigrams and trigrams
- English likelihood assessment (High/Medium/Low)

### Cracking Engine
- **Caesar**: Brute-force all 25 shifts, scored by normalized frequency + bigram + trigram + common word analysis
- **Vigenère**: Kasiski analysis with Index of Coincidence for key length detection
- **Substitution**: Hill-climbing with random restarts, optimizing combined score
- **Affine**: Brute-force all valid (a, b) pairs
- Atbash/ROT13: Direct decryption (self-inverse)

### Multiple Interfaces
- **CLI mode** — Script-friendly argparse interface for pipelining
- **Interactive mode** — REPL-style playground with history tracking
- **Demo mode** — One-command showcase of all features
- **File I/O** — `--infile` and `--outfile` flags for batch processing
- **Version flag** — `--version` support

## Installation

```bash
# No dependencies — pure Python 3.6+
# Just download and run:
curl -O https://raw.githubusercontent.com/USER/daily-ideas/main/2026-06-12-rune-cipher/rune_cipher.py
chmod +x rune_cipher.py
```

## How to Run

```bash
# Interactive mode (recommended for exploring)
python3 rune_cipher.py interactive

# Demo — see all ciphers in action
python3 rune_cipher.py demo

# Show version
python3 rune_cipher.py --version

# Encrypt with Caesar cipher
python3 rune_cipher.py encrypt --cipher caesar --key 3 --text "hello world"

# Encrypt with runic output
python3 rune_cipher.py encrypt --cipher caesar --key 7 --text "attack at dawn" --runic

# Encrypt with Vigenère cipher
python3 rune_cipher.py encrypt --cipher vigenere --key secret --text "meet me at the bridge"

# Encrypt with Affine cipher (a=5, b=8)
python3 rune_cipher.py encrypt --cipher affine --key 5,8 --text "hello"

# Encrypt with XOR cipher
python3 rune_cipher.py encrypt --cipher xor --key secret --text "hello"

# Decrypt
python3 rune_cipher.py decrypt --cipher caesar --key 3 --text "khoor zruog"
python3 rune_cipher.py decrypt --cipher affine --key 5,8 --text "rclla"
python3 rune_cipher.py decrypt --cipher xor --key secret --text "1b 00 0f 1e 0a"

# Crack a Caesar cipher (tries all 25 shifts, ranks by English-likeness)
python3 rune_cipher.py crack --cipher caesar --text "khoor zruog"

# Crack a Vigenère cipher (Kasiski analysis)
python3 rune_cipher.py crack --cipher vigenere --text "rngete glv zbvklrwj ug hrqa"

# Crack an Affine cipher (brute-force valid keys)
python3 rune_cipher.py crack --cipher affine --text "zrc ivswcvz"

# Frequency analysis
python3 rune_cipher.py analyze --text "khoor zruog"

# Convert text to runes
python3 rune_cipher.py runes --text "hello world"

# Read from file / write to file
python3 rune_cipher.py encrypt --cipher caesar --key 3 --infile plaintext.txt --outfile ciphertext.txt
```

## Usage Examples

### Interactive Mode

```
rune ⟩ encrypt caesar 5 secret message
  ╔══════════════════════════════════════╗
  ║  Caesar (key=5) — Encrypted         ║
  ║  ᛪᛃᚺᚱᛦ᛬ᛗᛗᛋᛋᚨᚷᛖ                  ║
  ╚══════════════════════════════════════╝

  ASCII: xjhwjy rjjxyf nljjqj

rune ⟩ crack caesar khoor zruog
  [1] Key 3: hello world ← BEST MATCH

rune ⟩ runes attack at dawn
  ᛏᚨᛏᛏᚨᚲᚴ᛬ᚨᛏ᛬ᛞᚨᚹᚾ

rune ⟩ stats khoor zruog
  ────────────────────────────────────────────────────
  📊 FREQUENCY ANALYSIS
  ...

rune ⟩ encrypt affine 5,8 secret message
  ╔══════════════════════════════════════╗
  ║  Affine (a=5, b=8) — Encrypted      ║
  ║  ᛗᛖᚲᚱᛖᛏ᛬ᛗᛖᛋᛋᚨᚷᛖ                  ║
  ╚══════════════════════════════════════╝

rune ⟩ history
    1: encrypt caesar 5 secret message
    2: crack caesar khoor zruog
    3: runes attack at dawn
```

### Cracking

The cracker uses:
- **Caesar**: Brute-force all 25 shifts, scored by normalized letter frequency + bigram + trigram + common word analysis
- **Vigenère**: Index-of-coincidence to guess key length, then frequency analysis per column
- **Substitution**: Hill-climbing with random restarts (8 restarts × 500 iterations), optimizing combined score
- **Affine**: Brute-force all valid (a, b) pairs where gcd(a, 26) = 1

Longer ciphertexts produce more accurate results. Short texts (<20 letters) may not crack reliably, though common word matching helps.

### Affine Cipher

The Affine cipher uses the formula E(x) = (ax + b) mod 26, where `a` must be coprime with 26. Valid `a` values: 1, 3, 5, 7, 9, 11, 15, 17, 19, 21, 23, 25.

```bash
# Encrypt with Affine (a=5, b=8)
python3 rune_cipher.py encrypt --cipher affine --key 5,8 --text "hello"
# Result: rclla

# Decrypt
python3 rune_cipher.py decrypt --cipher affine --key 5,8 --text "rclla"
# Result: hello

# Crack (tries all 312 valid key combinations)
python3 rune_cipher.py crack --cipher affine --text "rclla"
```

### XOR Cipher

XOR encryption is symmetric — encrypting twice with the same key decrypts. Output is hex-encoded for safe display.

```bash
# Encrypt
python3 rune_cipher.py encrypt --cipher xor --key secret --text "hello"
# Output: 1b 00 0f 1e 0a

# Decrypt
python3 rune_cipher.py decrypt --cipher xor --key secret --text "1b 00 0f 1e 0a"
# Output: hello
```

### Frequency Analysis

```bash
python3 rune_cipher.py analyze --text "khoor zruog"
```

Outputs: letter frequency chart with English comparison, Index of Coincidence, chi-squared distance, bigrams, trigrams, and English likelihood rating.

### Substitution Cipher with Keywords

```bash
# Use a keyword to generate the substitution alphabet
python3 rune_cipher.py encrypt --cipher substitution --key rune --text "hello"
# Internally generates: runeabcdfghijklmopqstvwxyz (keyword-based alphabet)
```

## Unicode Handling

All ciphers operate exclusively on ASCII letters (a–z). Non-ASCII characters — including runic characters, accented letters (é, ü), and emoji — are **passed through unchanged** and not transformed. This means:

- Encrypting runic text preserves the runes: `caesar_encrypt("ᚨᛒᚲ", 3)` → `"ᚨᛒᚲ"` (unchanged)
- Accented letters pass through: `caesar_encrypt("café", 3)` → `"fdié"` (é unchanged)
- Runic conversion (`text_to_runes`) is independent and only works on a–z letters
- Frequency analysis and cracking functions only count ASCII a–z letters

This design prevents crashes and garbled output when processing text that contains Unicode characters.

## Runic Alphabet

The tool maps A–Z to Elder Futhark runes:

| A | B | C | D | E | F | G | H | I | J | K | L | M | N | O | P | Q | R | S | T | U | V | W | X | Y | Z |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ᚨ | ᛒ | ᚲ | ᛞ | ᛖ | ᚠ | ᚷ | ᚺ | ᛁ | ᛃ | ᚴ | ᛚ | ᛗ | ᚾ | ᛟ | ᛈ | ᛩ | ᚱ | ᛋ | ᛏ | ᚢ | ᚡ | ᚹ | ᛪ | ᛦ | ᛉ |

Spaces render as `᛬`

## Testing

```bash
python3 test_rune_cipher.py
```

Runs 49 tests covering:
- Round-trip encryption/decryption for all 7 ciphers
- Runic text conversion (text → runes → text)
- Known-value tests for Caesar, Vigenère, Atbash, Affine
- Edge cases (empty strings, invalid keys, non-alpha characters)
- Cracking accuracy tests (including short text like "khoor zruog")
- Frequency analysis validation
- Keyword key generation and deduplication
- XOR round-trip with special characters
- Caesar with large keys (> 25)
- **Unicode safety**: Runic characters, accented letters, and emoji pass through all ciphers without crashes or garbled output
- **Non-ASCII passthrough**: All cipher functions correctly ignore Unicode letters and only transform ASCII a–z
- **Frequency analysis with non-ASCII**: Runic/accented text returns an error (no a–z letters found) rather than producing misleading results
- **crack_affine with non-alpha text**: Returns empty list instead of spurious candidates

## Changelog

### v2.0.3 — Unicode Safety Bug Fixes (2026-06-13)
- **Fixed crash in `atbash_encrypt`**: Input containing Unicode letters (runic chars, accented letters like é) caused `ValueError: chr() arg not in range(0x110000)` because the formula `ord('z') - (ord(ch) - ord('a'))` produced invalid code points for non-ASCII letters.
- **Fixed crash in `substitution_encrypt`**: Input containing Unicode letters caused `IndexError: string index out of range` because `ord(ch) - ord('a')` produced indices outside 0–25 for non-ASCII characters.
- **Fixed silent corruption in all cipher functions**: `caesar_encrypt`, `vigenere_encrypt`, `vigenere_decrypt`, `affine_encrypt`, `affine_decrypt`, and `rot13_encrypt` (which calls `caesar_encrypt`) all used `ch.isalpha()` which returns True for Unicode letters like runic characters and accented letters. This caused these characters to be incorrectly transformed through the cipher math, producing garbage output. Changed all cipher functions to use `'a' <= ch <= 'z'` to only transform ASCII lowercase letters.
- **Fixed `analyze_frequency` Unicode handling**: `isalpha()` counted Unicode letters (runes, accented chars) in `total_letters` and `most_common_letters`, producing misleading analysis. Now only ASCII a–z letters are counted.
- **Fixed `frequency_score`, `bigram_score`, `combined_score`**: Same `isalpha()` issue caused incorrect scoring when text contained Unicode letters. Now only scores ASCII a–z letters.
- **Fixed `crack_vigenere` and `crack_substitution`**: Same `isalpha()` issue in ciphertext cleaning. Now only extracts ASCII a–z letters.
- **Fixed `crack_affine` with non-alpha input**: Previously returned 312 spurious candidates when given text with no alphabetic characters (e.g., `"123!@#"`). Now returns an empty list.
- **Added 11 new tests**: Runic passthrough for all cipher functions, accented letter passthrough, Unicode crash prevention, non-alpha crack_affine, and frequency analysis Unicode handling.

### v2.0.2 — Bug Hunt Fixes (2026-06-12)
- **Fixed `crack_vigenere` short-text marker**: Changed `<short>` to `<too-short>` to avoid confusion with a real decryption key.
- **Fixed `combined_score` punctuation handling**: Words with trailing punctuation (e.g., `"mat."`) now correctly match common words like `"mat"` by stripping punctuation before comparison.
- **Fixed `analyze_frequency` IoC edge case**: Made the division-by-zero guard for `total <= 1` explicit with a clear `if/else` block instead of a ternary that relied on Python's `0/0 → 0.0` behavior.

### v2.0.1 — Bug Fixes
- **Fixed crack_caesar for short texts**: Improved combined scoring with normalized frequency (divides by √N to reduce small-sample bias), common English word matching, and trigram analysis. "khoor zruog" now correctly decrypts to "hello world" as the top candidate.
- **Fixed interactive mode atbash/rot13 decrypt**: Removed redundant double-encryption code that overwrote the result with the same computation. Both ciphers are self-inverse, so encrypt and decrypt produce the same result.
- **Fixed README examples**: Corrected XOR cipher output (was `02 00 0c 0c 06`, should be `05 1c 07 09 16` for key "mykey"), substitution key example (was `runeahijlmopqstuvwxfz`, should be `runeabcdfghijklmopqstvwxyz`), and Vigenère crack example.
- **Added 3 new tests**: Short-text Caesar cracking, XOR round-trip with special characters, and Caesar with large keys.