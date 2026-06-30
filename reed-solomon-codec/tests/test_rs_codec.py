"""Comprehensive pytest test suite for the Reed-Solomon codec.

Tests cover:
- GF(2^8) arithmetic properties
- Polynomial operations
- Encoding correctness
- Error correction (various counts)
- Erasure correction
- Combined error + erasure correction
- Interleaving / burst-error correction
- RSCode class API
- Edge cases and error handling
- Randomized round-trip tests
- Boundary conditions
"""
from __future__ import annotations

import random
import pytest

from reed_solomon.gf import GF256, gf_poly_mul, gf_poly_eval, gf_poly_add, gf_poly_div, gf_poly_scale
from reed_solomon.codec import (
    generator_poly,
    rs_encode,
    rs_decode,
    rs_decode_detailed,
    calc_syndromes,
    berlekamp_massey,
    chien_search,
    forney,
    encode,
    decode,
    encode_message,
    decode_message,
    RSCode,
    DecodeResult,
    interleave,
    deinterleave,
    encode_interleaved,
    decode_interleaved,
)


# ---------------------------------------------------------------------------
# GF(2^8) arithmetic tests
# ---------------------------------------------------------------------------


class TestGF256:
    """Test Galois field arithmetic."""

    def test_add_is_xor(self):
        """Addition in GF(2^8) is XOR."""
        for a in range(256):
            for b in range(256):
                assert GF256.add(a, b) == (a ^ b)

    def test_sub_is_xor(self):
        """Subtraction equals addition (same as XOR in char-2)."""
        for a in range(256):
            for b in range(256):
                assert GF256.sub(a, b) == (a ^ b)

    def test_mul_zero(self):
        """Multiplication by zero gives zero."""
        for a in range(256):
            assert GF256.mul(a, 0) == 0
            assert GF256.mul(0, a) == 0

    def test_mul_one(self):
        """Multiplication by 1 is identity."""
        for a in range(256):
            assert GF256.mul(a, 1) == a
            assert GF256.mul(1, a) == a

    def test_mul_commutative(self):
        """Multiplication is commutative."""
        for _ in range(1000):
            a = random.randint(0, 255)
            b = random.randint(0, 255)
            assert GF256.mul(a, b) == GF256.mul(b, a)

    def test_mul_associative(self):
        """Multiplication is associative."""
        for _ in range(500):
            a = random.randint(1, 255)
            b = random.randint(1, 255)
            c = random.randint(1, 255)
            assert GF256.mul(GF256.mul(a, b), c) == GF256.mul(a, GF256.mul(b, c))

    def test_mul_distributive(self):
        """Multiplication distributes over addition."""
        for _ in range(500):
            a = random.randint(0, 255)
            b = random.randint(0, 255)
            c = random.randint(0, 255)
            assert GF256.mul(a, GF256.add(b, c)) == \
                   GF256.add(GF256.mul(a, b), GF256.mul(a, c))

    def test_div_inverse(self):
        """Division is multiplication by inverse."""
        for _ in range(500):
            a = random.randint(1, 255)
            b = random.randint(1, 255)
            assert GF256.div(a, b) == GF256.mul(a, GF256.inv(b))

    def test_div_by_zero(self):
        """Division by zero raises ZeroDivisionError."""
        with pytest.raises(ZeroDivisionError):
            GF256.div(1, 0)

    def test_inv_of_zero(self):
        """Inverse of zero raises."""
        with pytest.raises(ZeroDivisionError):
            GF256.inv(0)

    def test_inv_is_inverse(self):
        """a * inv(a) = 1 for all nonzero a."""
        for a in range(1, 256):
            assert GF256.mul(a, GF256.inv(a)) == 1

    def test_pow_zero(self):
        """Anything to the 0th power is 1."""
        for a in range(1, 256):
            assert GF256.pow(a, 0) == 1

    def test_pow_one(self):
        """Anything to the 1st power is itself."""
        for a in range(256):
            assert GF256.pow(a, 1) == a

    def test_pow_cycle(self):
        """a^255 = 1 for all nonzero a (Fermat's little theorem)."""
        for a in range(1, 256):
            assert GF256.pow(a, 255) == 1

    def test_log_of_zero(self):
        """log(0) raises ValueError."""
        with pytest.raises(ValueError):
            GF256.log(0)

    def test_log_exp_roundtrip(self):
        """log(exp(i)) = i and exp(log(a)) = a."""
        for i in range(255):
            assert GF256.log(GF256.pow(2, i)) == i
        for a in range(1, 256):
            assert GF256.pow(2, GF256.log(a)) == a

    def test_generator_is_primitive(self):
        """2 is a primitive element: its powers generate all nonzero elements."""
        powers = set()
        x = 1
        for _ in range(255):
            powers.add(x)
            x = GF256.mul(x, 2)
        assert powers == set(range(1, 256))


# ---------------------------------------------------------------------------
# Polynomial operation tests
# ---------------------------------------------------------------------------


class TestPolynomials:
    """Test polynomial operations over GF(2^8)."""

    def test_add_identity(self):
        """Adding zero polynomial is identity."""
        p = [1, 2, 3, 4, 5]
        assert gf_poly_add(p, [0]) == p

    def test_add_self_is_zero(self):
        """Adding a polynomial to itself gives zero."""
        p = [1, 2, 3, 4, 5]
        result = gf_poly_add(p, p)
        assert all(c == 0 for c in result)

    def test_mul_by_one(self):
        """Multiplying by [1] (the polynomial 1) is identity."""
        p = [1, 2, 3, 4, 5]
        assert gf_poly_mul(p, [1]) == p

    def test_mul_by_zero(self):
        """Multiplying by [0] gives [0]."""
        p = [1, 2, 3, 4, 5]
        result = gf_poly_mul(p, [0])
        assert all(c == 0 for c in result)

    def test_mul_degree(self):
        """deg(p*q) = deg(p) + deg(q)."""
        p = [1, 0, 1]  # x^2 + 1
        q = [1, 1]     # x + 1
        result = gf_poly_mul(p, q)
        assert len(result) == len(p) + len(q) - 1

    def test_div_identity(self):
        """Dividing by [1] gives the same polynomial, remainder is 0s."""
        p = [1, 2, 3, 4, 5]
        q, r = gf_poly_div(p, [1])
        assert q == p
        assert all(c == 0 for c in r)

    def test_div_self(self):
        """Dividing a polynomial by itself gives quotient [1], remainder all 0s."""
        p = [3, 1, 2, 4]
        q, r = gf_poly_div(p, list(p))
        assert len(q) == 1 and q[0] == 1
        assert all(c == 0 for c in r)

    def test_div_remainder_degree(self):
        """Remainder degree < divisor degree."""
        dividend = [1, 2, 3, 4, 5, 6, 7, 8]
        divisor = [1, 1, 1]
        q, r = gf_poly_div(dividend, divisor)
        assert len(r) < len(divisor)

    def test_eval_zero(self):
        """Evaluating at 0 gives the constant term."""
        p = [5, 3, 1, 2]
        assert gf_poly_eval(p, 0) == 5

    def test_eval_one(self):
        """Evaluating at 1 gives sum of all coefficients."""
        p = [5, 3, 1, 2]
        assert gf_poly_eval(p, 1) == 5 ^ 3 ^ 1 ^ 2


# ---------------------------------------------------------------------------
# Generator polynomial tests
# ---------------------------------------------------------------------------


class TestGeneratorPoly:
    """Test generator polynomial construction."""

    def test_roots(self):
        """Generator polynomial has roots at α^0, α^1, ..., α^{nsym-1}."""
        for nsym in [2, 4, 8, 10, 16, 32]:
            gen = generator_poly(nsym)
            for i in range(nsym):
                assert gf_poly_eval(gen, GF256.pow(2, i)) == 0

    def test_degree(self):
        """Generator polynomial degree equals nsym."""
        for nsym in [1, 2, 5, 10, 20, 50]:
            gen = generator_poly(nsym)
            # Lowest-first: degree = len-1, and leading coeff should be nonzero
            assert len(gen) == nsym + 1
            assert gen[-1] != 0  # leading coefficient

    def test_caching(self):
        """Generator polynomial is cached and returns same values."""
        g1 = generator_poly(10)
        g2 = generator_poly(10)
        assert g1 == g2


# ---------------------------------------------------------------------------
# Encoding tests
# ---------------------------------------------------------------------------


class TestEncoding:
    """Test RS encoding."""

    def test_basic_encode(self):
        """Encoding produces a valid codeword (zero syndromes)."""
        msg = list(range(10))
        encoded = rs_encode(msg, nsym=10)
        syndromes = calc_syndromes(encoded, nsym=10)
        assert all(s == 0 for s in syndromes)

    def test_empty_message(self):
        """Encoding an empty message returns just parity (all zeros)."""
        encoded = rs_encode([], nsym=5)
        assert len(encoded) == 5
        assert all(s == 0 for s in encoded)

    def test_nsym_zero(self):
        """nsym=0 returns the message unchanged."""
        msg = [1, 2, 3, 4, 5]
        encoded = rs_encode(msg, nsym=0)
        assert encoded == msg

    def test_message_preserved(self):
        """Systematic encoding preserves the message in the codeword."""
        msg = [10, 20, 30, 40, 50]
        encoded = rs_encode(msg, nsym=10)
        # Message is in the high-order positions (after parity)
        assert encoded[10:] == msg

    def test_length(self):
        """Encoded length = message length + nsym."""
        msg = list(range(20))
        encoded = rs_encode(msg, nsym=8)
        assert len(encoded) == 28

    def test_invalid_symbol(self):
        """Out-of-range symbols raise ValueError."""
        with pytest.raises(ValueError):
            rs_encode([256], nsym=10)
        with pytest.raises(ValueError):
            rs_encode([-1], nsym=10)

    def test_negative_nsym(self):
        """Negative nsym raises ValueError."""
        with pytest.raises(ValueError):
            rs_encode([1, 2, 3], nsym=-1)

    def test_too_long(self):
        """Message too long for GF(2^8) raises ValueError."""
        msg = [0] * 250
        with pytest.raises(ValueError):
            rs_encode(msg, nsym=10)  # 250 + 10 = 260 > 255


# ---------------------------------------------------------------------------
# Error correction tests
# ---------------------------------------------------------------------------


class TestErrorCorrection:
    """Test RS error correction."""

    def test_no_errors(self):
        """Decoding a valid codeword returns it unchanged."""
        msg = list(range(20))
        encoded = rs_encode(msg, nsym=10)
        decoded = rs_decode(encoded, nsym=10)
        assert decoded == encoded

    def test_single_error(self):
        """Correct a single error."""
        msg = list(range(20))
        encoded = rs_encode(msg, nsym=10)
        corrupted = list(encoded)
        corrupted[5] ^= 42
        decoded = rs_decode(corrupted, nsym=10)
        assert decoded == encoded

    def test_two_errors(self):
        """Correct two errors."""
        msg = list(range(20))
        encoded = rs_encode(msg, nsym=10)
        corrupted = list(encoded)
        corrupted[3] ^= 42
        corrupted[15] ^= 99
        decoded = rs_decode(corrupted, nsym=10)
        assert decoded == encoded

    def test_max_errors(self):
        """Correct the maximum number of errors (nsym//2)."""
        msg = list(range(20))
        nsym = 10
        encoded = rs_encode(msg, nsym)
        corrupted = list(encoded)
        for i in range(nsym // 2):
            corrupted[i * 3] ^= (i + 1) * 17
        decoded = rs_decode(corrupted, nsym)
        assert decoded == encoded

    def test_too_many_errors(self):
        """Too many errors raises ValueError."""
        msg = list(range(20))
        nsym = 10
        encoded = rs_encode(msg, nsym)
        corrupted = list(encoded)
        # nsym//2 + 1 = 6 errors
        for i in range(nsym // 2 + 1):
            corrupted[i * 3] ^= 42 + i
        with pytest.raises(ValueError):
            rs_decode(corrupted, nsym)

    def test_random_errors(self):
        """Randomized test: correct random errors up to nsym//2."""
        for trial in range(20):
            msg = [random.randint(0, 255) for _ in range(30)]
            nsym = 16
            encoded = rs_encode(msg, nsym)
            n = len(encoded)
            num_errors = nsym // 2
            positions = random.sample(range(n), num_errors)
            corrupted = list(encoded)
            for p in positions:
                corrupted[p] ^= random.randint(1, 255)
            decoded = rs_decode(corrupted, nsym)
            assert decoded == encoded, f"Trial {trial}: failed to correct {num_errors} errors"


# ---------------------------------------------------------------------------
# Erasure correction tests
# ---------------------------------------------------------------------------


class TestErasureCorrection:
    """Test RS erasure correction."""

    def test_single_erasure(self):
        """Correct a single erasure."""
        msg = list(range(20))
        nsym = 10
        encoded = rs_encode(msg, nsym)
        corrupted = list(encoded)
        corrupted[7] = 0
        decoded = rs_decode(corrupted, nsym, erasures=[7])
        assert decoded == encoded

    def test_max_erasures(self):
        """Correct the maximum number of erasures (nsym)."""
        msg = list(range(20))
        nsym = 10
        encoded = rs_encode(msg, nsym)
        corrupted = list(encoded)
        positions = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19]
        for p in positions:
            corrupted[p] = 0
        decoded = rs_decode(corrupted, nsym, erasures=positions)
        assert decoded == encoded

    def test_too_many_erasures(self):
        """Too many erasures raises ValueError."""
        msg = list(range(20))
        nsym = 4
        encoded = rs_encode(msg, nsym)
        corrupted = list(encoded)
        with pytest.raises(ValueError):
            rs_decode(corrupted, nsym, erasures=[0, 1, 2, 3, 4])

    def test_erasure_out_of_range(self):
        """Erasure position out of range raises ValueError."""
        msg = list(range(10))
        nsym = 4
        encoded = rs_encode(msg, nsym)
        with pytest.raises(ValueError):
            rs_decode(list(encoded), nsym, erasures=[100])
        with pytest.raises(ValueError):
            rs_decode(list(encoded), nsym, erasures=[-1])

    def test_random_erasures(self):
        """Randomized erasure correction test."""
        for trial in range(10):
            msg = [random.randint(0, 255) for _ in range(30)]
            nsym = 12
            encoded = rs_encode(msg, nsym)
            n = len(encoded)
            num_erasures = nsym
            positions = sorted(random.sample(range(n), num_erasures))
            corrupted = list(encoded)
            for p in positions:
                corrupted[p] = 0
            decoded = rs_decode(corrupted, nsym, erasures=positions)
            assert decoded == encoded, f"Trial {trial}: erasure correction failed"


# ---------------------------------------------------------------------------
# RSCode class tests
# ---------------------------------------------------------------------------


class TestRSCodeClass:
    """Test the class-based API."""

    def test_basic(self):
        """RSCode basic encode/decode."""
        rs = RSCode(nsym=10)
        msg = [1, 2, 3, 4, 5]
        encoded = rs.encode(msg)
        decoded = rs.decode(encoded)
        assert decoded == encoded

    def test_properties(self):
        """RSCode properties are correct."""
        rs = RSCode(nsym=10)
        assert rs.nsym == 10
        assert rs.max_errors == 5
        assert rs.max_erasures == 10
        assert rs.max_message_length == 245

    def test_bytes_api(self):
        """RSCode byte encode/decode."""
        rs = RSCode(nsym=10)
        data = b"Hello, World!"
        encoded = rs.encode_bytes(data)
        corrupted = bytearray(encoded)
        corrupted[5] ^= 0xFF
        decoded = rs.decode_bytes(corrupted)
        assert decoded == encoded

    def test_encode_data_decode_data(self):
        """RSCode data encode/decode with parity stripping."""
        rs = RSCode(nsym=10)
        data = b"Hello, World!"
        encoded = rs.encode_data(data)
        corrupted = bytearray(encoded)
        corrupted[3] ^= 0xAA
        recovered = rs.decode_data(bytes(corrupted))
        assert recovered == data

    def test_detailed_decode(self):
        """RSCode detailed decode returns statistics."""
        rs = RSCode(nsym=10)
        msg = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        encoded = rs.encode(msg)
        corrupted = list(encoded)
        corrupted[3] ^= 42
        corrupted[7] ^= 99
        result = rs.decode_detailed(corrupted)
        assert result.success
        assert result.errors_corrected == 2
        assert set(result.error_positions) == {3, 7}

    def test_message_too_long(self):
        """RSCode rejects too-long messages."""
        rs = RSCode(nsym=10)
        msg = [0] * 246  # exceeds max_message_length=245
        with pytest.raises(ValueError):
            rs.encode(msg)

    def test_repr(self):
        """RSCode has a useful repr."""
        rs = RSCode(nsym=10)
        s = repr(rs)
        assert "nsym=10" in s
        assert "max_errors=5" in s

    def test_str(self):
        """RSCode has a useful str."""
        rs = RSCode(nsym=10)
        s = str(rs)
        assert "Reed-Solomon" in s
        assert "nsym" in s.lower()


# ---------------------------------------------------------------------------
# Interleaving tests
# ---------------------------------------------------------------------------


class TestInterleaving:
    """Test interleaving for burst-error correction."""

    def test_interleave_deinterleave(self):
        """Interleave then deinterleave is identity."""
        data = list(range(20))
        interleaved = interleave(data, 4)
        assert deinterleave(interleaved, 4) == data

    def test_interleave_invalid_rows(self):
        """Interleave with non-divisible length raises."""
        with pytest.raises(ValueError):
            interleave([1, 2, 3], 2)

    def test_interleave_zero_rows(self):
        """Interleave with 0 rows raises."""
        with pytest.raises(ValueError):
            interleave([1, 2, 3, 4], 0)

    def test_burst_correction(self):
        """Interleaved RS corrects burst errors that would fail non-interleaved."""
        nsym = 4
        depth = 5
        msg = b"Interleaving protects against burst errors!!"
        encoded = bytearray(encode_interleaved(msg, nsym, depth))

        # Burst of length depth (5) — each codeword sees 1 error, easily corrected
        burst_start = 3
        burst_len = depth
        for i in range(burst_len):
            if burst_start + i < len(encoded):
                encoded[burst_start + i] ^= 0xFF

        recovered = decode_interleaved(bytes(encoded), nsym, depth, original_len=len(msg))
        assert recovered == msg

    def test_padding(self):
        """Interleaving pads data to be divisible by depth."""
        data = b"Hello"  # 5 bytes
        encoded = encode_interleaved(data, 4, 3)
        # 5 -> pad to 6 (divisible by 3), each block 2 bytes, cw = 2+4=6, total = 18
        recovered = decode_interleaved(encoded, 4, 3, original_len=5)
        assert recovered == data


# ---------------------------------------------------------------------------
# Byte API tests
# ---------------------------------------------------------------------------


class TestByteAPI:
    """Test the byte-oriented convenience API."""

    def test_encode_decode_no_errors(self):
        """Byte API round trip with no errors."""
        data = b"Hello, Reed-Solomon!"
        encoded = encode_message(data, 10)
        decoded = decode_message(encoded, 10)
        assert decoded == data

    def test_encode_decode_with_errors(self):
        """Byte API with errors."""
        data = b"Hello, Reed-Solomon!"
        encoded = bytearray(encode_message(data, 10))
        encoded[5] ^= 0xFF
        encoded[10] ^= 0xAA
        encoded[15] ^= 0x42
        decoded = decode_message(bytes(encoded), 10)
        assert decoded == data

    def test_encode_decode_with_erasures(self):
        """Byte API with erasures."""
        data = b"Hello, RS!"
        encoded = bytearray(encode_message(data, 6))
        erasures = [0, 3, 8]
        for p in erasures:
            encoded[p] = 0
        decoded = decode_message(bytes(encoded), 6, erasures=erasures)
        assert decoded == data


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_all_zero_message(self):
        """All-zero message encodes to all-zero codeword."""
        msg = [0] * 10
        encoded = rs_encode(msg, nsym=5)
        assert all(s == 0 for s in encoded)

    def test_all_ones_message(self):
        """All-0xFF message encodes correctly."""
        msg = [255] * 10
        encoded = rs_encode(msg, nsym=5)
        syndromes = calc_syndromes(encoded, 5)
        assert all(s == 0 for s in syndromes)

    def test_single_symbol_message(self):
        """Single symbol message with large nsym."""
        msg = [42]
        encoded = rs_encode(msg, nsym=20)
        decoded = rs_decode(encoded, nsym=20)
        assert decoded == encoded

    def test_error_at_position_zero(self):
        """Error at position 0 is correctable."""
        msg = list(range(10))
        encoded = rs_encode(msg, nsym=10)
        corrupted = list(encoded)
        corrupted[0] ^= 77
        decoded = rs_decode(corrupted, nsym=10)
        assert decoded == encoded

    def test_error_at_last_position(self):
        """Error at the last position is correctable."""
        msg = list(range(10))
        encoded = rs_encode(msg, nsym=10)
        corrupted = list(encoded)
        corrupted[-1] ^= 88
        decoded = rs_decode(corrupted, nsym=10)
        assert decoded == encoded

    def test_large_nsym(self):
        """Large nsym works correctly."""
        msg = list(range(50))
        nsym = 100
        encoded = rs_encode(msg, nsym)
        assert len(encoded) == 150
        corrupted = list(encoded)
        # 50 errors = nsym // 2
        for i in range(0, 50):
            corrupted[i * 2] ^= (i * 5 + 3) & 0xFF
        decoded = rs_decode(corrupted, nsym)
        assert decoded == encoded

    def test_duplicate_erasures(self):
        """Duplicate erasure positions are handled."""
        msg = list(range(10))
        encoded = rs_encode(msg, nsym=8)
        corrupted = list(encoded)
        corrupted[3] = 0
        corrupted[7] = 0
        # Duplicates in the erasure list
        decoded = rs_decode(corrupted, nsym=8, erasures=[3, 3, 7, 7])
        assert decoded == encoded

    def test_nsym_one(self):
        """nsym=1 can detect but not correct errors."""
        msg = [1, 2, 3]
        encoded = rs_encode(msg, nsym=1)
        syndromes = calc_syndromes(encoded, 1)
        assert all(s == 0 for s in syndromes)
        # No-error decode works
        assert rs_decode(encoded, nsym=1) == encoded

    def test_empty_codeword(self):
        """Empty received codeword decodes to empty."""
        result = rs_decode_detailed([], nsym=10)
        assert result.success
        assert result.corrected == []


# ---------------------------------------------------------------------------
# DecodeResult tests
# ---------------------------------------------------------------------------


class TestDecodeResult:
    """Test the DecodeResult class."""

    def test_no_error_result(self):
        """No-error decode has zero corrections."""
        rs = RSCode(nsym=10)
        encoded = rs.encode([1, 2, 3, 4, 5])
        result = rs.decode_detailed(list(encoded))
        assert result.success
        assert result.errors_corrected == 0
        assert result.erasures_corrected == 0
        assert result.error_positions == []

    def test_repr(self):
        """DecodeResult has a useful repr."""
        result = DecodeResult([1, 2, 3], [1], [], True)
        s = repr(result)
        assert "success=True" in s
        assert "errors_corrected=1" in s


# ---------------------------------------------------------------------------
# Randomized stress tests
# ---------------------------------------------------------------------------


class TestStressTests:
    """Randomized stress tests for robustness."""

    def test_random_round_trip(self):
        """100 random encode/decode round trips with errors."""
        for trial in range(100):
            msg_len = random.randint(1, 50)
            msg = [random.randint(0, 255) for _ in range(msg_len)]
            nsym = random.choice([4, 6, 8, 10, 12, 16, 20])
            encoded = rs_encode(msg, nsym)
            n = len(encoded)
            num_errors = random.randint(0, nsym // 2)
            positions = random.sample(range(n), num_errors)
            corrupted = list(encoded)
            for p in positions:
                corrupted[p] ^= random.randint(1, 255)
            decoded = rs_decode(corrupted, nsym)
            assert decoded == encoded, f"Trial {trial}: round-trip failed"

    def test_random_erasure_round_trip(self):
        """50 random erasure-only round trips."""
        for trial in range(50):
            msg_len = random.randint(1, 30)
            msg = [random.randint(0, 255) for _ in range(msg_len)]
            nsym = random.choice([6, 8, 10, 12])
            encoded = rs_encode(msg, nsym)
            n = len(encoded)
            num_erasures = random.randint(0, nsym)
            positions = sorted(random.sample(range(n), num_erasures))
            corrupted = list(encoded)
            for p in positions:
                corrupted[p] = 0
            decoded = rs_decode(corrupted, nsym, erasures=positions)
            assert decoded == encoded, f"Trial {trial}: erasure round-trip failed"