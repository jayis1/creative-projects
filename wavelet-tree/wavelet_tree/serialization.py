"""JSON serialization for wavelet tree structures."""

from __future__ import annotations

import json
from typing import Any

from .wavelet_tree import WaveletTree
from .wavelet_matrix import WaveletMatrix
from .huffman import HuffmanWaveletTree, HuffmanWaveletMatrix


def _symbol_to_jsonable(sym: Any) -> Any:
    """Convert a symbol to a JSON-serializable value.

    For single-character strings, the symbol is stored as-is.
    For other types (int, float, multi-char strings, etc.), we store
    a {"type": ..., "value": ...} wrapper so the type survives the roundtrip.
    """
    if isinstance(sym, str) and len(sym) == 1:
        return sym
    if isinstance(sym, int) and not isinstance(sym, bool):
        return {"type": "int", "value": sym}
    if isinstance(sym, float):
        return {"type": "float", "value": sym}
    if isinstance(sym, bool):
        return {"type": "bool", "value": sym}
    if isinstance(sym, str):
        return {"type": "str", "value": sym}
    # Fallback: store repr
    return {"type": "repr", "value": repr(sym)}


def _jsonable_to_symbol(val: Any) -> Any:
    """Convert a JSON-loaded value back to a symbol."""
    if isinstance(val, str):
        return val
    if isinstance(val, dict):
        t = val.get("type")
        v = val.get("value")
        if t == "int":
            return int(v)
        if t == "float":
            return float(v)
        if t == "bool":
            return bool(v)
        if t == "str":
            return str(v)
        if t == "repr":
            # We can't safely eval, so return as string
            return v
    return val


def save(obj, path: str) -> None:
    """Save a wavelet tree/matrix to a JSON file.

    Stores the original sequence and the structure type so it can be
    reconstructed on load.
    """
    if isinstance(obj, WaveletTree):
        seq = obj._sequence
        data = {
            "type": "WaveletTree",
            "sequence": [_symbol_to_jsonable(s) for s in seq],
            "alphabet": [_symbol_to_jsonable(s) for s in obj.alphabet],
        }
    elif isinstance(obj, WaveletMatrix):
        data = {
            "type": "WaveletMatrix",
            "sequence": [_symbol_to_jsonable(s) for s in obj._original_sequence],
            "alphabet": [_symbol_to_jsonable(s) for s in obj.alphabet],
        }
    elif isinstance(obj, (HuffmanWaveletTree, HuffmanWaveletMatrix)):
        data = {
            "type": type(obj).__name__,
            "sequence": [_symbol_to_jsonable(s) for s in obj._original_sequence],
            "alphabet": [_symbol_to_jsonable(s) for s in obj.alphabet],
            "codes": {
                json.dumps(_symbol_to_jsonable(k)): v
                for k, v in obj.codes.items()
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

    seq = [_jsonable_to_symbol(s) for s in data["sequence"]]
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