"""File operations: INCLUDE."""

import os

from forth.core import ForthError, _NextIdx


def register_file_ops(i) -> None:
    """Register file-related words on *i*."""

    # ── INCLUDE ( "filename" -- )  Load and evaluate a Forth source file ──
    def _include(i, t, n):
        if n + 1 >= len(t):
            raise ForthError("INCLUDE needs a filename")
        tok = t[n + 1]
        # Strip quotes if present
        if tok.startswith('"') and tok.endswith('"'):
            filename = tok[1:-1]
        else:
            filename = tok
        # Search relative to current file's directory, or cwd
        search_paths = [os.getcwd()]
        if hasattr(i, "_include_dir") and i._include_dir:
            search_paths.insert(0, i._include_dir)
        filepath = None
        for base in search_paths:
            candidate = os.path.join(base, filename)
            if os.path.isfile(candidate):
                filepath = candidate
                break
        if filepath is None:
            # Try as-is (absolute path)
            if os.path.isfile(filename):
                filepath = filename
            else:
                raise ForthError(f"INCLUDE: file not found: {filename}")
        old_dir = getattr(i, "_include_dir", None)
        i._include_dir = os.path.dirname(os.path.abspath(filepath))
        try:
            with open(filepath) as f:
                source = f.read()
            i.eval(source)
        finally:
            i._include_dir = old_dir
        return _NextIdx(n + 2)
    i._defining_words["INCLUDE"] = _include