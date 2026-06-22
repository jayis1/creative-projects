"""Entropy (Huffman) coding of quantised DCT coefficient sequences.

This module implements the baseline (sequential) JPEG entropy coding:

  - DC coefficients: differential coding (diff from previous block of the
    same channel) then (SIZE, VALUE) Huffman coding.
  - AC coefficients: run-length of zeros + (SIZE, VALUE) coding, with
    the special symbols End-of-Block (0x00) and ZRL (0xF0).
"""

import numpy as np

from .bitio import BitWriter, BitReader
from .huffman import (
    magnitude_category, encode_value, decode_value,
    HuffmanTree,
)


def encode_block(coefficients_zz: np.ndarray,
                 prev_dc: int,
                 dc_table: dict,
                 ac_table: dict,
                 writer: BitWriter) -> int:
    """Entropy-encode one 64-coefficient (zig-zag) block.

    Parameters
    ----------
    coefficients_zz : np.ndarray
        64-element array of quantised coefficients in zig-zag order.
    prev_dc : int
        DC coefficient of the previous block in the same channel (for
        differential coding).
    dc_table, ac_table : dict
        Huffman ``{symbol: (code, length)}`` tables.
    writer : BitWriter
        Destination bit stream.

    Returns
    -------
    int
        The new ``prev_dc`` (this block's DC coefficient) to be passed
        to the next call.
    """
    # --- DC coefficient (differential) ---
    dc = int(coefficients_zz[0])
    diff = dc - prev_dc
    size = magnitude_category(diff)
    code, length = dc_table[size]
    writer.write_bits(code, length)
    if size > 0:
        writer.write_bits(encode_value(diff, size), size)

    # --- AC coefficients (run-length + magnitude) ---
    # Find the last non-zero AC coefficient.
    end = 63
    while end > 0 and coefficients_zz[end] == 0:
        end -= 1

    run = 0
    for i in range(1, end + 1):
        coeff = int(coefficients_zz[i])
        if coeff == 0:
            run += 1
            if run == 16:
                # ZRL: 16 zeros.
                code, length = ac_table[0xF0]
                writer.write_bits(code, length)
                run = 0
        else:
            # Emit (run, size) symbol.
            symbol = (run << 4) | magnitude_category(coeff)
            code, length = ac_table[symbol]
            writer.write_bits(code, length)
            writer.write_bits(encode_value(coeff, magnitude_category(coeff)),
                              magnitude_category(coeff))
            run = 0

    if end < 63:
        # End-of-block marker.
        code, length = ac_table[0x00]
        writer.write_bits(code, length)

    return dc


def decode_block(prev_dc: int,
                 dc_tree: HuffmanTree,
                 ac_tree: HuffmanTree,
                 reader: BitReader) -> tuple:
    """Entropy-decode one 64-coefficient block.

    Returns
    -------
    (np.ndarray, int)
        The 64-element zig-zag-ordered coefficient array and the new
        ``prev_dc`` value.
    """
    coeffs = np.zeros(64, dtype=np.int32)

    # --- DC ---
    size = _huff_decode_symbol(dc_tree, reader)
    if size > 0:
        bits = reader.read_bits(size)
        diff = decode_value(bits, size)
    else:
        diff = 0
    dc = prev_dc + diff
    coeffs[0] = dc

    # --- AC ---
    k = 1
    while k < 64:
        symbol = _huff_decode_symbol(ac_tree, reader)
        if symbol == 0x00:
            # End-of-block: remaining coefficients are zero.
            break
        # Run-length in high nibble, size in low nibble.
        run = (symbol >> 4) & 0xF
        size = symbol & 0xF
        if size == 0:
            # ZRL: skip 16 zeros.
            k += 16
            continue
        k += run
        if k >= 64:
            raise ValueError("AC coefficient index out of range during decode")
        bits = reader.read_bits(size)
        coeffs[k] = decode_value(bits, size)
        k += 1

    return coeffs, dc


def _huff_decode_symbol(tree: HuffmanTree, reader: BitReader) -> int:
    """Decode one Huffman symbol by walking the tree bit-by-bit."""
    node = tree
    while not node.is_leaf():
        bit = reader.read_bit()
        node = node.left if bit == 0 else node.right
        if node is None:
            raise ValueError("Invalid Huffman code in bit stream")
    return node.value