"""JSON serialization for wavelet tree structures."""

from __future__ import annotations

import json
from typing import Any

from .wavelet_tree import WaveletTree
from .wavelet_matrix import WaveletMatrix
from .huffman import HuffmanWaveletTree, HuffmanWaveletMatrix


def _symbol_to_str(sym: Any) -> str:
    """Convert a symbol to a JSON-serializable string."""
    if isinstance(sym, str):
        return sym
    return repr(sym)


def _str_to_symbol(s: str) -> Any:
    """Convert a string back to a symbol."""
    # If it's a single character, return as char
    if len(s) == 1:
        return s
    # If it looks like a repr, try to eval it safely
    if s.startswith("'") and s.endswith("'") and len(s) >= 2:
        inner = s[1:-1]
        if len(inner) == 1:
            return inner
    return s


def save(obj, path: str) -> None:
    """Save a wavelet tree/matrix to a JSON file.

    Stores the original sequence and the structure type so it can be
    reconstructed on load.
    """
    if isinstance(obj, WaveletTree):
        seq = obj._sequence
        data = {
            "type": "WaveletTree",
            "sequence": [_symbol_to_str(s) for s in seq],
            "alphabet": [_symbol_to_str(s) for s in obj.alphabet],
        }
    elif isinstance(obj, WaveletMatrix):
        data = {
            "type": "WaveletMatrix",
            "sequence": [_symbol_to_str(s) for s in obj._original_sequence],
            "alphabet": [_symbol_to_str(s) for s in obj.alphabet],
        }
    elif isinstance(obj, (HuffmanWaveletTree, HuffmanWaveletMatrix)):
        data = {
            "type": type(obj).__name__,
            "sequence": [_symbol_to_str(s) for s in obj._original_sequence],
            "alphabet": [_symbol_to_str(s) for s in obj.alphabet],
            "codes": {
                _symbol_to_str(k): v for k, v in obj.codes.items()
            },
        }
    else:
        raise TypeError(f"Cannot serialize object of type {type(obj)}")

    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load(path: str):
    """Load a wavelet tree/matrix from a JSON file."""
    with open(path) as f:
        data = json.load(f)

    seq = [_str_to_symbol(s) for s in data["sequence"]]
    struct_type = data["type"]

    if struct_type == "WaveletTree":
        return WaveletTree(seq)
    elif struct_type == "WaveletMatrix":
        return WaveletMatrix(seq)
    elif struct_type == "HuffmanWaveletTree":
        return HuffmanWaveletTree(seq)
    elif struct_type == "HuffmanWaveletMatrix":
        return HuffmanWaveletMatrix(seq)
    else:
        raise ValueError(f"Unknown structure type: {struct_type}")