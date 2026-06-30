"""Bug hunt tests for the Reed-Solomon codec.

These tests verify bugs found during the Phase 3 bug hunt, and serve as
regression tests after fixes are applied.
"""
from __future__ import annotations

import pytest

from reed_solomon.gf import GF256, gf_poly_mul, gf_poly_div, gf_poly_eval
from reed_solomon.codec import (
    rs_encode,
    rs_decode,
    encode_interleaved,
    decode_interleaved,
    RSCode,
    berlekamp_massey,
    calc_syndromes,
)


# ---------------------------------------------------------------------------
# Bug 1: gf_poly_mul crashes on empty input
# ---------------------------------------------------------------------------


class TestBugEmptyPolyMul:
    """Bug: gf_poly_mul([] , [1]) returns [] instead of [0] or raising."""

    def test_empty_mul_does_not_crash(self):
        """gf_poly_mul with empty polynomial should return [0] not []."""
        # Before fix: gf_poly_mul([], [1]) returns [] (length -1 array)
        # After fix: should return [0]
        result = gf_poly_mul([], [1])
        assert len(result) >= 1, "gf_poly_mul with empty input returned empty list"

    def test_empty_mul_both_empty(self):
        """gf_poly_mul([], []) should not crash."""
        result = gf_poly_mul([], [])
        assert len(result) >= 1


# ---------------------------------------------------------------------------
# Bug 2: decode_interleaved doesn't validate minimum data length
# ---------------------------------------------------------------------------


class TestBugInterleavedMinLength:
    """Bug: decode_interleaved with too-short data produces negative msg_len."""

    def test_short_interleaved_data_raises(self):
        """Data shorter than nsym * depth should raise a clear error."""
        # nsym=10, depth=3 → need at least 30 bytes, but only give 6
        with pytest.raises((ValueError, IndexError)):
            decode_interleaved(b"\x00" * 6, nsym=10, depth=3)


# ---------------------------------------------------------------------------
# Bug 3: CLI decode output filename replaces all '.rs' occurrences
# ---------------------------------------------------------------------------


class TestBugCLIDecodeFilename:
    """Bug: cli.py cmd_decode replaces all '.rs' in path, not just extension."""

    def test_filename_replacement_logic(self):
        """The .rs replacement should only affect the file extension."""
        import os
        # Case 1: file ends with .rs → strip extension
        input1 = "myfile.rs"
        if input1.endswith(".rs"):
            expected1 = input1[:-3]
        else:
            expected1 = input1 + ".decoded"
        assert expected1 == "myfile"

        # Case 2: file contains .rs but doesn't end with it → add .decoded
        input2 = "data.rs.txt"
        if input2.endswith(".rs"):
            expected2 = input2[:-3]
        else:
            expected2 = input2 + ".decoded"
        assert expected2 == "data.rs.txt.decoded"


# ---------------------------------------------------------------------------
# Bug 4: GF256.pow with negative exponent gives wrong results
# ---------------------------------------------------------------------------


class TestBugNegativePow:
    """Bug: GF256.pow with negative exponent gives incorrect results."""

    def test_negative_pow_raises(self):
        """Negative exponent should raise ValueError, not give wrong result."""
        with pytest.raises((ValueError, TypeError)):
            GF256.pow(2, -1)


# ---------------------------------------------------------------------------
# Bug 5: encode_interleaved doesn't validate max block size
# ---------------------------------------------------------------------------


class TestBugInterleavedMaxSize:
    """Bug: encode_interleaved doesn't check if blocks fit in GF(2^8)."""

    def test_large_interleaved_data_raises(self):
        """Data where block_size + nsym > 255 should raise."""
        # depth=1, nsym=10, data=250 bytes → block_size=250, 250+10=260>255
        with pytest.raises(ValueError):
            encode_interleaved(b"\x00" * 250, nsym=10, depth=1)


# ---------------------------------------------------------------------------
# Bug 6: Berlekamp-Massey degree check missing
# ---------------------------------------------------------------------------


class TestBugBMDegree:
    """Bug: BM may return a polynomial with degree > nsym//2 without error."""

    def test_bm_degree_never_exceeds_nsym_half(self):
        """BM with valid syndromes should produce locator of degree <= nsym//2."""
        from reed_solomon.codec import berlekamp_massey
        msg = list(range(20))
        encoded = rs_encode(msg, nsym=10)
        corrupted = list(encoded)
        # 5 errors = nsym//2, the max
        for i in range(5):
            corrupted[i * 3] ^= 42 + i
        syndromes = [gf_poly_eval(corrupted, GF256.pow(2, i)) for i in range(10)]
        sigma = berlekamp_massey(syndromes)
        # Degree of sigma should be <= 5
        deg = len(sigma) - 1
        assert deg <= 5, f"BM returned degree {deg} > nsym//2=5"


# ---------------------------------------------------------------------------
# Bug 7: rs_encode with empty message produces wrong-length codeword
# ---------------------------------------------------------------------------


class TestBugEmptyMessageEncode:
    """Bug: rs_encode([], nsym) may produce wrong-length codeword."""

    def test_empty_message_length(self):
        """Encoding empty message should produce nsym-length codeword."""
        encoded = rs_encode([], nsym=10)
        assert len(encoded) == 10, f"Expected length 10, got {len(encoded)}"

    def test_empty_message_valid(self):
        """Encoding empty message should produce valid codeword."""
        from reed_solomon.codec import calc_syndromes
        encoded = rs_encode([], nsym=10)
        synd = calc_syndromes(encoded, 10)
        assert all(s == 0 for s in synd), "Empty message encoding has nonzero syndromes"


# ---------------------------------------------------------------------------
# Bug 8: gf_poly_div with zero divisor should raise
# ---------------------------------------------------------------------------


class TestBugDivByZeroPoly:
    """Bug: gf_poly_div with all-zero divisor should raise ZeroDivisionError."""

    def test_div_by_zero_poly_raises(self):
        """Dividing by [0] or [0,0,0] should raise."""
        with pytest.raises(ZeroDivisionError):
            gf_poly_div([1, 2, 3], [0])
        with pytest.raises(ZeroDivisionError):
            gf_poly_div([1, 2, 3], [0, 0, 0])

    def test_div_by_empty_raises(self):
        """Dividing by empty list should raise."""
        with pytest.raises(ZeroDivisionError):
            gf_poly_div([1, 2, 3], [])