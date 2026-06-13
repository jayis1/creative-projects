#!/usr/bin/env python3
"""
Rune Cipher — A terminal cryptography playground.

Encode messages with historical ciphers, render them in runic Unicode,
and crack them with frequency analysis. Supports Caesar, Vigenère,
Substitution, Atbash, ROT13, Affine, and XOR ciphers.

Usage:
    python3 rune_cipher.py encrypt --cipher caesar --key 3 --text "hello world"
    python3 rune_cipher.py encrypt --cipher vigenere --key secret --text "attack at dawn"
    python3 rune_cipher.py encrypt --cipher atbash --text "abcxyz"
    python3 rune_cipher.py decrypt --cipher caesar --key 3 --text "khoor zruog"
    python3 rune_cipher.py crack --cipher caesar --text "khoor zruog"
    python3 rune_cipher.py crack --cipher substitution --text "xktlx wztlx"
    python3 rune_cipher.py interactive
    python3 rune_cipher.py analyze --text "khoor zruog"
    python3 rune_cipher.py runes --text "hello world"
"""

import argparse
import json
import math
import os
import random
import re
import sys
import string
import textwrap
from collections import Counter
from pathlib import Path

__version__ = "2.0.3"

# ── Runic Unicode mapping ──────────────────────────────────────────────────────
# Elder Futhark runic alphabet (24 runes) + extensions for full Latin coverage
RUNE_MAP = {
    'a': 'ᚨ', 'b': 'ᛒ', 'c': 'ᚲ', 'd': 'ᛞ', 'e': 'ᛖ',
    'f': 'ᚠ', 'g': 'ᚷ', 'h': 'ᚺ', 'i': 'ᛁ', 'j': 'ᛃ',
    'k': 'ᚴ', 'l': 'ᛚ', 'm': 'ᛗ', 'n': 'ᚾ', 'o': 'ᛟ',
    'p': 'ᛈ', 'q': 'ᛩ', 'r': 'ᚱ', 's': 'ᛋ', 't': 'ᛏ',
    'u': 'ᚢ', 'v': 'ᚡ', 'w': 'ᚹ', 'x': 'ᛪ', 'y': 'ᛦ',
    'z': 'ᛉ',
}

RUNE_SPACE = '᛬'

# Reverse map for rune-to-text conversion (precomputed for performance)
RUNE_REVERSE = {v: k for k, v in RUNE_MAP.items()}
RUNE_REVERSE[RUNE_SPACE] = ' '

# English letter frequency (approximate, from corpus analysis)
ENGLISH_FREQ = {
    'e': 12.7, 't': 9.1, 'a': 8.2, 'o': 7.5, 'i': 7.0,
    'n': 6.7, 's': 6.3, 'h': 6.1, 'r': 6.0, 'd': 4.3,
    'l': 4.0, 'c': 2.8, 'u': 2.8, 'm': 2.4, 'w': 2.4,
    'f': 2.2, 'g': 2.0, 'y': 2.0, 'p': 1.9, 'b': 1.5,
    'v': 1.0, 'k': 0.8, 'j': 0.2, 'x': 0.2, 'q': 0.1,
    'z': 0.1,
}

# Common English bigrams for scoring
COMMON_BIGRAMS = {'th', 'he', 'in', 'er', 'an', 'on', 'en', 'at',
                  'es', 'ed', 'or', 'te', 'of', 'nd', 'to', 'st',
                  'al', 'ar', 'ng', 'se', 'ha', 'as', 'ou', 'io',
                  'le', 've', 'co', 'me', 'de', 'hi', 'ri', 'ro',
                  'ic', 'ne', 'ea', 'ra', 'ce'}

# Common English trigrams for enhanced scoring
COMMON_TRIGRAMS = {'the', 'and', 'ing', 'her', 'hat', 'his', 'tha',
                   'ere', 'for', 'ent', 'ion', 'ter', 'was', 'you',
                   'ith', 'ver', 'all', 'not', 'tion', 'ate'}

# Integers coprime with 26 (valid 'a' values for affine cipher)
AFFINE_VALID_A = [a for a in range(1, 26) if math.gcd(a, 26) == 1]

# Interesting cryptography facts used by the 'random' command
FUN_FACTS = [
    "the quick brown fox jumps over the lazy dog",
    "cryptography is the practice and study of techniques for secure communication",
    "the enigma machine was used by nazi germany to protect communications",
    "alan turing helped crack the enigma code during world war two",
    "julius caesar used a simple shift cipher for military messages",
    "the vigenere cipher was called the indecipherable cipher for three centuries",
    "frequency analysis was first described by al kindi in the ninth century",
    "ancient spartans used a scytale a cylinder wrapped with a strip of parchment",
    "the affine cipher uses modular arithmetic with two keys for extra security",
    "xor encryption is the foundation of many modern stream ciphers",
    "a one time pad is theoretically unbreakable if used correctly",
    "the beale ciphers remain unsolved to this day despite many attempts",
]

BANNER = r"""
╦╔═╔═╗╔╦╗╔═╗╦ ╦╦  
╠╩╗║ ║║║║║╣ ║║║║  
╩ ╩╚═╝╩ ╩╚═╝╚╩╝╩═╝
    C I P H E R
"""

DIVIDER = "─" * 52

# ── Runic conversion ────────────────────────────────────────────────────────────

def text_to_runes(text: str) -> str:
    """Convert ASCII text to runic characters.
    
    Maps a-z to Elder Futhark runes, spaces to ᛬, and preserves
    newlines. All other characters pass through unchanged.
    
    Args:
        text: ASCII text to convert.
        
    Returns:
        String with letters replaced by runic equivalents.
    """
    result = []
    for ch in text.lower():
        if ch in RUNE_MAP:
            result.append(RUNE_MAP[ch])
        elif ch == ' ':
            result.append(RUNE_SPACE)
        elif ch == '\n':
            result.append('\n')
        else:
            result.append(ch)
    return ''.join(result)


def runes_to_text(runes: str) -> str:
    """Convert runic characters back to ASCII text.
    
    Args:
        runes: String containing runic characters.
        
    Returns:
        Decoded ASCII text.
    """
    result = []
    for ch in runes:
        if ch in RUNE_REVERSE:
            result.append(RUNE_REVERSE[ch])
        elif ch == '\n':
            result.append('\n')
        else:
            result.append(ch)
    return ''.join(result)


# ── Ciphers ─────────────────────────────────────────────────────────────────────

def caesar_encrypt(text: str, key: int) -> str:
    """Encrypt with Caesar cipher (shift cipher).
    
    Args:
        text: Plaintext to encrypt.
        key: Shift value (0-25). Can be negative for decryption.
        
    Returns:
        Encrypted ciphertext.
    """
    if not text:
        return ""
    result = []
    for ch in text.lower():
        if 'a' <= ch <= 'z':
            shifted = chr((ord(ch) - ord('a') + key) % 26 + ord('a'))
            result.append(shifted)
        else:
            result.append(ch)
    return ''.join(result)


def caesar_decrypt(text: str, key: int) -> str:
    """Decrypt Caesar cipher by shifting backwards.
    
    Args:
        text: Ciphertext to decrypt.
        key: The shift key that was used for encryption.
        
    Returns:
        Decrypted plaintext.
    """
    return caesar_encrypt(text, -key)


def vigenere_encrypt(text: str, key: str) -> str:
    """Encrypt with Vigenère cipher.
    
    Args:
        text: Plaintext to encrypt.
        key: Keyword (letters only). Must be at least 1 character.
        
    Returns:
        Encrypted ciphertext.
        
    Raises:
        ValueError: If key contains no alphabetic characters.
    """
    key = ''.join(ch for ch in key.lower() if ch.isalpha())
    if not key:
        raise ValueError("Vigenère key must contain at least one letter.")
    result = []
    ki = 0
    for ch in text.lower():
        if 'a' <= ch <= 'z':
            shift = ord(key[ki % len(key)]) - ord('a')
            result.append(chr((ord(ch) - ord('a') + shift) % 26 + ord('a')))
            ki += 1
        else:
            result.append(ch)
    return ''.join(result)


def vigenere_decrypt(text: str, key: str) -> str:
    """Decrypt Vigenère cipher.
    
    Args:
        text: Ciphertext to decrypt.
        key: The keyword that was used for encryption.
        
    Returns:
        Decrypted plaintext.
    """
    key = ''.join(ch for ch in key.lower() if ch.isalpha())
    if not key:
        raise ValueError("Vigenère key must contain at least one letter.")
    result = []
    ki = 0
    for ch in text.lower():
        if 'a' <= ch <= 'z':
            shift = ord(key[ki % len(key)]) - ord('a')
            result.append(chr((ord(ch) - ord('a') - shift) % 26 + ord('a')))
            ki += 1
        else:
            result.append(ch)
    return ''.join(result)


def atbash_encrypt(text: str) -> str:
    """Atbash cipher: A↔Z, B↔Y, etc. Encryption = decryption.
    
    Args:
        text: Text to encrypt/decrypt.
        
    Returns:
        Transformed text.
    """
    result = []
    for ch in text.lower():
        if 'a' <= ch <= 'z':
            result.append(chr(ord('z') - (ord(ch) - ord('a'))))
        else:
            result.append(ch)
    return ''.join(result)


def rot13_encrypt(text: str) -> str:
    """ROT13 cipher (Caesar with key 13). Self-inverse.
    
    Args:
        text: Text to transform.
        
    Returns:
        Transformed text.
    """
    return caesar_encrypt(text, 13)


def substitution_encrypt(text: str, key: str) -> str:
    """Encrypt with simple substitution cipher using a 26-char key.
    
    The key must be a permutation of all 26 lowercase letters.
    For keyword-based keys, use generate_keyword_key() first.
    
    Args:
        text: Plaintext to encrypt.
        key: 26-character substitution alphabet.
        
    Returns:
        Encrypted ciphertext.
        
    Raises:
        ValueError: If key is not a valid 26-letter permutation.
    """
    if not text:
        return ""
    key = key.lower()
    if len(key) != 26 or len(set(key)) != 26 or not all(ch.isalpha() for ch in key):
        raise ValueError("Substitution key must be 26 unique letters.")
    result = []
    for ch in text.lower():
        if 'a' <= ch <= 'z':
            result.append(key[ord(ch) - ord('a')])
        else:
            result.append(ch)
    return ''.join(result)


def substitution_decrypt(text: str, key: str) -> str:
    """Decrypt simple substitution cipher.
    
    Args:
        text: Ciphertext to decrypt.
        key: The 26-character substitution alphabet used for encryption.
        
    Returns:
        Decrypted plaintext.
    """
    key = key.lower()
    if len(key) != 26 or len(set(key)) != 26 or not all(ch.isalpha() for ch in key):
        raise ValueError("Substitution key must be 26 unique letters.")
    reverse = {key[i]: chr(ord('a') + i) for i in range(26)}
    result = []
    for ch in text.lower():
        if ch in reverse:
            result.append(reverse[ch])
        else:
            result.append(ch)
    return ''.join(result)


def affine_encrypt(text: str, a: int, b: int) -> str:
    """Encrypt with Affine cipher: E(x) = (ax + b) mod 26.
    
    Args:
        text: Plaintext to encrypt.
        a: Multiplicative key (must be coprime with 26).
        b: Additive key (0-25).
        
    Returns:
        Encrypted ciphertext.
        
    Raises:
        ValueError: If 'a' is not coprime with 26 or b is out of range.
    """
    if not text:
        return ""
    if math.gcd(a, 26) != 1:
        raise ValueError(f"Affine key 'a'={a} is not coprime with 26. Valid values: {AFFINE_VALID_A}")
    if not (0 <= b <= 25):
        raise ValueError(f"Affine key 'b' must be 0-25, got {b}.")
    result = []
    for ch in text.lower():
        if 'a' <= ch <= 'z':
            x = ord(ch) - ord('a')
            enc = (a * x + b) % 26
            result.append(chr(enc + ord('a')))
        else:
            result.append(ch)
    return ''.join(result)


def affine_decrypt(text: str, a: int, b: int) -> str:
    """Decrypt Affine cipher: D(x) = a_inv * (x - b) mod 26.
    
    Args:
        text: Ciphertext to decrypt.
        a: Multiplicative key (must be coprime with 26).
        b: Additive key (0-25).
        
    Returns:
        Decrypted plaintext.
    """
    if not text:
        return ""
    if math.gcd(a, 26) != 1:
        raise ValueError(f"Affine key 'a'={a} is not coprime with 26. Valid values: {AFFINE_VALID_A}")
    # Find modular inverse of a mod 26
    a_inv = pow(a, -1, 26)
    result = []
    for ch in text.lower():
        if 'a' <= ch <= 'z':
            x = ord(ch) - ord('a')
            dec = (a_inv * (x - b)) % 26
            result.append(chr(dec + ord('a')))
        else:
            result.append(ch)
    return ''.join(result)


def xor_encrypt(text: str, key: str) -> str:
    """Encrypt/decrypt with XOR cipher using a text key.
    
    XOR cipher is symmetric — encrypting again with the same key decrypts.
    Output is hex-encoded for safe display (non-printable chars avoided).
    
    Args:
        text: Text to encrypt.
        key: Key string (at least 1 character).
        
    Returns:
        Hex-encoded XOR result.
        
    Raises:
        ValueError: If key is empty.
    """
    if not key:
        raise ValueError("XOR key must not be empty.")
    if not text:
        return ""
    result = []
    for i, ch in enumerate(text):
        xored = ord(ch) ^ ord(key[i % len(key)])
        result.append(f"{xored:02x}")
    return ' '.join(result)


def xor_decrypt(hex_text: str, key: str) -> str:
    """Decrypt XOR cipher from hex-encoded ciphertext.
    
    Args:
        hex_text: Space-separated hex values from xor_encrypt.
        key: The key that was used for encryption.
        
    Returns:
        Decrypted plaintext.
        
    Raises:
        ValueError: If hex format is invalid.
    """
    if not key:
        raise ValueError("XOR key must not be empty.")
    if not hex_text.strip():
        return ""
    try:
        values = [int(h, 16) for h in hex_text.split()]
    except ValueError:
        raise ValueError("XOR ciphertext must be space-separated hex values (e.g., '1a 2b 3c').")
    result = []
    for i, val in enumerate(values):
        ch = chr(val ^ ord(key[i % len(key)]))
        result.append(ch)
    return ''.join(result)


def random_substitution_key() -> str:
    """Generate a random substitution cipher key.
    
    Returns:
        A random permutation of the 26 lowercase letters.
    """
    alpha = list(string.ascii_lowercase)
    random.shuffle(alpha)
    return ''.join(alpha)


def generate_keyword_key(keyword: str) -> str:
    """Generate a substitution key from a keyword (keyword cipher).
    
    The keyword letters come first (duplicates removed), then remaining
    alphabet letters in order.
    
    Args:
        keyword: A word or phrase to build the key from.
        
    Returns:
        A 26-character substitution alphabet derived from the keyword.
    """
    keyword = keyword.lower()
    seen = set()
    key = []
    for ch in keyword:
        if ch.isalpha() and ch not in seen:
            key.append(ch)
            seen.add(ch)
    for ch in string.ascii_lowercase:
        if ch not in seen:
            key.append(ch)
    return ''.join(key)


# ── Cracking / Frequency Analysis ─────────────────────────────────────────────

def frequency_score(text: str) -> float:
    """Score text by how closely its letter frequency matches English.
    
    Uses chi-squared distance from expected English letter frequencies.
    Lower score = better match.
    
    Args:
        text: Text to score.
        
    Returns:
        Chi-squared frequency distance score.
    """
    text = text.lower()
    letters = [ch for ch in text if 'a' <= ch <= 'z']
    if not letters:
        return float('inf')
    total = len(letters)
    counts = Counter(letters)
    score = 0.0
    for letter, expected_freq in ENGLISH_FREQ.items():
        actual_freq = (counts.get(letter, 0) / total) * 100
        score += (actual_freq - expected_freq) ** 2
    return score


def bigram_score(text: str) -> float:
    """Score text by how many common English bigrams it contains.
    
    Higher score = more English-like text.
    
    Args:
        text: Text to score.
        
    Returns:
        Count of common English bigrams found.
    """
    text = text.lower()
    letters = [ch for ch in text if 'a' <= ch <= 'z']
    if len(letters) < 2:
        return 0
    bigrams = [''.join(letters[i:i+2]) for i in range(len(letters) - 1)]
    return sum(1 for b in bigrams if b in COMMON_BIGRAMS)


def combined_score(text: str) -> float:
    """Combined scoring: normalized frequency + bigrams + trigrams + common words.
    
    Uses normalized frequency (divided by sqrt of text length) to reduce
    small-sample bias, plus bonuses for common English bigrams, trigrams,
    and words. Lower score = more English-like.
    
    Args:
        text: Text to score.
        
    Returns:
        Combined score (lower = more English-like).
    """
    text_lower = text.lower()
    letters = [ch for ch in text_lower if 'a' <= ch <= 'z']
    if not letters:
        return float('inf')
    
    total = len(letters)
    counts = Counter(letters)
    
    # Frequency score normalized by sqrt(N) to reduce small-sample bias
    freq_score = 0.0
    for letter, expected_freq in ENGLISH_FREQ.items():
        actual_freq = (counts.get(letter, 0) / total) * 100
        freq_score += (actual_freq - expected_freq) ** 2
    normalized_freq = freq_score / math.sqrt(total)
    
    # Bigram and trigram bonuses
    bigram_count = bigram_score(text)
    trigrams = [''.join(letters[i:i+3]) for i in range(len(letters) - 2)]
    trigram_count = sum(1 for t in trigrams if t in COMMON_TRIGRAMS)
    
    # Common word matching — very effective for short texts
    # Fix: strip punctuation from words so "mat." matches "mat"
    words = [w.strip('.,!?;:\'"()') for w in text_lower.split()]
    common_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all',
                    'can', 'her', 'was', 'one', 'our', 'out', 'has', 'had',
                    'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see',
                    'way', 'who', 'did', 'get', 'let', 'say', 'she', 'too',
                    'use', 'at', 'be', 'by', 'he', 'in', 'is', 'it', 'of',
                    'on', 'or', 'so', 'to', 'up', 'we', 'an', 'do', 'if',
                    'me', 'my', 'no', 'as', 'am', 'go', 'a', 'i', 'world',
                    'hello', 'from', 'this', 'that', 'with', 'they', 'have',
                    'been', 'would', 'make', 'like', 'time', 'just', 'know',
                    'take', 'into', 'over', 'good', 'some', 'could'}
    word_count = sum(1 for w in words if w in common_words)
    
    return normalized_freq - bigram_count * 4 - trigram_count * 8 - word_count * 30


def crack_caesar(ciphertext: str) -> list:
    """Try all 25 shifts and return candidates sorted by English-likeness.
    
    Args:
        ciphertext: The Caesar-encrypted text to crack.
        
    Returns:
        List of (key, plaintext) tuples, best match first.
    """
    if not ciphertext.strip():
        return []
    candidates = []
    for key in range(1, 26):
        decrypted = caesar_decrypt(ciphertext, key)
        score = combined_score(decrypted)
        candidates.append((key, decrypted, score))
    candidates.sort(key=lambda x: x[2])
    return [(k, d) for k, d, _ in candidates]


def crack_vigenere(ciphertext: str, max_key_len: int = 10) -> list:
    """Attempt to crack Vigenère cipher using Kasiski-like analysis.
    
    Uses Index of Coincidence to guess key length, then frequency
    analysis per column to recover each key letter.
    
    Args:
        ciphertext: The Vigenère-encrypted text to crack.
        max_key_len: Maximum key length to try.
        
    Returns:
        List of (key, decrypted_text) candidates, best match first.
    """
    ciphertext_clean = ''.join(ch for ch in ciphertext.lower() if 'a' <= ch <= 'z')
    if len(ciphertext_clean) < 12:
        # Fix: return an informative marker instead of the original ciphertext,
        # so users don't confuse it with a successful decryption
        return [("<too-short>", ciphertext)]
    
    def find_key_length_candidates(text, max_len):
        """Use Index of Coincidence to find likely key lengths."""
        scores = {}
        for kl in range(2, min(max_len + 1, len(text) // 3 + 1)):
            groups = ['' for _ in range(kl)]
            for i, ch in enumerate(text):
                groups[i % kl] += ch
            total_ic = 0
            valid_groups = 0
            for g in groups:
                n = len(g)
                if n < 2:
                    continue
                counts = Counter(g)
                ic = sum(c * (c - 1) for c in counts.values()) / (n * (n - 1))
                total_ic += ic
                valid_groups += 1
            if valid_groups > 0:
                avg_ic = total_ic / valid_groups
                # English IC is ~0.0667; score by closeness to that
                scores[kl] = abs(avg_ic - 0.0667)
        # Sort by closeness to English IC (lower = better)
        return sorted(scores.keys(), key=lambda k: scores[k])
    
    key_lengths = find_key_length_candidates(ciphertext_clean, max_key_len)
    candidates = []
    
    for kl in key_lengths[:4]:  # Try top 4 key length candidates
        key_chars = []
        for pos in range(kl):
            group = ciphertext_clean[pos::kl]
            best_shift = 0
            best_score = float('inf')
            for shift in range(26):
                shifted = caesar_encrypt(group, -shift)
                s = frequency_score(shifted)
                if s < best_score:
                    best_score = s
                    best_shift = shift
            key_chars.append(chr(best_shift + ord('a')))
        key = ''.join(key_chars)
        decrypted = vigenere_decrypt(ciphertext, key)
        score = combined_score(decrypted)
        candidates.append((key, decrypted, score))
    
    candidates.sort(key=lambda x: x[2])
    return [(k, d) for k, d, _ in candidates]


def crack_substitution(ciphertext: str, iterations: int = 500) -> list:
    """Hill-climbing attack on simple substitution cipher.
    
    Uses multiple random restarts with swap-based hill climbing,
    scored by combined frequency and bigram analysis.
    
    Args:
        ciphertext: Substitution-encrypted text to crack.
        iterations: Max iterations per restart.
        
    Returns:
        Top 3 (key, plaintext) candidates.
    """
    ciphertext_clean = ''.join(ch for ch in ciphertext.lower() if 'a' <= ch <= 'z')
    if len(ciphertext_clean) < 10:
        return [("<too short>", ciphertext)]
    
    best_overall = []
    
    for restart in range(8):  # Multiple restarts
        key = list(string.ascii_lowercase)
        random.shuffle(key)
        current_key = ''.join(key)
        current_text = substitution_decrypt(ciphertext, current_key)
        current_score = combined_score(current_text)
        
        improved = True
        iters = 0
        while improved and iters < iterations:
            improved = False
            for _ in range(200):
                # Swap two random positions
                a, b = random.sample(range(26), 2)
                new_key = list(current_key)
                new_key[a], new_key[b] = new_key[b], new_key[a]
                new_key = ''.join(new_key)
                new_text = substitution_decrypt(ciphertext, new_key)
                new_score = combined_score(new_text)
                if new_score < current_score:
                    current_key = new_key
                    current_score = new_score
                    current_text = new_text
                    improved = True
            iters += 1
        
        best_overall.append((current_key, current_text, current_score))
    
    best_overall.sort(key=lambda x: x[2])
    return [(k, d) for k, d, _ in best_overall[:3]]


def crack_affine(ciphertext: str) -> list:
    """Brute-force crack Affine cipher by trying all valid (a, b) pairs.
    
    Args:
        ciphertext: Affine-encrypted text to crack.
        
    Returns:
        List of (a, b, plaintext) tuples sorted by English-likeness.
    """
    if not ciphertext.strip():
        return []
    # Skip if text has no ASCII letters (nothing meaningful to crack)
    if not any('a' <= ch <= 'z' for ch in ciphertext.lower()):
        return []
    candidates = []
    for a in AFFINE_VALID_A:
        for b in range(26):
            try:
                decrypted = affine_decrypt(ciphertext, a, b)
                score = combined_score(decrypted)
                candidates.append((a, b, decrypted, score))
            except (ValueError, ZeroDivisionError):
                continue
    candidates.sort(key=lambda x: x[3])
    return [(a, b, d) for a, b, d, _ in candidates[:10]]


# ── Frequency Analysis ──────────────────────────────────────────────────────────

def analyze_frequency(text: str) -> dict:
    """Perform frequency analysis on text.
    
    Args:
        text: Text to analyze.
        
    Returns:
        Dictionary with letter frequencies, bigram counts, IoC, etc.
    """
    text = text.lower()
    letters = [ch for ch in text if 'a' <= ch <= 'z']
    if not letters:
        return {"error": "No alphabetic characters found."}
    
    total = len(letters)
    counts = Counter(letters)
    
    # Letter frequencies
    freq = {ch: round((counts.get(ch, 0) / total) * 100, 2) for ch in string.ascii_lowercase}
    
    # Index of Coincidence
    # Fix: handle edge case where n <= 1 (division by zero in n*(n-1))
    if total > 1:
        ic = sum(c * (c - 1) for c in counts.values()) / (total * (total - 1))
    else:
        ic = 0.0
    
    # Bigrams
    bigrams = [''.join(letters[i:i+2]) for i in range(len(letters) - 1)]
    bigram_counts = Counter(bigrams)
    top_bigrams = bigram_counts.most_common(10)
    
    # Trigrams
    trigrams = [''.join(letters[i:i+3]) for i in range(len(letters) - 2)]
    trigram_counts = Counter(trigrams)
    top_trigrams = trigram_counts.most_common(10)
    
    # Chi-squared against English
    chi_sq = sum((freq.get(ch, 0) - ENGLISH_FREQ.get(ch, 0)) ** 2 / max(ENGLISH_FREQ.get(ch, 0), 0.01)
                 for ch in string.ascii_lowercase)
    
    # Most common letters
    most_common = counts.most_common(5)
    
    return {
        "total_letters": total,
        "letter_frequencies": freq,
        "index_of_coincidence": round(ic, 4),
        "chi_squared_vs_english": round(chi_sq, 2),
        "most_common_letters": most_common,
        "top_bigrams": top_bigrams,
        "top_trigrams": top_trigrams,
        "english_likelihood": "High" if ic > 0.06 else "Medium" if ic > 0.04 else "Low",
    }


def format_analysis(analysis: dict) -> str:
    """Format frequency analysis results for display.
    
    Args:
        analysis: Output from analyze_frequency().
        
    Returns:
        Formatted string for terminal display.
    """
    if "error" in analysis:
        return f"  ⚠ {analysis['error']}"
    
    lines = []
    lines.append(DIVIDER)
    lines.append("  📊 FREQUENCY ANALYSIS")
    lines.append(DIVIDER)
    lines.append(f"  Total letters: {analysis['total_letters']}")
    lines.append(f"  Index of Coincidence: {analysis['index_of_coincidence']:.4f} (English ≈ 0.0667)")
    lines.append(f"  Chi-squared vs English: {analysis['chi_squared_vs_english']}")
    lines.append(f"  English likelihood: {analysis['english_likelihood']}")
    lines.append("")

    # Letter frequency chart
    lines.append("  Letter frequencies:")
    freq = analysis['letter_frequencies']
    max_freq = max(freq.values()) if freq else 1
    bar_width = 30
    for ch in sorted(freq, key=freq.get, reverse=True)[:10]:
        bar_len = int(freq[ch] / max_freq * bar_width)
        expected = ENGLISH_FREQ.get(ch, 0)
        lines.append(f"    {ch}: {freq[ch]:5.1f}% {'█' * bar_len} (EN: {expected:.1f}%)")
    lines.append("")
    
    lines.append(f"  Most common letters: {', '.join(f'{ch}({n})' for ch, n in analysis['most_common_letters'])}")
    lines.append(f"  Top bigrams: {', '.join(f'{bg}({n})' for bg, n in analysis['top_bigrams'][:5])}")
    if analysis['top_trigrams']:
        lines.append(f"  Top trigrams: {', '.join(f'{tg}({n})' for tg, n in analysis['top_trigrams'][:5])}")
    lines.append(DIVIDER)
    
    return '\n'.join(lines)


# ── Display helpers ────────────────────────────────────────────────────────────

def print_runic_box(text: str, title: str = ""):
    """Print text in a runic-styled box.
    
    Args:
        text: Text to display (will be converted to runes).
        title: Optional title for the box.
    """
    rune_text = text_to_runes(text)
    lines = rune_text.split('\n')
    max_len = max(len(line) for line in lines) if lines else 0
    width = max(max_len + 4, 40)
    
    print(f"  ╔{'═' * width}╗")
    if title:
        print(f"  ║  {title.center(width - 2)}  ║")
        print(f"  ╠{'═' * width}╣")
    for line in lines:
        print(f"  ║  {line.ljust(width - 2)}  ║")
    print(f"  ╚{'═' * width}╝")


def print_candidates(candidates: list, cipher_name: str, show_key: bool = True):
    """Print cracking candidates nicely.
    
    Args:
        candidates: List of candidate tuples from a crack function.
        cipher_name: Name of the cipher being cracked.
        show_key: Whether to display the key for each candidate.
    """
    print(f"\n🔍 Cracking {cipher_name} — Top candidates:\n")
    for i, item in enumerate(candidates):
        if len(item) == 2:
            key, plaintext = item
            if show_key:
                print(f"  [{i+1}] Key: {key}")
        elif len(item) == 3:
            # Affine: (a, b, plaintext)
            key, _, plaintext = item
            if show_key:
                print(f"  [{i+1}] Key (a={item[0]}, b={item[1]})")
        else:
            key, plaintext = item[0], item[1]
            if show_key:
                print(f"  [{i+1}] Key: {key}")
        print(f"      Plaintext: {plaintext}")
        print(f"      Runes:     {text_to_runes(plaintext)}")
        print()


# ── File I/O ────────────────────────────────────────────────────────────────────

def read_input(filepath: str) -> str:
    """Read text from a file.
    
    Args:
        filepath: Path to the file to read.
        
    Returns:
        File contents as a string.
        
    Raises:
        FileNotFoundError: If the file doesn't exist.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    return path.read_text(encoding='utf-8')


def write_output(filepath: str, content: str):
    """Write text to a file.
    
    Args:
        filepath: Path to write to.
        content: Text content to write.
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


# ── Interactive mode ────────────────────────────────────────────────────────────

def interactive():
    """Run an interactive cipher session with history and stats."""
    print(BANNER)
    print(f"  Rune Cipher v{__version__} — encode, decode, and crack ciphers!")
    print("  Type 'help' for commands, 'quit' to exit.\n")
    
    current_text = ""
    history = []  # Track all operations for the 'history' command
    
    while True:
        try:
            prompt = "rune ⟩ "
            cmd = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n  ✦ Farewell, cryptographer! ✦\n")
            break
        
        if not cmd:
            continue
        
        # Save to history
        history.append(cmd)
        
        parts = cmd.split(None, 1)
        action = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""
        
        if action in ('quit', 'exit', 'q'):
            print("\n  ✦ Farewell, cryptographer! ✦\n")
            break
        
        elif action == 'help':
            print(textwrap.dedent("""
                Commands:
                  encrypt <cipher> <key> <text>  — Encrypt text
                  decrypt <cipher> <key> <text>  — Decrypt text  
                  crack <cipher> <text>          — Crack ciphertext
                  runes <text>                    — Convert to runes
                  fromrunes <text>                — Convert from runes
                  stats [text]                    — Frequency analysis
                  random <cipher>                 — Encrypt random fact
                  history                         — Show command history
                  version                         — Show version
                  help                            — Show this help
                  quit                            — Exit
                
                Ciphers: caesar, vigenere, atbash, rot13, substitution, affine, xor
                
                Examples:
                  encrypt caesar 3 hello world
                  encrypt affine 5,8 secret message
                  decrypt vigenere secret jiqtg vjwv
                  crack caesar khoor zruog
                  runes attack at dawn
                  stats khoor zruog
            """))
        
        elif action == 'version':
            print(f"  Rune Cipher v{__version__}")
        
        elif action == 'history':
            if not history:
                print("  (no commands yet)")
            else:
                for i, h in enumerate(history[-20:], 1):  # Show last 20
                    print(f"  {i:3d}: {h}")
        
        elif action == 'runes':
            print(f"  ᛬ {text_to_runes(rest)}")
        
        elif action == 'fromrunes':
            print(f"  → {runes_to_text(rest)}")
        
        elif action == 'stats':
            # Frequency analysis of provided text or current text
            target = rest.strip() if rest.strip() else current_text
            if not target:
                print("  ⚠ No text to analyze. Encrypt/decrypt something first, or provide text.")
                continue
            analysis = analyze_frequency(target)
            print(format_analysis(analysis))
        
        elif action in ('encrypt', 'decrypt', 'crack'):
            sub = rest.split()
            if len(sub) < 1:
                print("  ⚠ Specify a cipher. Type 'help' for usage.")
                continue
            
            cipher = sub[0].lower()
            
            if action in ('encrypt', 'decrypt'):
                result = ""
                
                if cipher in ('atbash', 'rot13') and len(sub) >= 2:
                    text = ' '.join(sub[1:])
                    # Both atbash and rot13 are self-inverse, so encrypt == decrypt
                    if cipher == 'atbash':
                        result = atbash_encrypt(text)
                    else:
                        result = rot13_encrypt(text)
                    current_text = result
                    print_runic_box(result, f"{cipher.title()} — {action.title()}ed")
                    print(f"\n  ASCII: {result}")
                
                elif cipher == 'caesar' and len(sub) >= 3:
                    try:
                        key = int(sub[1])
                    except ValueError:
                        print("  ⚠ Caesar key must be a number.")
                        continue
                    text = ' '.join(sub[2:])
                    if action == 'encrypt':
                        result = caesar_encrypt(text, key)
                    else:
                        result = caesar_decrypt(text, key)
                    current_text = result
                    print_runic_box(result, f"Caesar (key={key}) — {action.title()}ed")
                    print(f"\n  ASCII: {result}")
                
                elif cipher == 'vigenere' and len(sub) >= 3:
                    key = sub[1]
                    text = ' '.join(sub[2:])
                    try:
                        if action == 'encrypt':
                            result = vigenere_encrypt(text, key)
                        else:
                            result = vigenere_decrypt(text, key)
                    except ValueError as e:
                        print(f"  ⚠ {e}")
                        continue
                    current_text = result
                    print_runic_box(result, f"Vigenère (key={key}) — {action.title()}ed")
                    print(f"\n  ASCII: {result}")
                
                elif cipher == 'substitution' and len(sub) >= 3:
                    key = sub[1]
                    text = ' '.join(sub[2:])
                    if len(key) != 26:
                        key = generate_keyword_key(key)
                    try:
                        if action == 'encrypt':
                            result = substitution_encrypt(text, key)
                        else:
                            result = substitution_decrypt(text, key)
                        current_text = result
                        print_runic_box(result, f"Substitution — {action.title()}ed")
                        print(f"\n  ASCII: {result}")
                        print(f"  Key: {key}")
                    except ValueError as e:
                        print(f"  ⚠ {e}")
                
                elif cipher == 'affine' and len(sub) >= 3:
                    # Parse key as "a,b"
                    try:
                        key_parts = sub[1].split(',')
                        a = int(key_parts[0])
                        b = int(key_parts[1]) if len(key_parts) > 1 else 0
                    except (ValueError, IndexError):
                        print("  ⚠ Affine key must be in format 'a,b' (e.g., '5,8').")
                        continue
                    text = ' '.join(sub[2:])
                    try:
                        if action == 'encrypt':
                            result = affine_encrypt(text, a, b)
                        else:
                            result = affine_decrypt(text, a, b)
                        current_text = result
                        print_runic_box(result, f"Affine (a={a}, b={b}) — {action.title()}ed")
                        print(f"\n  ASCII: {result}")
                    except ValueError as e:
                        print(f"  ⚠ {e}")
                
                elif cipher == 'xor' and len(sub) >= 3:
                    key = sub[1]
                    text = ' '.join(sub[2:])
                    try:
                        if action == 'encrypt':
                            result = xor_encrypt(text, key)
                        else:
                            result = xor_decrypt(text, key)
                        current_text = result
                        print(f"  XOR (key={key}) — {action.title()}ed:")
                        print(f"  {result}")
                    except ValueError as e:
                        print(f"  ⚠ {e}")
                
                else:
                    print(f"  ⚠ Invalid usage. Type 'help' for usage.")
            
            elif action == 'crack':
                if cipher == 'caesar':
                    text = ' '.join(sub[1:])
                    if not text.strip():
                        print("  ⚠ Provide ciphertext to crack.")
                        continue
                    candidates = crack_caesar(text)
                    print_candidates(candidates, "Caesar")
                    if candidates:
                        current_text = candidates[0][1]
                
                elif cipher == 'vigenere':
                    text = ' '.join(sub[1:])
                    if not text.strip():
                        print("  ⚠ Provide ciphertext to crack.")
                        continue
                    candidates = crack_vigenere(text)
                    print_candidates(candidates, "Vigenère")
                    if candidates:
                        current_text = candidates[0][1]
                
                elif cipher == 'substitution':
                    text = ' '.join(sub[1:])
                    if not text.strip():
                        print("  ⚠ Provide ciphertext to crack.")
                        continue
                    print("  ⏳ Hill-climbing attack in progress (this may take a moment)...")
                    candidates = crack_substitution(text)
                    print_candidates(candidates, "Substitution")
                    if candidates:
                        current_text = candidates[0][1]
                
                elif cipher == 'affine':
                    text = ' '.join(sub[1:])
                    if not text.strip():
                        print("  ⚠ Provide ciphertext to crack.")
                        continue
                    print("  ⏳ Brute-forcing all valid affine keys...")
                    candidates = crack_affine(text)
                    if candidates:
                        print_candidates(candidates[:5], "Affine")
                        current_text = candidates[0][2]
                    else:
                        print("  No valid candidates found.")
                
                elif cipher in ('atbash', 'rot13'):
                    text = ' '.join(sub[1:])
                    if cipher == 'atbash':
                        result = atbash_encrypt(text)
                    else:
                        result = rot13_encrypt(text)
                    print(f"\n  {cipher.title()} is its own inverse!")
                    print_runic_box(result, f"{cipher.title()} — Decrypted")
                    print(f"\n  ASCII: {result}")
                    current_text = result
                
                elif cipher == 'xor':
                    print("  ⚠ XOR ciphers cannot be cracked without the key (theoretically impossible without known plaintext).")
                
                else:
                    print(f"  ⚠ Unknown cipher: {cipher}")
        
        elif action == 'random':
            text = random.choice(FUN_FACTS)
            cipher = sub[0].lower() if sub else 'caesar'
            if cipher == 'caesar':
                key = random.randint(1, 25)
                result = caesar_encrypt(text, key)
                print(f"  📜 Random fact encrypted with Caesar (key={key}):")
            elif cipher == 'vigenere':
                key = random.choice(['secret', 'rune', 'cipher', 'magic', 'ancient'])
                result = vigenere_encrypt(text, key)
                print(f"  📜 Random fact encrypted with Vigenère (key={key}):")
            elif cipher == 'atbash':
                result = atbash_encrypt(text)
                print(f"  📜 Random fact encrypted with Atbash:")
            elif cipher == 'rot13':
                result = rot13_encrypt(text)
                print(f"  📜 Random fact encrypted with ROT13:")
            elif cipher == 'affine':
                a = random.choice(AFFINE_VALID_A)
                b = random.randint(0, 25)
                result = affine_encrypt(text, a, b)
                print(f"  📜 Random fact encrypted with Affine (a={a}, b={b}):")
            elif cipher == 'xor':
                key = random.choice(['key', 'rune', 'secret'])
                result = xor_encrypt(text, key)
                print(f"  📜 Random fact encrypted with XOR (key={key}):")
                print(f"  Hex: {result}")
                current_text = text  # Store plaintext for stats
                continue
            else:
                key = generate_keyword_key(random.choice(['rune', 'norse', 'viking']))
                result = substitution_encrypt(text, key)
                print(f"  📜 Random fact encrypted with Substitution (keyword key):")
            
            print_runic_box(result, "Ciphertext")
            print(f"\n  ASCII: {result}")
            current_text = result
        
        else:
            print(f"  ⚠ Unknown command: {action}. Type 'help' for commands.")


# ── CLI ─────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Rune Cipher — Terminal cryptography playground with runic rendering",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            Examples:
              rune_cipher.py encrypt --cipher caesar --key 3 --text "hello world"
              rune_cipher.py encrypt --cipher vigenere --key secret --text "attack at dawn"
              rune_cipher.py encrypt --cipher affine --key 5,8 --text "secret"
              rune_cipher.py encrypt --cipher xor --key mykey --text "hello"
              rune_cipher.py decrypt --cipher caesar --key 3 --text "khoor zruog"
              rune_cipher.py crack --cipher caesar --text "khoor zruog"
              rune_cipher.py crack --cipher vigenere --text "lxfopv frhsr"
              rune_cipher.py analyze --text "khoor zruog"
              rune_cipher.py interactive
              rune_cipher.py demo
              
            Supported ciphers: caesar, vigenere, atbash, rot13, substitution, affine, xor
        """)
    )
    parser.add_argument('--version', action='version', version=f'Rune Cipher v{__version__}')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # encrypt
    enc = subparsers.add_parser('encrypt', help='Encrypt text')
    enc.add_argument('--cipher', required=True,
                     choices=['caesar', 'vigenere', 'atbash', 'rot13', 'substitution', 'affine', 'xor'],
                     help='Cipher to use')
    enc.add_argument('--key', default='', help='Cipher key (number for caesar, a,b for affine, word for vigenere/substitution/xor)')
    enc.add_argument('--text', default='', help='Text to encrypt')
    enc.add_argument('--infile', default='', help='Read plaintext from file')
    enc.add_argument('--outfile', default='', help='Write ciphertext to file')
    enc.add_argument('--runic', action='store_true', help='Also display runic output')
    
    # decrypt
    dec = subparsers.add_parser('decrypt', help='Decrypt text')
    dec.add_argument('--cipher', required=True,
                    choices=['caesar', 'vigenere', 'atbash', 'rot13', 'substitution', 'affine', 'xor'],
                    help='Cipher to use')
    dec.add_argument('--key', default='', help='Cipher key')
    dec.add_argument('--text', default='', help='Text to decrypt')
    dec.add_argument('--infile', default='', help='Read ciphertext from file')
    dec.add_argument('--outfile', default='', help='Write plaintext to file')
    dec.add_argument('--runic', action='store_true', help='Also display runic output')
    
    # crack
    crk = subparsers.add_parser('crack', help='Crack ciphertext using frequency analysis')
    crk.add_argument('--cipher', required=True,
                    choices=['caesar', 'vigenere', 'substitution', 'atbash', 'rot13', 'affine'],
                    help='Cipher type to crack')
    crk.add_argument('--text', default='', help='Ciphertext to crack')
    crk.add_argument('--infile', default='', help='Read ciphertext from file')
    crk.add_argument('--top', type=int, default=5, help='Number of candidates to show (default: 5)')
    
    # analyze
    ana = subparsers.add_parser('analyze', help='Perform frequency analysis on text')
    ana.add_argument('--text', default='', help='Text to analyze')
    ana.add_argument('--infile', default='', help='Read text from file')
    
    # runes
    run = subparsers.add_parser('runes', help='Convert text to runic characters')
    run.add_argument('--text', required=True, help='Text to convert')
    
    # interactive
    subparsers.add_parser('interactive', help='Start interactive mode')
    
    # demo
    subparsers.add_parser('demo', help='Run a demo showing all ciphers')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Helper to get text from --text or --infile
    def get_text(args_obj):
        """Get text from --text flag or --infile flag, or stdin."""
        if hasattr(args_obj, 'infile') and args_obj.infile:
            try:
                return read_input(args_obj.infile)
            except FileNotFoundError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
        if hasattr(args_obj, 'text') and args_obj.text:
            return args_obj.text
        # Try reading from stdin if piped
        if not sys.stdin.isatty():
            return sys.stdin.read().strip()
        return ""
    
    if args.command == 'interactive':
        interactive()
        return
    
    if args.command == 'demo':
        print(BANNER)
        print(f"  Rune Cipher v{__version__} Demo\n")
        demo_text = "the ancient runes conceal great power"
        print(f"  Original: {demo_text}")
        print(f"  Runes:    {text_to_runes(demo_text)}\n")
        
        print(DIVIDER)
        print("  CAESAR CIPHER (key=7)")
        enc = caesar_encrypt(demo_text, 7)
        print(f"  Encrypted: {enc}")
        print(f"  As runes:  {text_to_runes(enc)}")
        print(f"  Decrypted: {caesar_decrypt(enc, 7)}\n")
        
        print(DIVIDER)
        print("  VIGENÈRE CIPHER (key='rune')")
        enc = vigenere_encrypt(demo_text, 'rune')
        print(f"  Encrypted: {enc}")
        print(f"  As runes:  {text_to_runes(enc)}")
        print(f"  Decrypted: {vigenere_decrypt(enc, 'rune')}\n")
        
        print(DIVIDER)
        print("  ATBASH CIPHER")
        enc = atbash_encrypt(demo_text)
        print(f"  Encrypted: {enc}")
        print(f"  As runes:  {text_to_runes(enc)}")
        print(f"  Decrypted: {atbash_encrypt(enc)}\n")
        
        print(DIVIDER)
        print("  ROT13 CIPHER")
        enc = rot13_encrypt(demo_text)
        print(f"  Encrypted: {enc}")
        print(f"  As runes:  {text_to_runes(enc)}")
        print(f"  Decrypted: {rot13_encrypt(enc)}\n")
        
        print(DIVIDER)
        print("  AFFINE CIPHER (a=5, b=8)")
        enc = affine_encrypt(demo_text, 5, 8)
        print(f"  Encrypted: {enc}")
        print(f"  As runes:  {text_to_runes(enc)}")
        print(f"  Decrypted: {affine_decrypt(enc, 5, 8)}\n")
        
        print(DIVIDER)
        print("  XOR CIPHER (key='rune')")
        enc = xor_encrypt(demo_text, 'rune')
        print(f"  Encrypted (hex): {enc}")
        dec = xor_decrypt(enc, 'rune')
        print(f"  Decrypted: {dec}\n")
        
        print(DIVIDER)
        print("  CRACKING DEMO — Caesar-encrypted ciphertext")
        ct = caesar_encrypt("attack the fortress at dawn", 11)
        print(f"  Ciphertext: {ct}")
        print(f"  Cracking...")
        candidates = crack_caesar(ct)
        for i, (key, plain) in enumerate(candidates[:3]):
            marker = " ← BEST" if i == 0 else ""
            print(f"    Key {key:2d}: {plain}{marker}")
        print()
        
        print(DIVIDER)
        print("  FREQUENCY ANALYSIS DEMO")
        analysis = analyze_frequency(caesar_encrypt("hello world this is a secret message", 7))
        print(format_analysis(analysis))
        return
    
    if args.command == 'runes':
        result = text_to_runes(args.text)
        print(result)
        return
    
    if args.command == 'analyze':
        text = get_text(args)
        if not text:
            print("Error: Provide text with --text or --infile.", file=sys.stderr)
            sys.exit(1)
        analysis = analyze_frequency(text)
        print(format_analysis(analysis))
        return
    
    if args.command == 'encrypt':
        cipher = args.cipher
        text = get_text(args)
        if not text:
            print("Error: Provide text with --text or --infile.", file=sys.stderr)
            sys.exit(1)
        
        if cipher == 'caesar':
            key = int(args.key) if args.key else 3
            result = caesar_encrypt(text, key)
        elif cipher == 'vigenere':
            key = args.key or 'secret'
            try:
                result = vigenere_encrypt(text, key)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
        elif cipher == 'atbash':
            result = atbash_encrypt(text)
        elif cipher == 'rot13':
            result = rot13_encrypt(text)
        elif cipher == 'substitution':
            key = args.key
            if len(key) != 26:
                key = generate_keyword_key(key)
            try:
                result = substitution_encrypt(text, key)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
            print(f"Substitution key: {key}")
        elif cipher == 'affine':
            try:
                key_parts = args.key.split(',') if args.key else '5,8'.split(',')
                a = int(key_parts[0])
                b = int(key_parts[1]) if len(key_parts) > 1 else 0
            except (ValueError, IndexError):
                print("Error: Affine key must be 'a,b' (e.g., '5,8').", file=sys.stderr)
                sys.exit(1)
            try:
                result = affine_encrypt(text, a, b)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
        elif cipher == 'xor':
            key = args.key
            if not key:
                print("Error: XOR cipher requires a --key.", file=sys.stderr)
                sys.exit(1)
            try:
                result = xor_encrypt(text, key)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
        
        print(f"Result: {result}")
        if args.runic and cipher != 'xor':
            print(f"Runes:  {text_to_runes(result)}")
        
        if args.outfile:
            write_output(args.outfile, result)
            print(f"Output written to: {args.outfile}")
    
    elif args.command == 'decrypt':
        cipher = args.cipher
        text = get_text(args)
        if not text:
            print("Error: Provide text with --text or --infile.", file=sys.stderr)
            sys.exit(1)
        
        if cipher == 'caesar':
            key = int(args.key) if args.key else 3
            result = caesar_decrypt(text, key)
        elif cipher == 'vigenere':
            key = args.key or 'secret'
            try:
                result = vigenere_decrypt(text, key)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
        elif cipher == 'atbash':
            result = atbash_encrypt(text)  # Atbash is its own inverse
        elif cipher == 'rot13':
            result = rot13_encrypt(text)  # ROT13 is its own inverse
        elif cipher == 'substitution':
            key = args.key
            if len(key) != 26:
                key = generate_keyword_key(key)
            try:
                result = substitution_decrypt(text, key)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
        elif cipher == 'affine':
            try:
                key_parts = args.key.split(',') if args.key else '5,8'.split(',')
                a = int(key_parts[0])
                b = int(key_parts[1]) if len(key_parts) > 1 else 0
            except (ValueError, IndexError):
                print("Error: Affine key must be 'a,b' (e.g., '5,8').", file=sys.stderr)
                sys.exit(1)
            try:
                result = affine_decrypt(text, a, b)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
        elif cipher == 'xor':
            key = args.key
            if not key:
                print("Error: XOR cipher requires a --key.", file=sys.stderr)
                sys.exit(1)
            try:
                result = xor_decrypt(text, key)
            except ValueError as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
        
        print(f"Result: {result}")
        if args.runic and cipher != 'xor':
            print(f"Runes:  {text_to_runes(result)}")
        
        if args.outfile:
            write_output(args.outfile, result)
            print(f"Output written to: {args.outfile}")
    
    elif args.command == 'crack':
        cipher = args.cipher
        text = get_text(args)
        if not text:
            print("Error: Provide text with --text or --infile.", file=sys.stderr)
            sys.exit(1)
        
        if cipher == 'caesar':
            candidates = crack_caesar(text)
            print(f"Top {min(args.top, len(candidates))} Caesar cipher candidates:\n")
            for i, (key, plain) in enumerate(candidates[:args.top]):
                marker = " ← BEST MATCH" if i == 0 else ""
                print(f"  Key {key:2d}: {plain}{marker}")
                print(f"         {text_to_runes(plain)}\n")
        
        elif cipher == 'vigenere':
            print("Cracking Vigenère cipher (Kasiski analysis)...\n")
            candidates = crack_vigenere(text)
            for i, (key, plain) in enumerate(candidates[:args.top]):
                marker = " ← BEST MATCH" if i == 0 else ""
                print(f"  Key \"{key}\": {plain}{marker}")
                print(f"           {text_to_runes(plain)}\n")
        
        elif cipher == 'substitution':
            print("Cracking substitution cipher (hill-climbing attack)...\n")
            candidates = crack_substitution(text)
            for i, (key, plain) in enumerate(candidates[:args.top]):
                marker = " ← BEST MATCH" if i == 0 else ""
                print(f"  Key: {key}")
                print(f"  Text: {plain}{marker}\n")
        
        elif cipher == 'affine':
            print("Cracking affine cipher (brute-force all valid keys)...\n")
            candidates = crack_affine(text)
            for i, (a, b, plain) in enumerate(candidates[:args.top]):
                marker = " ← BEST MATCH" if i == 0 else ""
                print(f"  Key (a={a}, b={b}): {plain}{marker}")
                print(f"                      {text_to_runes(plain)}\n")
        
        elif cipher in ('atbash', 'rot13'):
            if cipher == 'atbash':
                result = atbash_encrypt(text)
            else:
                result = rot13_encrypt(text)
            print(f"{cipher} is its own inverse!")
            print(f"Decrypted: {result}")
            print(f"Runes:     {text_to_runes(result)}")


if __name__ == '__main__':
    main()