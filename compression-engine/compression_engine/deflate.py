"""DEFLATE-like compression codec combining LZ77 and Huffman coding.

Implements a simplified version of the DEFLATE algorithm:
1. LZ77 pass to produce literal/length/distance tokens
2. Huffman coding of the token stream
3. Block-based output format

This is a from-scratch implementation (no zlib dependency).
"""

from __future__ import annotations

import heapq
from typing import Dict, List, Optional, Tuple
from .bitio import BitReader, BitWriter
from .huffman import _lengths_to_canonical


# --- Length and Distance encoding tables (DEFLATE-compatible) ---

# Length codes: code 257-285 map to lengths 3-258
LENGTH_EXTRA_BITS = [
    0, 0, 0, 0, 0, 0, 0, 0,  # 257-264: lengths 3-10
    1, 1, 1, 1,               # 265-268: lengths 11-18
    2, 2, 2, 2,               # 269-272: lengths 19-34
    3, 3, 3, 3,               # 273-276: lengths 35-66
    4, 4, 4, 4,               # 277-280: lengths 67-130
    5, 5, 5, 5,               # 281-284: lengths 131-258
    0,                         # 285: length 258
]

LENGTH_BASE = [
    3, 4, 5, 6, 7, 8, 9, 10,     # 257-264
    11, 13, 15, 17,               # 265-268
    19, 23, 27, 31,               # 269-272
    35, 43, 51, 59,               # 273-276
    67, 83, 99, 115,              # 277-280
    131, 163, 195, 227,           # 281-284
    258,                          # 285
]

# Distance codes: code 0-29 map to distances 1-32768
DIST_EXTRA_BITS = [
    0, 0, 0, 0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6,
    7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12, 13, 13,
]

DIST_BASE = [
    1, 2, 3, 4, 5, 7, 9, 13, 17, 25, 33, 49, 65, 97, 129, 193,
    257, 385, 513, 769, 1025, 1537, 2049, 3073, 4097, 6145,
    8193, 12289, 16385, 24577,
]


def _length_to_code(length: int) -> Tuple[int, int, int]:
    """Convert a match length (3-258) to (code, extra_bits_value, extra_bits_count)."""
    for i in range(len(LENGTH_BASE) - 1, -1, -1):
        if length >= LENGTH_BASE[i]:
            code = 257 + i
            extra_bits_count = LENGTH_EXTRA_BITS[i]
            extra_value = length - LENGTH_BASE[i]
            return code, extra_value, extra_bits_count
    raise ValueError(f"Invalid length: {length}")


def _code_to_length(code: int, extra_value: int) -> int:
    """Convert a length code + extra bits back to length."""
    idx = code - 257
    if idx < 0 or idx >= len(LENGTH_BASE):
        raise ValueError(f"Invalid length code: {code}")
    return LENGTH_BASE[idx] + extra_value


def _distance_to_code(distance: int) -> Tuple[int, int, int]:
    """Convert a distance (1-32768) to (code, extra_value, extra_bits_count)."""
    for i in range(len(DIST_BASE) - 1, -1, -1):
        if distance >= DIST_BASE[i]:
            extra_bits_count = DIST_EXTRA_BITS[i]
            extra_value = distance - DIST_BASE[i]
            return i, extra_value, extra_bits_count
    raise ValueError(f"Invalid distance: {distance}")


def _code_to_distance(code: int, extra_value: int) -> int:
    """Convert a distance code + extra bits back to distance."""
    if code < 0 or code >= len(DIST_BASE):
        raise ValueError(f"Invalid distance code: {code}")
    return DIST_BASE[code] + extra_value


# Token types
LITERAL = 0
MATCH = 1


class _Token:
    __slots__ = ("kind", "byte", "length", "distance")

    def __init__(self, kind: int, byte: int = 0, length: int = 0, distance: int = 0) -> None:
        self.kind = kind
        self.byte = byte
        self.length = length
        self.distance = distance


def _lz77_tokenize(data: bytes, window_size: int = 32768, max_match: int = 258, min_match: int = 3) -> List[_Token]:
    """Produce LZ77 tokens from input data."""
    tokens: List[_Token] = []
    i = 0
    n = len(data)
    while i < n:
        best_length = 0
        best_distance = 0
        window_start = max(0, i - window_size)
        max_len = min(max_match, n - i)

        for j in range(window_start, i):
            length = 0
            while length < max_len and data[j + length] == data[i + length]:
                length += 1
            if length >= min_match and length > best_length:
                best_length = length
                best_distance = i - j
                if best_length >= max_match:
                    break

        if best_length >= min_match:
            tokens.append(_Token(MATCH, length=best_length, distance=best_distance))
            i += best_length
        else:
            tokens.append(_Token(LITERAL, byte=data[i]))
            i += 1
    return tokens


class DeflateCodec:
    """DEFLATE-like compression codec.

    Combines LZ77 tokenization with Huffman coding.

    Format:
    - 4 bytes: original data length (little-endian)
    - 1 bit: BFINAL (1 if last block)
    - 2 bits: BTYPE (01 = static Huffman)
    - Compressed data using static Huffman codes
    - End-of-block symbol (256)

    Static Huffman code lengths (DEFLATE spec):
    - Lit/Len 0-143:   8 bits
    - Lit/Len 144-255: 9 bits
    - Lit/Len 256-279: 7 bits  (256=end-of-block, 257-279=length codes)
    - Lit/Len 280-287: 8 bits  (280-287=length codes)
    - Distance 0-31:   5 bits
    """

    # Static Huffman code lengths (DEFLATE spec)
    _STATIC_LIT_LENGTHS: Dict[int, int] = {}
    _STATIC_DIST_LENGTHS: Dict[int, int] = {}

    def __init__(self, window_size: int = 32768) -> None:
        self.window_size = window_size

    @classmethod
    def _init_static_tables(cls) -> None:
        """Build static Huffman code tables."""
        if cls._STATIC_LIT_LENGTHS:
            return
        lengths: Dict[int, int] = {}
        for i in range(144):
            lengths[i] = 8
        for i in range(144, 256):
            lengths[i] = 9
        lengths[256] = 7  # End of block
        for i in range(257, 280):
            lengths[i] = 7
        for i in range(280, 288):
            lengths[i] = 8
        cls._STATIC_LIT_LENGTHS = lengths
        cls._STATIC_DIST_LENGTHS = {i: 5 for i in range(32)}

    def compress(self, data: bytes) -> bytes:
        """Compress data using DEFLATE-like codec with static Huffman."""
        self._init_static_tables()

        if not data:
            # Write 4-byte length prefix + minimal block
            writer = BitWriter()
            # 4-byte original length
            for shift in range(0, 32, 8):
                writer.write_byte(0)
            # Block: BFINAL=1, BTYPE=01 (static Huffman)
            writer.write_bit(1)       # BFINAL
            writer.write_bits(1, 2)   # BTYPE = 01 (static Huffman)
            # Write end-of-block only
            lit_canonical = _lengths_to_canonical(self._STATIC_LIT_LENGTHS)
            eob_code, eob_len = lit_canonical[256]
            writer.write_bits(eob_code, eob_len)
            return writer.flush()

        tokens = _lz77_tokenize(data, self.window_size)

        lit_canonical = _lengths_to_canonical(self._STATIC_LIT_LENGTHS)
        dist_canonical = _lengths_to_canonical(self._STATIC_DIST_LENGTHS)

        # Prepend 4-byte original length
        length_prefix = bytearray()
        for shift in range(0, 32, 8):
            length_prefix.append((len(data) >> shift) & 0xFF)

        writer = BitWriter()
        # Block header: BFINAL=1, BTYPE=01
        writer.write_bit(1)       # BFINAL
        writer.write_bits(1, 2)   # BTYPE = 01 (static Huffman)

        for token in tokens:
            if token.kind == LITERAL:
                code, code_len = lit_canonical[token.byte]
                writer.write_bits(code, code_len)
            else:
                # Length code
                len_code, extra_val, extra_bits = _length_to_code(token.length)
                code, code_len = lit_canonical[len_code]
                writer.write_bits(code, code_len)
                if extra_bits > 0:
                    writer.write_bits(extra_val, extra_bits)
                # Distance code
                dist_code, dist_extra_val, dist_extra_bits = _distance_to_code(token.distance)
                code, code_len = dist_canonical[dist_code]
                writer.write_bits(code, code_len)
                if dist_extra_bits > 0:
                    writer.write_bits(dist_extra_val, dist_extra_bits)

        # End of block
        eob_code, eob_len = lit_canonical[256]
        writer.write_bits(eob_code, eob_len)

        return bytes(length_prefix) + writer.flush()

    def decompress(self, data: bytes) -> bytes:
        """Decompress DEFLATE-like coded data."""
        self._init_static_tables()
        if len(data) < 4:
            raise ValueError("Data too short")
        orig_len = int.from_bytes(data[:4], "little")

        lit_canonical = _lengths_to_canonical(self._STATIC_LIT_LENGTHS)
        dist_canonical = _lengths_to_canonical(self._STATIC_DIST_LENGTHS)

        # Build decode tables: (code, length) -> symbol
        lit_decode: Dict[Tuple[int, int], int] = {}
        for sym, (code, code_len) in lit_canonical.items():
            lit_decode[(code, code_len)] = sym
        dist_decode: Dict[Tuple[int, int], int] = {}
        for sym, (code, code_len) in dist_canonical.items():
            dist_decode[(code, code_len)] = sym

        max_lit_len = max(ln for ln in self._STATIC_LIT_LENGTHS.values())
        max_dist_len = max(ln for ln in self._STATIC_DIST_LENGTHS.values())

        reader = BitReader(data[4:])
        result = bytearray()

        while True:
            bfinal = reader.read_bit()
            btype = reader.read_bits(2)

            if btype == 0:
                # Stored block: skip to byte boundary, read LEN/NLEN, copy bytes
                # Align to byte boundary
                _align_reader(reader)
                if reader.bits_remaining < 32:
                    raise ValueError("Unexpected end of stored block header")
                block_len = reader.read_uint16_le()
                _nlen = reader.read_uint16_le()  # one's complement of LEN
                for _ in range(block_len):
                    result.append(reader.read_byte())
            elif btype == 1:
                # Static Huffman
                while True:
                    code = 0
                    code_len = 0
                    found_eob = False
                    while code_len < max_lit_len + 1:
                        bit = reader.read_bit()
                        code = (code << 1) | bit
                        code_len += 1
                        sym = lit_decode.get((code, code_len))
                        if sym is not None:
                            if sym == 256:
                                # End of block
                                found_eob = True
                            elif sym < 256:
                                result.append(sym)
                            else:
                                # Length code
                                extra_bits = LENGTH_EXTRA_BITS[sym - 257]
                                extra_val = reader.read_bits(extra_bits) if extra_bits > 0 else 0
                                length = _code_to_length(sym, extra_val)
                                # Read distance
                                dist_code = 0
                                dist_code_len = 0
                                while dist_code_len < max_dist_len + 1:
                                    bit = reader.read_bit()
                                    dist_code = (dist_code << 1) | bit
                                    dist_code_len += 1
                                    d = dist_decode.get((dist_code, dist_code_len))
                                    if d is not None:
                                        dist_extra_bits = DIST_EXTRA_BITS[d]
                                        dist_extra_val = reader.read_bits(dist_extra_bits) if dist_extra_bits > 0 else 0
                                        distance = _code_to_distance(d, dist_extra_val)
                                        for _ in range(length):
                                            result.append(result[-distance])
                                        break
                            break  # break from inner code-scanning loop
                    if found_eob:
                        break
            elif btype == 2:
                raise NotImplementedError("Dynamic Huffman blocks not yet supported")
            else:
                raise ValueError(f"Invalid block type: {btype}")

            if bfinal == 1:
                break

        return bytes(result[:orig_len])


def _align_reader(reader: BitReader) -> None:
    """Align the reader to the next byte boundary."""
    while reader._bit_pos != 7:
        reader.read_bit()