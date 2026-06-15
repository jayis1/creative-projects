"""Tests for bit-level I/O."""

import pytest
from compression_engine.bitio import BitReader, BitWriter


class TestBitWriter:
    def test_write_single_bits(self):
        writer = BitWriter()
        writer.write_bit(1)
        writer.write_bit(0)
        writer.write_bit(1)
        result = writer.flush()
        # 10100000 = 0xA0
        assert result == bytes([0xA0])

    def test_write_byte(self):
        writer = BitWriter()
        writer.write_byte(0xAB)
        result = writer.flush()
        assert result == bytes([0xAB])

    def test_write_bits(self):
        writer = BitWriter()
        writer.write_bits(0b101, 3)
        result = writer.flush()
        # 10100000 = 0xA0
        assert result == bytes([0xA0])

    def test_write_multiple_bytes(self):
        writer = BitWriter()
        writer.write_byte(0xFF)
        writer.write_byte(0x00)
        writer.write_byte(0x12)
        result = writer.flush()
        assert result == bytes([0xFF, 0x00, 0x12])

    def test_write_uint16_le(self):
        writer = BitWriter()
        writer.write_uint16_le(0x1234)
        result = writer.flush()
        assert result == bytes([0x34, 0x12])

    def test_bit_length(self):
        writer = BitWriter()
        assert writer.bit_length == 0
        writer.write_bit(1)
        assert writer.bit_length == 1
        writer.write_byte(0)
        assert writer.bit_length == 9

    def test_flush_pads_correctly(self):
        writer = BitWriter()
        writer.write_bit(1)
        result = writer.flush()
        # 1 followed by 7 zeros = 0x80
        assert result == bytes([0x80])
        assert len(result) == 1


class TestBitReader:
    def test_read_single_bits(self):
        data = bytes([0xA0])  # 10100000
        reader = BitReader(data)
        assert reader.read_bit() == 1
        assert reader.read_bit() == 0
        assert reader.read_bit() == 1

    def test_read_byte(self):
        data = bytes([0xAB])
        reader = BitReader(data)
        assert reader.read_byte() == 0xAB

    def test_read_bits(self):
        data = bytes([0xA0])  # 10100000
        reader = BitReader(data)
        assert reader.read_bits(3) == 0b101

    def test_read_uint16_le(self):
        data = bytes([0x34, 0x12])
        reader = BitReader(data)
        assert reader.read_uint16_le() == 0x1234

    def test_eof_error(self):
        data = bytes([0xFF])
        reader = BitReader(data)
        reader.read_byte()  # consume 8 bits
        with pytest.raises(EOFError):
            reader.read_bit()

    def test_bits_remaining(self):
        data = bytes([0xFF, 0x00])
        reader = BitReader(data)
        assert reader.bits_remaining == 16
        reader.read_bit()
        assert reader.bits_remaining == 15
        reader.read_byte()
        assert reader.bits_remaining == 7

    def test_roundtrip_bits(self):
        writer = BitWriter()
        bits = [1, 0, 1, 1, 0, 0, 1, 0, 1, 0]
        for b in bits:
            writer.write_bit(b)
        data = writer.flush()

        reader = BitReader(data)
        result = [reader.read_bit() for _ in range(len(bits))]
        assert result == bits