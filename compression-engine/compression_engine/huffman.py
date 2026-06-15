"""Huffman coding: canonical Huffman with bit-level I/O."""

from __future__ import annotations

import heapq
from typing import Dict, List, Optional, Tuple
from .bitio import BitReader, BitWriter


class _Node:
    """Internal node for Huffman tree construction."""

    __slots__ = ("freq", "symbol", "left", "right")

    def __init__(
        self,
        freq: int,
        symbol: Optional[int] = None,
        left: Optional["_Node"] = None,
        right: Optional["_Node"] = None,
    ) -> None:
        self.freq = freq
        self.symbol = symbol
        self.left = left
        self.right = right

    def __lt__(self, other: "_Node") -> bool:
        # Break ties deterministically by using a synthetic sort key
        if self.freq != other.freq:
            return self.freq < other.freq
        # Leaves (with symbol) sort before internal nodes
        if self.symbol is not None and other.symbol is not None:
            return self.symbol < other.symbol
        if self.symbol is not None:
            return True  # leaf < internal
        if other.symbol is not None:
            return False
        return False  # both internal, equal

    def is_leaf(self) -> bool:
        return self.symbol is not None


def _build_frequency_table(data: bytes) -> List[int]:
    """Build a 257-entry frequency table (0-255 byte values + 256 EOF symbol)."""
    freq = [0] * 257
    for b in data:
        freq[b] += 1
    freq[256] = 1  # EOF marker
    return freq


def _build_tree(freq: List[int]) -> _Node:
    """Build a Huffman tree from a frequency table."""
    heap: List[_Node] = []
    for symbol in range(257):
        if freq[symbol] > 0:
            heapq.heappush(heap, _Node(freq[symbol], symbol=symbol))
    if len(heap) == 0:
        raise ValueError("Cannot build Huffman tree from empty data")
    if len(heap) == 1:
        # Single symbol: create a dummy parent so we have at least 2 leaves
        node = heapq.heappop(heap)
        dummy = _Node(node.freq, left=node, right=_Node(0, symbol=0))
        heapq.heappush(heap, dummy)
    while len(heap) > 1:
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)
        parent = _Node(left.freq + right.freq, left=left, right=right)
        heapq.heappush(heap, parent)
    return heap[0]


def _build_code_table(node: _Node, prefix: int = 0, length: int = 0) -> Dict[int, Tuple[int, int]]:
    """Build a code table: symbol -> (code, bit_length)."""
    table: Dict[int, Tuple[int, int]] = {}
    if node.is_leaf():
        # A single-symbol tree gets code 0, length 1
        if length == 0:
            table[node.symbol] = (0, 1)
        else:
            table[node.symbol] = (prefix, length)
        return table
    if node.left:
        table.update(_build_code_table(node.left, prefix << 1, length + 1))
    if node.right:
        table.update(_build_code_table(node.right, (prefix << 1) | 1, length + 1))
    return table


def _lengths_to_canonical(lengths: Dict[int, int]) -> Dict[int, Tuple[int, int]]:
    """Convert bit-lengths to canonical Huffman codes.

    Canonical ordering: shorter codes first, then by symbol value.
    Algorithm:
    1. Sort symbols by (length, symbol)
    2. Start with code 0 at the first (shortest) length
    3. For each next symbol: code = (prev_code + 1) << (length_diff)
    """
    symbols_by_len = sorted(
        ((sym, ln) for sym, ln in lengths.items() if ln > 0),
        key=lambda x: (x[1], x[0]),
    )
    if not symbols_by_len:
        return {}
    result: Dict[int, Tuple[int, int]] = {}
    code = 0
    prev_len = symbols_by_len[0][1]
    for sym, ln in symbols_by_len:
        code <<= (ln - prev_len)
        result[sym] = (code, ln)
        code += 1
        prev_len = ln
    return result


class HuffmanCodec:
    """Huffman coding codec with canonical code serialization.

    Format:
    - 4 bytes: original data length (little-endian, unsigned)
    - 1 byte: number of code length entries (N)
    - N entries, each: 2 bytes symbol (uint16 LE) + 1 byte code length
    - Compressed bitstream using canonical Huffman codes
    - Terminated by EOF symbol (256) code
    """

    MAX_CODE_LENGTH = 32

    def compress(self, data: bytes) -> bytes:
        """Compress data using Huffman coding."""
        if len(data) > 0xFFFFFFFF:
            raise ValueError("Data too large for Huffman codec (max ~4GB)")

        if not data:
            writer = BitWriter()
            # 4-byte original length (0)
            for shift in range(0, 32, 8):
                writer.write_byte(0)
            # 2-byte entry count (0)
            writer.write_uint16_le(0)
            return writer.flush()

        freq = _build_frequency_table(data)
        tree = _build_tree(freq)
        raw_codes = _build_code_table(tree)
        # Get lengths only
        lengths = {sym: ln for sym, (_, ln) in raw_codes.items()}
        # Build canonical codes from lengths
        canonical = _lengths_to_canonical(lengths)

        writer = BitWriter()
        # Write original length as 4 bytes LE
        for shift in range(0, 32, 8):
            writer.write_byte((len(data) >> shift) & 0xFF)
        # Write code length table: 2-byte entry count (supports up to 65535)
        entries = sorted(lengths.items())
        writer.write_uint16_le(len(entries))
        for sym, ln in entries:
            # Write symbol as 2 bytes LE (supports 0-65535, including EOF=256)
            writer.write_byte(sym & 0xFF)
            writer.write_byte((sym >> 8) & 0xFF)
            writer.write_byte(ln)
        # Encode data
        for b in data:
            code, code_len = canonical[b]
            writer.write_bits(code, code_len)
        # Write EOF marker
        eof_code, eof_len = canonical[256]
        writer.write_bits(eof_code, eof_len)
        return writer.flush()

    def decompress(self, data: bytes) -> bytes:
        """Decompress Huffman-coded data."""
        reader = BitReader(data)
        # Read original length as 4 bytes LE
        orig_len = 0
        for shift in range(0, 32, 8):
            orig_len |= reader.read_byte() << shift
        if orig_len == 0:
            _num_entries = reader.read_uint16_le()
            return b""
        num_entries = reader.read_uint16_le()
        lengths: Dict[int, int] = {}
        for _ in range(num_entries):
            sym_low = reader.read_byte()
            sym_high = reader.read_byte()
            sym = (sym_high << 8) | sym_low
            ln = reader.read_byte()
            lengths[sym] = ln
        # Build canonical codes from lengths
        canonical = _lengths_to_canonical(lengths)
        # Build decode table: (code, length) -> symbol
        decode_table: Dict[Tuple[int, int], int] = {}
        for sym, (code, code_len) in canonical.items():
            decode_table[(code, code_len)] = sym

        max_len = max(ln for ln in lengths.values()) if lengths else 0
        result = bytearray()
        while len(result) < orig_len:
            code = 0
            code_len = 0
            while code_len <= max_len:
                bit = reader.read_bit()
                code = (code << 1) | bit
                code_len += 1
                sym = decode_table.get((code, code_len))
                if sym is not None:
                    if sym == 256:  # EOF
                        return bytes(result)
                    result.append(sym)
                    break
            else:
                raise ValueError(f"Invalid Huffman code encountered at position {len(result)}")
        return bytes(result)