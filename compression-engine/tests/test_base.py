"""Tests for base module (Codec base class, exceptions)."""

import pytest
from compression_engine.base import (
    Codec, CompressionError, IntegrityError, FormatError,
    compute_crc32, verify_crc32,
)


class TestExceptions:
    """Test custom exception classes."""

    def test_compression_error(self):
        with pytest.raises(CompressionError):
            raise CompressionError("test error")

    def test_integrity_error(self):
        err = IntegrityError(expected=0xDEADBEEF, actual=0xCAFEBABE, context="test context")
        assert err.expected == 0xDEADBEEF
        assert err.actual == 0xCAFEBABE
        assert "CRC32 mismatch" in str(err)
        assert "test context" in str(err)

    def test_format_error(self):
        with pytest.raises(FormatError):
            raise FormatError("bad format")

    def test_integrity_error_inherits(self):
        err = IntegrityError(0, 1)
        assert isinstance(err, CompressionError)
        assert isinstance(err, Exception)


class TestCRC32:
    """Test CRC32 utility functions."""

    def test_compute_crc32_empty(self):
        assert compute_crc32(b"") == 0

    def test_compute_crc32_hello(self):
        result = compute_crc32(b"hello")
        assert isinstance(result, int)
        assert result > 0

    def test_verify_crc32_success(self):
        data = b"test data"
        checksum = compute_crc32(data)
        # Should not raise
        verify_crc32(data, checksum)

    def test_verify_crc32_failure(self):
        data = b"test data"
        with pytest.raises(IntegrityError):
            verify_crc32(data, 0xBADBAD)

    def test_verify_crc32_with_context(self):
        data = b"test"
        with pytest.raises(IntegrityError) as exc_info:
            verify_crc32(data, 99999, "my codec")
        assert "my codec" in str(exc_info.value)


class TestCodecBase:
    """Test Codec abstract base class."""

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            Codec()  # type: ignore[abstract]

    def test_concrete_subclass(self):
        class DummyCodec(Codec):
            name = "dummy"
            def compress(self, data):
                return data
            def decompress(self, data):
                return data

        codec = DummyCodec()
        assert codec.roundtrip(b"test") is True
        assert repr(codec) == "DummyCodec()"

    def test_roundtrip_failure(self):
        class BadCodec(Codec):
            name = "bad"
            def compress(self, data):
                return data[::-1]
            def decompress(self, data):
                return data[::-1]  # not inverse of compress

        codec = BadCodec()
        result = codec.roundtrip(b"abcd")
        # compress then decompress: b"abcd" -> b"dcba" -> b"abcd"
        # Actually this does roundtrip correctly for this silly example
        # Let's make it truly bad
        class TrulyBadCodec(Codec):
            name = "trulybad"
            def compress(self, data):
                raise RuntimeError("nope")
            def decompress(self, data):
                return data

        codec2 = TrulyBadCodec()
        assert codec2.roundtrip(b"test") is False