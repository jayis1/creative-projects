"""
Parsers for various boolean function input formats.

Supported formats
-----------------
* **Truth table** — one value per line (0, 1, or - for don't-care).
* **Minterm list** — comma/space-separated integers, with optional ``d:`` prefix
  for don't-cares: ``4 8 10 11 d:9 14``.
* **SOP string** — ``AB'C + AC`` (delegates to ``BooleanFunction.from_sop``).
* **PLA** — simple Berkeley PLA format (.i/.o/.ilb/.obf/.p/.e directives).
"""

from __future__ import annotations

from typing import List, Tuple

from .boolean import BooleanFunction, TruthTable, var_names


def parse_truth_table(text: str, name: str = "f") -> BooleanFunction:
    """Parse a truth table from a block of text.

    Each non-empty, non-comment line is one entry.  Values may be
    0, 1, - (or 2 for don't-care).  The number of entries must be a power of
    two.
    """
    entries: List = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        # allow multi-character lines like "1 0 1 -"
        tokens = line.replace(",", " ").split()
        for tok in tokens:
            if tok in ("0", "1"):
                entries.append(int(tok))
            elif tok in ("-", "2", "x", "X"):
                entries.append("-")
            else:
                raise ValueError(f"invalid truth-table token {tok!r}")
    return BooleanFunction.from_truth_table(entries, name=name)


def parse_minterms(text: str, n_vars: int, name: str = "f") -> BooleanFunction:
    """Parse a minterm list.

    Format: ``minterms d: dontcares`` where the ``d:`` separator switches to
    don't-care mode.  Also accepts ``dc:`` or ``dc=``.

    Example::

        parse_minterms("4 8 10 11 12 15 d: 9 14", n_vars=4)
    """
    minterms: List[int] = []
    dontcare: List[int] = []
    mode = "m"
    tokens = text.replace(",", " ").split()
    for tok in tokens:
        low = tok.lower()
        if low in ("d:", "dc:", "dc=", "d=", "dc"):
            mode = "d"
            continue
        try:
            val = int(tok)
        except ValueError:
            raise ValueError(f"invalid minterm token {tok!r}")
        if mode == "m":
            minterms.append(val)
        else:
            dontcare.append(val)
    return BooleanFunction(
        n_vars=n_vars, minterms=minterms, dontcare=dontcare, name=name
    )


def parse_sop(sop: str, n_vars: int = None) -> BooleanFunction:  # type: ignore[assignment]
    """Parse a sum-of-products string."""
    return BooleanFunction.from_sop(sop, n_vars=n_vars)


def parse_pla(text: str) -> List[BooleanFunction]:
    """Parse a Berkeley PLA (Espresso) format text block.

    Supports single- and multi-output PLA.  Returns a list of
    :class:`BooleanFunction` objects, one per output.
    """
    lines = text.strip().splitlines()
    n_in: int = 0
    n_out: int = 0
    in_names: List[str] = []
    out_names: List[str] = []
    entries: List[Tuple[str, str]] = []  # (input_pat, output_pat)
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        directive = parts[0].lower()
        if directive == ".i":
            n_in = int(parts[1])
        elif directive == ".o":
            n_out = int(parts[1])
        elif directive == ".ilb":
            in_names = parts[1:]
        elif directive == ".ob" or directive == ".obf":
            out_names = parts[1:]
        elif directive == ".p":
            pass  # number of product lines follows
        elif directive == ".e":
            break
        elif directive.startswith("."):
            # skip unknown directives
            continue
        else:
            # a product line: input-pattern output-pattern
            if len(parts) >= 2:
                entries.append((parts[0], parts[1]))
    if n_in == 0:
        raise ValueError("PLA missing .i directive")
    if n_out == 0:
        n_out = 1
    if not in_names:
        in_names = var_names(n_in)
    if not out_names:
        out_names = [f"f{i}" for i in range(n_out)]
    # Build per-output minterm/dontcare lists
    per_output_mt: List[List[int]] = [[] for _ in range(n_out)]
    per_output_dc: List[List[int]] = [[] for _ in range(n_out)]
    for in_pat, out_pat in entries:
        if len(in_pat) != n_in:
            raise ValueError(
                f"input pattern {in_pat!r} length != .i ({n_in})"
            )
        if len(out_pat) != n_out:
            raise ValueError(
                f"output pattern {out_pat!r} length != .o ({n_out})"
            )
        # expand input pattern (may contain '-') into minterms
        minterms = _expand_pat(in_pat)
        for oi, sym in enumerate(out_pat):
            if sym == "1":
                per_output_mt[oi].extend(minterms)
            elif sym in ("-", "2"):
                per_output_dc[oi].extend(minterms)
            # 0 → nothing
    functions: List[BooleanFunction] = []
    for oi in range(n_out):
        functions.append(
            BooleanFunction(
                n_vars=n_in,
                minterms=per_output_mt[oi],
                dontcare=per_output_dc[oi],
                name=out_names[oi] if oi < len(out_names) else f"f{oi}",
            )
        )
    return functions


def _expand_pat(pattern: str) -> List[int]:
    """Expand a PLA input pattern (with '-') into minterm integers."""
    n = len(pattern)
    dash_positions = [i for i, c in enumerate(pattern) if c == "-"]
    base = 0
    for i, c in enumerate(pattern):
        if c == "1":
            base |= 1 << (n - 1 - i)
    result: List[int] = []
    for combo in range(1 << len(dash_positions)):
        val = base
        for j, pos in enumerate(dash_positions):
            if combo & (1 << (len(dash_positions) - 1 - j)):
                val |= 1 << (n - 1 - pos)
        result.append(val)
    return result