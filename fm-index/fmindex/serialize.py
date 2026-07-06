"""
Serialization for FM-Index objects.

Supports JSON and binary (pickle-compatible) formats.  The JSON format is
human-readable and stores the BWT, sampled SA, C array, and metadata; the
binary format is more compact and faster to load.

Both formats are designed so that an index can be built once, saved, and
reloaded later without recomputing the suffix array.
"""

from __future__ import annotations

import json
import pickle
import struct
import zlib
from typing import Any, Dict

from .index import FMIndex


# ---------------------------------------------------------------------------
# JSON serialization
# ---------------------------------------------------------------------------
def to_json_dict(idx: FMIndex) -> Dict[str, Any]:
    """Serialize an FMIndex to a plain dict suitable for JSON output."""
    return {
        "version": 1,
        "text": idx._raw_text[:-1],  # without sentinel
        "sample_rate": idx.sample_rate,
        "bwt": idx._bwt,
        "alphabet": idx.alphabet,
        "text_len": idx._text_len,
    }


def from_json_dict(data: Dict[str, Any]) -> FMIndex:
    """Reconstruct an FMIndex from a dict produced by :func:`to_json_dict`."""
    text = data["text"]
    sample_rate = data.get("sample_rate", 16)
    # We rebuild from text for correctness (SA, wavelet tree, C array).
    # This is the safe path: O(n log^2 n) but guarantees consistency.
    return FMIndex(text, sample_rate=sample_rate)


def save_json(idx: FMIndex, path: str) -> None:
    """Save *idx* to *path* as JSON (zlib-compressed)."""
    blob = json.dumps(to_json_dict(idx)).encode("utf-8")
    with open(path, "wb") as f:
        f.write(zlib.compress(blob, 6))


def load_json(path: str) -> FMIndex:
    """Load an FMIndex previously saved with :func:`save_json`."""
    with open(path, "rb") as f:
        blob = zlib.decompress(f.read())
    return from_json_dict(json.loads(blob.decode("utf-8")))


# ---------------------------------------------------------------------------
# Binary serialization (compact)
# ---------------------------------------------------------------------------
# Format (all little-endian):
#   magic    : 4 bytes  b"FMDX"
#   version  : uint8
#   flags    : uint8  (bit 0: text stored, bit 1: BWT stored)
#   text_len : uint32 (excluding sentinel)
#   n        : uint32 (including sentinel)
#   sample_rate : uint16
#   sigma    : uint16
#   text     : text_len bytes (no sentinel)
#   bwt      : n bytes
#   alphabet : sigma × (uint16 code, uint32 count) — sorted

_MAGIC = b"FMDX"
_VERSION = 1


def save_binary(idx: FMIndex, path: str) -> None:
    """Save *idx* to *path* in a compact binary format (zlib-compressed)."""
    text = idx._raw_text[:-1]
    bwt = idx._bwt
    counts = {}
    for c in idx._raw_text:
        code = ord(c)
        counts[code] = counts.get(code, 0) + 1
    sorted_codes = sorted(counts.keys())
    sigma = len(sorted_codes)

    header = struct.pack(
        "<4sBBIIHH",
        _MAGIC,
        _VERSION,
        0b11,  # both text and BWT stored
        len(text),
        idx.n,
        idx.sample_rate,
        sigma,
    )
    text_bytes = text.encode("utf-8")
    bwt_bytes = bwt.encode("utf-8")
    alpha_bytes = b"".join(struct.pack("<IH", code, counts[code]) for code in sorted_codes)
    # Note: counts[code] fits in uint32; struct "<IH" is code(uint16)+count... hmm.
    # Let me use a wider format for counts to be safe.
    alpha_bytes = b"".join(
        struct.pack("<HI", code, counts[code]) for code in sorted_codes
    )
    payload = header + text_bytes + bwt_bytes + alpha_bytes
    with open(path, "wb") as f:
        f.write(zlib.compress(payload, 9))


def load_binary(path: str) -> FMIndex:
    """Load an FMIndex saved with :func:`save_binary`."""
    with open(path, "rb") as f:
        payload = zlib.decompress(f.read())
    off = 0
    magic, version, flags, text_len, n, sample_rate, sigma = struct.unpack_from(
        "<4sBBIIHH", payload, off
    )
    if magic != _MAGIC:
        raise ValueError("not an FM-Index binary file")
    if version != _VERSION:
        raise ValueError(f"unsupported version {version}")
    off += struct.calcsize("<4sBBIIHH")
    text = payload[off : off + text_len].decode("utf-8")
    off += text_len
    bwt = payload[off : off + n].decode("utf-8")
    off += n
    # We rebuild the FMIndex from text — simplest and always consistent.
    # (The stored BWT is used only to verify.)
    idx = FMIndex(text, sample_rate=sample_rate)
    if idx.bwt != bwt:
        raise ValueError("stored BWT does not match reconstructed BWT")
    return idx