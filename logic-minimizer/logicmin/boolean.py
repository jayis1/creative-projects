"""
Core boolean algebra primitives: BooleanFunction, TruthTable, Implicant.

Conventions
-----------
* Variables are named A, B, C, ... (A is the most significant bit).
* A *cube* (implicant) is a string over {'0','1','-'} of length n_vars.
    '1'  → variable asserted in the product term
    '0'  → variable negated
    '-'  → variable absent (don't care position in the implicant)
* A *minterm* is an integer whose binary representation (n_vars bits wide)
  specifies a single input combination for which the function is 1.
"""

from __future__ import annotations

from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Variable naming
# ---------------------------------------------------------------------------

def var_names(n: int) -> List[str]:
    """Return ``n`` variable names starting from A (MSB)."""
    if n <= 0:
        raise ValueError("n_vars must be positive")
    if n > 26:
        return [f"x{i}" for i in range(n)]
    return [chr(ord("A") + i) for i in range(n)]


def minterm_to_cube(minterm: int, n_vars: int) -> str:
    """Convert an integer minterm to a cube string of length ``n_vars``."""
    if minterm < 0:
        raise ValueError("minterm must be non-negative")
    if minterm >= (1 << n_vars):
        raise ValueError(
            f"minterm {minterm} requires at least {minterm.bit_length()} vars, "
            f"but n_vars={n_vars}"
        )
    return format(minterm, f"0{n_vars}b")


def cube_to_minterms(cube: str) -> List[int]:
    """Expand a cube (with '-' wildcards) into its covered minterm integers."""
    minterms: List[int] = []
    dash_positions = [i for i, c in enumerate(cube) if c == "-"]
    n_dashes = len(dash_positions)
    base = 0
    for i, c in enumerate(cube):
        if c == "1":
            base |= 1 << (len(cube) - 1 - i)
    for combo in range(1 << n_dashes):
        val = base
        for j, pos in enumerate(dash_positions):
            if combo & (1 << (n_dashes - 1 - j)):
                val |= 1 << (len(cube) - 1 - pos)
        minterms.append(val)
    return sorted(minterms)


def cube_covers(cube: str, minterm: int) -> bool:
    """Return True if ``cube`` covers ``minterm``."""
    n = len(cube)
    if minterm < 0 or minterm >= (1 << n):
        return False
    bits = format(minterm, f"0{n}b")
    for c, b in zip(cube, bits):
        if c != "-" and c != b:
            return False
    return True


# ---------------------------------------------------------------------------
# Implicant
# ---------------------------------------------------------------------------

class Implicant:
    """A prime implicant represented as a cube with coverage bookkeeping.

    Parameters
    ----------
    cube : str
        String over {'0','1','-'}.
    minterms : iterable of int, optional
        Minterms covered; auto-derived if not supplied.
    """

    __slots__ = ("cube", "minterms", "_hash")

    def __init__(self, cube: str, minterms: Optional[Iterable[int]] = None) -> None:
        self._validate_cube(cube)
        self.cube = cube
        if minterms is None:
            self.minterms = frozenset(cube_to_minterms(cube))
        else:
            self.minterms = frozenset(minterms)
        self._hash = hash(self.cube)

    @staticmethod
    def _validate_cube(cube: str) -> None:
        if not cube:
            raise ValueError("cube must be non-empty")
        for c in cube:
            if c not in "01-":
                raise ValueError(f"invalid cube character {c!r}")

    @property
    def n_vars(self) -> int:
        return len(self.cube)

    @property
    def n_literals(self) -> int:
        """Number of specified (non-dash) positions."""
        return sum(1 for c in self.cube if c != "-")

    @property
    def n_dashes(self) -> int:
        return sum(1 for c in self.cube if c == "-")

    @property
    def size(self) -> int:
        """Number of minterms covered (2 ** n_dashes)."""
        return 1 << self.n_dashes

    def covers(self, minterm: int) -> bool:
        return cube_covers(self.cube, minterm)

    def sop_term(self, names: Optional[Sequence[str]] = None) -> str:
        """Render as a product term, e.g. ``AB'C``."""
        names = names or var_names(len(self.cube))
        parts = []
        for i, c in enumerate(self.cube):
            if c == "1":
                parts.append(names[i])
            elif c == "0":
                parts.append(names[i] + "'")
        return "".join(parts) if parts else "1"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Implicant):
            return NotImplemented
        return self.cube == other.cube

    def __hash__(self) -> int:
        return self._hash

    def __repr__(self) -> str:
        return f"Implicant({self.cube!r})"

    def __lt__(self, other: "Implicant") -> bool:
        return self.cube < other.cube


def can_merge(a: str, b: str) -> Optional[str]:
    """Try to merge two cubes that differ in exactly one position.

    Returns the merged cube (with a dash at the differing position) or None.
    """
    # Bug fix: validate that both cubes have the same length.
    # Previously, zip() silently truncated mismatched-length cubes, which
    # could produce incorrect merges (e.g. can_merge("01", "110") returned
    # "-1" by only comparing the first 2 characters).
    if len(a) != len(b):
        return None
    diff = -1
    for i, (ca, cb) in enumerate(zip(a, b)):
        if ca != cb:
            if diff != -1:
                return None
            # dashes must match to merge; a dash-vs-literal is never combinable
            if ca == "-" or cb == "-":
                return None
            diff = i
    if diff == -1:
        return None  # identical cubes
    return a[:diff] + "-" + a[diff + 1:]


# ---------------------------------------------------------------------------
# BooleanFunction
# ---------------------------------------------------------------------------

class BooleanFunction:
    """A boolean function described by minterms and don't-cares.

    Parameters
    ----------
    n_vars : int
        Number of input variables.
    minterms : iterable of int
        Input combinations where f = 1.
    dontcare : iterable of int
        Input combinations that are unconstrained (may be 0 or 1).
    name : str
        Optional function name (for multi-output contexts).
    """

    def __init__(
        self,
        n_vars: int,
        minterms: Iterable[int] = (),
        dontcare: Iterable[int] = (),
        name: str = "f",
    ) -> None:
        if n_vars <= 0:
            raise ValueError("n_vars must be positive")
        if n_vars > 64:
            raise ValueError("n_vars > 64 is not supported")
        self.n_vars = n_vars
        self.name = name
        max_val = (1 << n_vars) - 1
        mt = set(minterms)
        dc = set(dontcare)
        overlap = mt & dc
        if overlap:
            raise ValueError(
                f"minterms and dontcare overlap: {sorted(overlap)}"
            )
        for v in mt | dc:
            if v < 0 or v > max_val:
                raise ValueError(
                    f"value {v} out of range for {n_vars} variables (0..{max_val})"
                )
        self.minterms = frozenset(mt)
        self.dontcare = frozenset(dc)

    # -- construction helpers ------------------------------------------------

    @classmethod
    def from_truth_table(cls, table: Sequence[int], name: str = "f") -> "BooleanFunction":
        """Build from a truth table where index = minterm and value ∈ {0,1,'-'}.

        ``'-'`` or ``2`` or ``None`` means don't-care.
        """
        n = (len(table) - 1).bit_length()
        if 1 << n != len(table):
            # pad to next power of two? No — require exact power of two.
            raise ValueError(
                f"truth table length {len(table)} is not a power of two"
            )
        mt: List[int] = []
        dc: List[int] = []
        for i, v in enumerate(table):
            if v in (1, "1", True):
                mt.append(i)
            elif v in (0, "0", False):
                pass
            elif v in ("-", 2, None):
                dc.append(i)
            else:
                raise ValueError(f"invalid truth-table entry {v!r} at index {i}")
        return cls(n_vars=n, minterms=mt, dontcare=dc, name=name)

    @classmethod
    def from_sop(cls, sop: str, n_vars: Optional[int] = None) -> "BooleanFunction":
        """Build from a sum-of-products string like ``AB'C + AC``.

        ``n_vars`` is inferred from the widest product term if not given.
        """
        terms = [t.strip() for t in sop.split("+") if t.strip()]
        if not terms:
            raise ValueError("empty SOP expression")
        # detect variable letters
        letters: set[str] = set()
        for t in terms:
            i = 0
            while i < len(t):
                ch = t[i]
                if ch.isalpha():
                    letters.add(ch.upper())
                    i += 1
                    if i < len(t) and t[i] == "'":
                        i += 1
                else:
                    i += 1
        if n_vars is None:
            # Bug fix: infer n_vars from the highest letter position, not
            # the count of distinct letters.  "AC" implies 3 vars (A,B,C)
            # with B as don't-care, not 2 vars.
            if not letters:
                raise ValueError("no variable letters found in SOP expression")
            max_letter = max(ord(c) for c in letters)
            n_vars = max_letter - ord("A") + 1
            if n_vars > 26:
                raise ValueError(f"too many variables (>{26}) in SOP expression")
        # map letter -> position
        var_idx = {name: i for i, name in enumerate(var_names(n_vars))}
        minterms: List[int] = []
        for term in terms:
            cube = ["-"] * n_vars
            i = 0
            while i < len(term):
                ch = term[i].upper()
                if ch.isalpha():
                    if ch not in var_idx:
                        raise ValueError(f"unknown variable {ch!r} in term {term!r}")
                    pos = var_idx[ch]
                    val = "1"
                    i += 1
                    if i < len(term) and term[i] == "'":
                        val = "0"
                        i += 1
                    if cube[pos] != "-":
                        raise ValueError(
                            f"variable {ch} appears twice in term {term!r}"
                        )
                    cube[pos] = val
                else:
                    raise ValueError(f"unexpected character {ch!r} in term {term!r}")
            minterms.extend(cube_to_minterms("".join(cube)))
        return cls(n_vars=n_vars, minterms=minterms, name="f")

    # -- queries -------------------------------------------------------------

    @property
    def var_names(self) -> List[str]:
        return var_names(self.n_vars)

    @property
    def all_minterms(self) -> frozenset[int]:
        """minterms ∪ dontcare — every point where f may be 1."""
        return self.minterms | self.dontcare

    def eval(self, *args: int) -> int:
        """Evaluate at the given input values (MSB first)."""
        if len(args) != self.n_vars:
            raise ValueError(
                f"expected {self.n_vars} arguments, got {len(args)}"
            )
        idx = 0
        for v in args:
            if v not in (0, 1):
                raise ValueError("arguments must be 0 or 1")
            idx = (idx << 1) | v
        if idx in self.minterms:
            return 1
        if idx in self.dontcare:
            return -1  # unspecified
        return 0

    def truth_table(self) -> TruthTable:
        """Return the full truth table (with '-' for don't-cares)."""
        entries: List = []
        for i in range(1 << self.n_vars):
            if i in self.minterms:
                entries.append(1)
            elif i in self.dontcare:
                entries.append("-")
            else:
                entries.append(0)
        return TruthTable(entries, self.n_vars)

    def __repr__(self) -> str:
        return (
            f"BooleanFunction(n_vars={self.n_vars}, "
            f"minterms={sorted(self.minterms)}, "
            f"dontcare={sorted(self.dontcare)}, name={self.name!r})"
        )


# ---------------------------------------------------------------------------
# TruthTable
# ---------------------------------------------------------------------------

class TruthTable:
    """A truth table of length 2**n with values in {0, 1, '-'}."""

    def __init__(self, entries: Sequence, n_vars: Optional[int] = None) -> None:
        if n_vars is None:
            n_vars = (len(entries) - 1).bit_length()
            if 1 << n_vars != len(entries):
                raise ValueError("length must be a power of two")
        if len(entries) != (1 << n_vars):
            raise ValueError(
                f"expected {1 << n_vars} entries for {n_vars} vars, "
                f"got {len(entries)}"
            )
        self.n_vars = n_vars
        self.entries: List = list(entries)

    def __len__(self) -> int:
        return len(self.entries)

    def __getitem__(self, idx: int) -> object:
        return self.entries[idx]

    def __iter__(self) -> Iterator:
        return iter(self.entries)

    def to_function(self, name: str = "f") -> BooleanFunction:
        return BooleanFunction.from_truth_table(self.entries, name=name)

    def __repr__(self) -> str:
        return f"TruthTable(n_vars={self.n_vars}, entries={self.entries})"

    def render_ascii(self) -> str:
        """Render the truth table as an aligned ASCII table."""
        names = var_names(self.n_vars)
        header = " ".join(names) + " | f"
        sep = "-" * len(header)
        lines = [header, sep]
        for i, v in enumerate(self.entries):
            bits = format(i, f"0{self.n_vars}b")
            sym = str(v) if v != "-" else "-"
            lines.append(f"{' '.join(bits)} | {sym}")
        return "\n".join(lines)