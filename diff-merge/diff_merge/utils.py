"""
Text preprocessing utilities for diff operations.

Supports whitespace normalization, blank-line filtering, and other
common preprocessing options.
"""

from __future__ import annotations

from typing import List, Tuple

from .config import Config

__all__ = ["preprocess_lines", "reverse_ops"]


def preprocess_lines(
    lines: List[str], config: Config
) -> Tuple[List[str], List[int]]:
    """Preprocess lines according to config settings.

    Returns (processed_lines, original_indices) where original_indices[i]
    maps processed line i back to its index in the original list.
    """
    processed: List[str] = []
    indices: List[int] = []

    for i, line in enumerate(lines):
        line_stripped = line

        if config.ignore_whitespace:
            # Normalize internal whitespace and strip leading/trailing
            line_stripped = " ".join(line.split())
        else:
            line_stripped = line.rstrip("\n\r")

        if config.ignore_blank_lines:
            if not line_stripped.strip():
                continue

        processed.append(line_stripped)
        indices.append(i)

    return processed, indices


def reverse_ops(ops):
    """Reverse a list of DiffOps (swap a↔b, INSERT↔DELETE).

    This produces a diff that, when applied as a patch, reverses the
    original diff.
    """
    from .myers import DiffOp, Operation

    reversed_ops = []
    for op in ops:
        if op.tag == Operation.EQUAL:
            reversed_ops.append(DiffOp(Operation.EQUAL, op.j1, op.j2, op.i1, op.i2))
        elif op.tag == Operation.DELETE:
            reversed_ops.append(DiffOp(Operation.INSERT, op.j1, op.j2, op.i1, op.i2))
        elif op.tag == Operation.INSERT:
            reversed_ops.append(DiffOp(Operation.DELETE, op.j1, op.j2, op.i1, op.i2))
        elif op.tag == Operation.REPLACE:
            reversed_ops.append(DiffOp(Operation.REPLACE, op.j1, op.j2, op.i1, op.i2))
    return reversed_ops


def is_binary(data: bytes) -> bool:
    """Detect whether *data* is binary (not text).

    Uses a simple heuristic: if the data contains null bytes or more
    than 30% non-text bytes, it's considered binary.
    """
    if not data:
        return False
    if b"\x00" in data:
        return True
    # Check for high proportion of non-text bytes
    text_chars = bytes(range(32, 127)) + b"\n\r\t\f\b"
    nontext = sum(1 for byte in data if byte not in text_chars)
    return nontext / len(data) > 0.30