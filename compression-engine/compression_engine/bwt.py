"""Burrows-Wheeler Transform codec with Move-to-Front, Run-Length Encoding, and CRC32 integrity."""

from __future__ import annotations

import struct
import zlib
from typing import Dict, List, Tuple
from .bitio import BitReader, BitWriter


def _bwt_transform(data: bytes) -> Tuple[bytes, int]:
    """Compute the Burrows-Wheeler Transform.

    Returns (transformed_data, original_index).
    """
    if not data:
        return b"", 0
    n = len(data)
    # Double the data to handle wrap-around comparison
    doubled = data + data
    indices = list(range(n))
    indices.sort(key=lambda i: doubled[i:i + n])

    # Find original index
    orig_idx = indices.index(0)
    # BWT output is the last column
    transformed = bytes(data[(i - 1) % n] for i in indices)
    return transformed, orig_idx


def _bwt_inverse(transformed: bytes, orig_idx: int) -> bytes:
    """Inverse Burrows-Wheeler Transform using the LF-mapping."""
    if not transformed or orig_idx < 0:
        return b""
    n = len(transformed)
    if n == 0:
        return b""

    # Count occurrences of each byte
    count = [0] * 256
    for b in transformed:
        count[b] += 1

    # Cumulative counts (starting positions for each byte in sorted order)
    cumul = [0] * 256
    total = 0
    for i in range(256):
        cumul[i] = total
        total += count[i]

    # Build LF-mapping
    lf_map = [0] * n
    occ_count = [0] * 256
    for i in range(n):
        b = transformed[i]
        lf_map[i] = cumul[b] + occ_count[b]
        occ_count[b] += 1

    # Reconstruct original
    result = bytearray(n)
    idx = orig_idx
    for i in range(n - 1, -1, -1):
        result[i] = transformed[idx]
        idx = lf_map[idx]
    return bytes(result)


def _move_to_front_encode(data: bytes) -> bytes:
    """Move-to-Front encoding.

    Maintains a list of symbols [0..255]. For each input byte, output its
    current index, then move it to the front.
    """
    alphabet = list(range(256))
    result = bytearray()
    for b in data:
        idx = alphabet.index(b)
        result.append(idx)
        alphabet.pop(idx)
        alphabet.insert(0, b)
    return bytes(result)


def _move_to_front_decode(data: bytes) -> bytes:
    """Move-to-Front decoding."""
    alphabet = list(range(256))
    result = bytearray()
    for idx in data:
        b = alphabet[idx]
        result.append(b)
        alphabet.pop(idx)
        alphabet.insert(0, b)
    return bytes(result)


def _rle_encode(data: bytes) -> bytes:
    """Run-Length Encoding for BWT output.

    Two identical consecutive bytes signal a run: the third byte gives
    the additional count (0-255), so total run = 2 + count.
    """
    if not data:
        return b""
    result = bytearray()
    i = 0
    while i < len(data):
        b = data[i]
        run = 1
        while i + run < len(data) and data[i + run] == b and run < 255:
            run += 1
        if run > 1:
            result.append(b)
            result.append(b)
            result.append(run - 2)  # two identical bytes signal a run
        else:
            result.append(b)
        i += run
    return bytes(result)


def _rle_decode(data: bytes) -> bytes:
    """Run-Length Decoding for BWT codec."""
    if not data:
        return b""
    result = bytearray()
    i = 0
    while i < len(data):
        b = data[i]
        if i + 1 < len(data) and data[i + 1] == b:
            # Run detected
            count = data[i + 2] + 2 if i + 2 < len(data) else 2
            result.extend([b] * count)
            i += 3
        else:
            result.append(b)
            i += 1
    return bytes(result)


class BWTCodec:
    """Burrows-Wheeler Transform codec with CRC32 integrity.

    Pipeline: BWT -> Move-to-Front -> RLE -> output

    Format:
    - 4 bytes: original length (little-endian)
    - 4 bytes: CRC32 checksum of original data (little-endian)
    - 4 bytes: BWT original index (little-endian)
    - N bytes: MTF+RLE encoded BWT output
    """

    def compress(self, data: bytes) -> bytes:
        """Compress using BWT + MTF + RLE."""
        checksum = zlib.crc32(data) & 0xFFFFFFFF

        if not data:
            return struct.pack("<IIII", 0, checksum, 0, 0)

        bwt_data, orig_idx = _bwt_transform(data)
        mtf_data = _move_to_front_encode(bwt_data)
        rle_data = _rle_encode(mtf_data)

        header = struct.pack("<IIII", len(data), checksum, orig_idx, len(rle_data))
        return header + rle_data

    def decompress(self, data: bytes) -> bytes:
        """Decompress BWT-coded data with CRC32 verification."""
        if len(data) < 16:
            raise ValueError("Data too short for BWT header")

        orig_len, expected_checksum, orig_idx, rle_len = struct.unpack("<IIII", data[:16])

        if orig_len == 0:
            actual_checksum = zlib.crc32(b"") & 0xFFFFFFFF
            if actual_checksum != expected_checksum:
                raise ValueError(f"CRC32 mismatch: expected {expected_checksum:#010x}, got {actual_checksum:#010x}")
            return b""

        payload = data[16:16 + rle_len]
        mtf_data = _rle_decode(payload)
        bwt_data = _move_to_front_decode(mtf_data)
        result = _bwt_inverse(bwt_data, orig_idx)
        result = result[:orig_len]

        actual_checksum = zlib.crc32(result) & 0xFFFFFFFF
        if actual_checksum != expected_checksum:
            raise ValueError(f"CRC32 mismatch: expected {expected_checksum:#010x}, got {actual_checksum:#010x}")
        return result