#!/usr/bin/env python3
"""
Tests for rune_cipher — round-trip tests, rune conversion, edge cases,
and frequency analysis validation.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rune_cipher import (
    text_to_runes, runes_to_text,
    caesar_encrypt, caesar_decrypt,
    vigenere_encrypt, vigenere_decrypt,
    atbash_encrypt, rot13_encrypt,
    substitution_encrypt, substitution_decrypt,
    affine_encrypt, affine_decrypt,
    xor_encrypt, xor_decrypt,
    generate_keyword_key, random_substitution_key,
    frequency_score, bigram_score, combined_score,
    crack_caesar, crack_vigenere, crack_affine,
    analyze_frequency, format_analysis,
    AFFINE_VALID_A,
)


def test_rune_round_trip():
    """Text -> runes -> text should be identity."""
    samples = [
        "hello world",
        "the quick brown fox jumps over the lazy dog",
        "abcdefghijklmnopqrstuvwxyz",
        "attack at dawn",
    ]
    for s in samples:
        assert runes_to_text(text_to_runes(s)) == s, f"Round-trip failed for: {s}"


def test_rune_space():
    """Spaces should map to RUNE_SPACE and back."""
    assert text_to_runes("a b") == "ᚨ᛬ᛒ"
    assert runes_to_text("ᚨ᛬ᛒ") == "a b"


def test_rune_non_alpha():
    """Non-alpha, non-space characters should pass through unchanged."""
    assert text_to_runes("123!@#") == "123!@#"


def test_rune_empty():
    """Empty string should round-trip."""
    assert text_to_runes("") == ""
    assert runes_to_text("") == ""


def test_caesar_round_trip():
    """Caesar encrypt then decrypt should return original."""
    for key in [0, 1, 3, 13, 25]:
        plaintext = "hello world"
        assert caesar_decrypt(caesar_encrypt(plaintext, key), key) == plaintext


def test_caesar_known():
    """Test known Caesar ciphertexts."""
    assert caesar_encrypt("abc", 1) == "bcd"
    assert caesar_encrypt("xyz", 2) == "zab"
    assert caesar_encrypt("hello", 13) == "uryyb"


def test_caesar_preserves_non_alpha():
    """Caesar should preserve spaces and punctuation."""
    assert caesar_encrypt("hello, world!", 3) == "khoor, zruog!"


def test_caesar_empty():
    """Caesar with empty string should return empty string."""
    assert caesar_encrypt("", 5) == ""
    assert caesar_decrypt("", 5) == ""


def test_vigenere_round_trip():
    """Vigenère encrypt then decrypt should return original."""
    for key in ["a", "abc", "secret", "key"]:
        plaintext = "hello world"
        assert vigenere_decrypt(vigenere_encrypt(plaintext, key), key) == plaintext


def test_vigenere_known():
    """Test known Vigenère ciphertexts."""
    # Key 'a' is identity
    assert vigenere_encrypt("hello", "a") == "hello"
    # Key 'b' shifts each letter by 1
    assert vigenere_encrypt("abc", "b") == "bcd"


def test_vigenere_invalid_key():
    """Vigenère with no letters in key should raise ValueError."""
    try:
        vigenere_encrypt("hello", "123")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_atbash_round_trip():
    """Atbash is self-inverse: encrypt(encrypt(x)) == x."""
    for text in ["abc", "hello world", "zyxwvutsrqponmlkjihgfedcba"]:
        assert atbash_encrypt(atbash_encrypt(text)) == text


def test_atbash_known():
    """Test known Atbash mappings."""
    assert atbash_encrypt("abc") == "zyx"
    assert atbash_encrypt("hello") == "svool"


def test_rot13_round_trip():
    """ROT13 is self-inverse."""
    text = "hello world"
    assert rot13_encrypt(rot13_encrypt(text)) == text


def test_rot13_known():
    """Test known ROT13."""
    assert rot13_encrypt("hello") == "uryyb"


def test_substitution_round_trip():
    """Substitution encrypt then decrypt should return original."""
    key = random_substitution_key()
    plaintext = "hello world"
    assert substitution_decrypt(substitution_encrypt(plaintext, key), key) == plaintext


def test_substitution_keyword():
    """Test keyword-based key generation."""
    key = generate_keyword_key("rune")
    assert len(key) == 26
    assert len(set(key)) == 26
    assert key.startswith("rune")  # First 4 chars should be 'rune' (no duplicates)


def test_substitution_invalid_key():
    """Substitution with invalid key should raise ValueError."""
    try:
        substitution_encrypt("hello", "abc")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_affine_round_trip():
    """Affine encrypt then decrypt should return original."""
    for a in AFFINE_VALID_A[:5]:  # Test first 5 valid 'a' values
        for b in [0, 1, 5, 13, 25]:
            plaintext = "hello world"
            assert affine_decrypt(affine_encrypt(plaintext, a, b), a, b) == plaintext


def test_affine_known():
    """Test known Affine ciphertext (a=5, b=8, classic example)."""
    # E(0)=8='i', E(1)=13='n', etc.
    result = affine_encrypt("a", 5, 8)
    assert result == "i"


def test_affine_invalid_a():
    """Affine with a not coprime with 26 should raise ValueError."""
    for a in [2, 4, 6, 13, 26]:
        try:
            affine_encrypt("hello", a, 0)
            assert False, f"Should have raised ValueError for a={a}"
        except ValueError:
            pass


def test_xor_round_trip():
    """XOR encrypt then decrypt should return original."""
    for key in ["k", "key", "secret"]:
        plaintext = "hello world"
        encrypted = xor_encrypt(plaintext, key)
        decrypted = xor_decrypt(encrypted, key)
        assert decrypted == plaintext


def test_xor_empty():
    """XOR with empty text should return empty string."""
    assert xor_encrypt("", "key") == ""


def test_xor_invalid_key():
    """XOR with empty key should raise ValueError."""
    try:
        xor_encrypt("hello", "")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_crack_caesar():
    """Crack Caesar should find the correct key."""
    plaintext = "the quick brown fox jumps over the lazy dog"
    for key in [3, 7, 13, 20]:
        ciphertext = caesar_encrypt(plaintext, key)
        candidates = crack_caesar(ciphertext)
        assert candidates[0][0] == key, f"Expected key {key}, got {candidates[0][0]}"
        assert candidates[0][1] == plaintext


def test_crack_caesar_empty():
    """Crack Caesar with empty text should return empty list."""
    assert crack_caesar("") == []


def test_crack_affine():
    """Crack Affine should find correct (a, b) pair."""
    plaintext = "the quick brown fox jumps over the lazy dog"
    a, b = 5, 8
    ciphertext = affine_encrypt(plaintext, a, b)
    candidates = crack_affine(ciphertext)
    # Check that correct key is among top candidates
    found = any(cand_a == a and cand_b == b for cand_a, cand_b, _ in candidates)
    assert found, f"Expected (a={a}, b={b}) in candidates"


def test_frequency_score():
    """English text should have a lower frequency score than random text."""
    english = "the quick brown fox jumps over the lazy dog"
    # A shifted text should score worse
    shifted = caesar_encrypt(english, 13)
    assert frequency_score(english) < frequency_score(shifted)


def test_bigram_score():
    """English text should have more common bigrams than random text."""
    english = "the quick brown fox jumps over the lazy dog"
    shifted = caesar_encrypt(english, 13)
    assert bigram_score(english) > bigram_score(shifted)


def test_analyze_frequency():
    """Frequency analysis should return expected fields."""
    result = analyze_frequency("hello world")
    assert "total_letters" in result
    assert "letter_frequencies" in result
    assert "index_of_coincidence" in result
    assert "chi_squared_vs_english" in result
    assert "most_common_letters" in result
    assert "top_bigrams" in result
    assert result["total_letters"] == 10  # "helloworld" = 10 letters


def test_analyze_frequency_empty():
    """Frequency analysis with no letters should return error."""
    result = analyze_frequency("123!@#")
    assert "error" in result


def test_format_analysis():
    """format_analysis should produce a non-empty string."""
    result = analyze_frequency("the quick brown fox jumps over the lazy dog")
    formatted = format_analysis(result)
    assert len(formatted) > 0
    assert "FREQUENCY ANALYSIS" in formatted


def test_keyword_key_completeness():
    """generate_keyword_key should produce all 26 letters."""
    for keyword in ["a", "abc", "zebra", "crypto"]:
        key = generate_keyword_key(keyword)
        assert len(key) == 26
        assert len(set(key)) == 26
        assert set(key) == set("abcdefghijklmnopqrstuvwxyz")


def test_keyword_key_dedup():
    """generate_keyword_key should remove duplicate letters from keyword."""
    key = generate_keyword_key("hello")
    # 'h', 'e', 'l', 'l' -> 'h', 'e', 'l' (duplicate 'l' removed), then remaining
    assert key.startswith("helo")


def test_combined_score():
    """Combined score should favor English text over gibberish."""
    english = "this is a test of the emergency broadcast system"
    gibberish = "xyzqw jklmnb pqrstu vw"
    assert combined_score(english) < combined_score(gibberish)


def test_crack_caesar_short_text():
    """Crack Caesar should find correct key even for short text like 'khoor zruog'."""
    plaintext = "hello world"
    ciphertext = caesar_encrypt(plaintext, 3)
    candidates = crack_caesar(ciphertext)
    assert len(candidates) > 0, "Should return candidates"
    assert candidates[0][1] == plaintext, f"Best match should be '{plaintext}', got '{candidates[0][1]}'"


def test_xor_round_trip_special_chars():
    """XOR round-trip should work with special characters."""
    for text in ["hello!@#world", "café", "spaces and tabs\there", ""]:
        enc = xor_encrypt(text, "key")
        dec = xor_decrypt(enc, "key")
        assert dec == text, f"Round-trip failed for: {repr(text)}"


def test_caesar_large_key():
    """Caesar with keys > 25 should wrap correctly."""
    assert caesar_encrypt("hello", 26) == "hello"
    assert caesar_encrypt("hello", 52) == "hello"
    assert caesar_decrypt(caesar_encrypt("hello", 29), 29) == "hello"


# ── Unicode/Non-ASCII safety tests ──────────────────────────────────────────

def test_caesar_runic_passthrough():
    """Caesar cipher should pass runic characters through unchanged."""
    runic = text_to_runes("hello")
    result = caesar_encrypt(runic, 3)
    assert result == runic, f"Caesar should pass runes through, got {result!r}"

def test_caesar_accented_passthrough():
    """Caesar cipher should pass non-ASCII letters (é, ü, etc.) through unchanged."""
    result = caesar_encrypt("café", 3)
    # c->f, a->d, f->i, é passes through
    assert result == "fdié", f"Expected 'fdié', got {result!r}"

def test_vigenere_runic_passthrough():
    """Vigenère should pass runic characters through unchanged."""
    runic = text_to_runes("hello")
    result = vigenere_encrypt(runic, "key")
    assert result == runic, f"Vigenère should pass runes through, got {result!r}"

def test_atbash_runic_passthrough():
    """Atbash should pass runic characters through unchanged (no crash)."""
    runic = text_to_runes("hello")
    result = atbash_encrypt(runic)
    assert result == runic, f"Atbash should pass runes through, got {result!r}"

def test_atbash_accented_passthrough():
    """Atbash should pass non-ASCII letters through unchanged (no crash)."""
    result = atbash_encrypt("café")
    # c->x, a->z, f->u, é passes through
    assert result == "xzué", f"Expected 'xzué', got {result!r}"

def test_substitution_runic_passthrough():
    """Substitution should pass runic characters through unchanged (no crash)."""
    runic = text_to_runes("hello")
    result = substitution_encrypt(runic, "abcdefghijklmnopqrstuvwxyz")
    assert result == runic, f"Substitution should pass runes through, got {result!r}"

def test_affine_runic_passthrough():
    """Affine should pass runic characters through unchanged."""
    runic = text_to_runes("hello")
    result = affine_encrypt(runic, 5, 8)
    assert result == runic, f"Affine should pass runes through, got {result!r}"

def test_affine_accented_passthrough():
    """Affine should pass non-ASCII letters through unchanged."""
    result = affine_encrypt("café", 5, 8)
    # c->i, a->i, f->h, é passes through
    # Actually: c(2) -> (5*2+8)%26 = 18 = 's', a(0) -> (5*0+8)%26 = 8 = 'i', 
    # f(5) -> (5*5+8)%26 = 33%26 = 7 = 'h', é passes through
    expected = "sihé"
    assert result == expected, f"Expected {expected!r}, got {result!r}"

def test_crack_affine_non_alpha():
    """crack_affine with no alphabetic chars should return empty list."""
    assert crack_affine("123!@#") == []

def test_analyze_frequency_runic():
    """analyze_frequency on runic text should return error (no a-z letters)."""
    runic = text_to_runes("hello")
    result = analyze_frequency(runic)
    assert "error" in result, f"Expected error for runic input, got {result}"

def test_frequency_score_runic():
    """frequency_score on runic text should return inf (no a-z letters)."""
    runic = text_to_runes("hello")
    result = frequency_score(runic)
    assert result == float('inf'), f"Expected inf for runic input, got {result}"


# ── Run all tests ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_functions = [name for name in dir() if name.startswith("test_")]
    passed = 0
    failed = 0
    errors = []

    for test_name in sorted(test_functions):
        try:
            globals()[test_name]()
            print(f"  ✓ {test_name}")
            passed += 1
        except AssertionError as e:
            print(f"  ✗ {test_name}: {e}")
            failed += 1
            errors.append((test_name, str(e)))
        except Exception as e:
            print(f"  ✗ {test_name}: EXCEPTION: {e}")
            failed += 1
            errors.append((test_name, str(e)))

    print(f"\n{'═' * 50}")
    print(f"  Results: {passed} passed, {failed} failed, {passed + failed} total")
    
    if errors:
        print(f"\n  Failed tests:")
        for name, err in errors:
            print(f"    - {name}: {err}")
    
    sys.exit(0 if failed == 0 else 1)