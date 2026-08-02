"""Matrix file I/O: read and write matrices in CSV and JSON formats.

Supports loading matrices from files or strings, and writing them back.
Useful for piping data through the CLI or persisting results.

Supported formats
------------------

* **CSV** — comma- or whitespace-separated values, one row per line.
  Optionally a header row with column names.
* **JSON** — a 2-D array of numbers, optionally wrapped in an object
  ``{"matrix": [[...]], "shape": [m, n]}``.

Example
-------

>>> from matrix_decomp.file_io import save_csv, load_csv
>>> from matrix_decomp import Matrix
>>> save_csv(Matrix([[1, 2], [3, 4]]), "data.csv")  # writes file
>>> M = load_csv("data.csv")                         # reads it back
"""

from __future__ import annotations

import csv
import json
import os
from typing import List, Optional, Tuple

from .matrix import Matrix


def save_csv(matrix: Matrix, path: str, delimiter: str = ",", precision: int = 12) -> None:
    """Write a matrix to a CSV file.

    Parameters
    ----------
    matrix : Matrix
        The matrix to save.
    path : str
        Output file path.
    delimiter : str
        Field delimiter (default ``,``).
    precision : int
        Number of significant digits to keep (passed to ``repr``).
    """
    with open(path, "w", newline="") as f:
        writer = csv.writer(f, delimiter=delimiter)
        for row in matrix.data:
            writer.writerow([f"{v:.{precision}g}" for v in row])


def load_csv(path: str, delimiter: Optional[str] = None, skip_header: bool = False) -> Matrix:
    """Read a matrix from a CSV (or whitespace-delimited) file.

    If ``delimiter`` is ``None`` (default), the function auto-detects
    commas, semicolons, or whitespace.
    """
    rows: List[List[float]] = []
    with open(path, "r", newline="") as f:
        if delimiter is not None:
            reader = csv.reader(f, delimiter=delimiter)
            for i, line in enumerate(reader):
                if skip_header and i == 0:
                    continue
                if not line or all(c.strip() == "" for c in line):
                    continue
                rows.append([float(c.strip()) for c in line])
        else:
            for i, line in enumerate(f):
                if skip_header and i == 0:
                    continue
                line = line.strip()
                if not line:
                    continue
                if "," in line:
                    cells = line.split(",")
                elif ";" in line:
                    cells = line.split(";")
                else:
                    cells = line.split()
                rows.append([float(c.strip()) for c in cells])
    if not rows:
        raise ValueError(f"load_csv: no data rows found in {path!r}")
    return Matrix(rows)


def save_json(matrix: Matrix, path: str, wrapper: bool = False) -> None:
    """Write a matrix to a JSON file.

    If ``wrapper=True``, writes ``{"matrix": [[...]], "shape": [m, n]}``;
    otherwise writes a bare 2-D array.
    """
    payload: object
    if wrapper:
        payload = {"matrix": matrix.data, "shape": list(matrix.shape())}
    else:
        payload = matrix.data
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def load_json(path: str) -> Matrix:
    """Read a matrix from a JSON file (bare array or wrapped object)."""
    with open(path, "r") as f:
        obj = json.load(f)
    if isinstance(obj, list):
        return Matrix(obj)
    if isinstance(obj, dict) and "matrix" in obj:
        return Matrix(obj["matrix"])
    raise ValueError("load_json: expected a 2-D array or {'matrix': [...]}")


def parse_matrix_string(text: str) -> Matrix:
    """Parse a matrix from a string: JSON array, or semicolon/newline-separated
    rows with comma- or space-separated cells.
    """
    text = text.strip()
    if text.startswith("["):
        return Matrix(json.loads(text))
    rows: List[List[float]] = []
    for chunk in text.replace(";", "\n").split("\n"):
        chunk = chunk.strip()
        if not chunk:
            continue
        cells = [c.strip() for c in chunk.split(",")] if "," in chunk else chunk.split()
        rows.append([float(c) for c in cells])
    if not rows:
        raise ValueError("parse_matrix_string: no data found")
    return Matrix(rows)