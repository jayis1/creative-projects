"""Burrows-Wheeler Transform codec with Move-to-Front and Run-Length Encoding."""

from __future__ import annotations

from typing import List, Tuple
from .bitio import BitReader, BitWriter


def _bwt_transform(data: bytes) -> Tuple[bytes, int]:
    """Compute the Burrows-Wheeler Transform.

    Returns (transformed_data, original_index).
    Uses suffix-array-like approach for efficiency.
    """
    if not data:
        return b"", 0
    n = len(data)
    # Create all rotations' indices and sort by the rotation
    # To avoid creating n strings, we use index-based comparison
    indices = list(range(n))

    # Double the data to handle wrap-around comparison
    doubled = data + data

    def compare_rotations(i: int, j: int) -> bool:
        """Compare rotation starting at i vs j."""
        for k in range(n):
            ci = doubled[i + k]
            cj = doubled[j + k]
            if ci != cj:
                return ci < cj
        return False  # equal

    # For small data, use Python sort with a key function
    # For larger data, we'd want a suffix array, but this works for moderate sizes
    try:
        indices.sort(key=lambda i: doubled[i:i + n])
    except MemoryError:
        # Fallback: use comparison-based sort
        import functools
        indices.sort(key=functools.cmp_to_key(lambda i, j: -1 if doubled[i:i+n] < doubled[j:j+n] else (1 if doubled[i:i+n] > doubled[j:j+n] else 0)))

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

    Format: for each run of identical bytes:
    - If run length <= 1: just output the byte
    - If run length > 1: output the byte, then the count-1
    We use a simple scheme: escape byte 0xFF followed by count.
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
    """Burrows-Wheeler Transform codec.

    Pipeline: BWT -> Move-to-Front -> RLE -> output

    Format:
    - 4 bytes: original length (little-endian)
    - 4 bytes: BWT original index (little-endian)
    - N bytes: MTF+RLE encoded BWT output
    """

    def compress(self, data: bytes) -> bytes:
        """Compress using BWT + MTF + RLE."""
        if not data:
            return struct_header(0, 0)

        bwt_data, orig_idx = _bwt_transform(data)
        mtf_data = _move_to_front_encode(bwt_data)
        rle_data = _rle_encode(mtf_data)

        return struct_header(len(data), orig_idx) + rle_data

    def decompress(self, data: bytes) -> bytes:
        """Decompress BWT-coded data."""
        orig_len, orig_idx, payload = parse_header(data)
        if orig_len == 0:
            return b""

        mtf_data = _rle_decode(payload)
        bwt_data = _move_to_front_decode(mtf_data)
        result = _bwt_inverse(bwt_data, orig_idx)
        return result[:orig_len]


def struct_header(length: int, index: int) -> bytes:
    """Pack a header: 4 bytes length + 4 bytes index, little-endian."""
    import struct
    return struct.pack("<II", length, index)


def parse_header(data: bytes) -> tuple:
    """Parse header: returns (length, index, remaining_payload)."""
    import struct
    if len(data) < 8:
        raise ValueError("Data too short for BWT header")
    length, index = struct.unpack("<II", data[:8])
    return length, index, data[8:]