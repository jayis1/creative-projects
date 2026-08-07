"""
PLA (Berkeley Espresso PLA) format reader and writer.

This module provides a more complete PLA parser/writer than the basic one
in :mod:`logicmin.parser`, supporting:

* Full directive set (.i, .o, .ilb, .ob, .p, .e, .type, .phase, .start-kiss,
  .end-kiss, .default)
* PLA export (write a list of :class:`~logicmin.boolean.BooleanFunction`
  objects to a PLA file)
* Validation (check consistency of dimensions, names, and patterns)
* PLA statistics (input/output counts, product count, minterm counts)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .boolean import BooleanFunction, var_names, cube_to_minterms


# ---------------------------------------------------------------------------
# PLA data structure
# ---------------------------------------------------------------------------

@dataclass
class PLAData:
    """Structured representation of a PLA file."""

    n_in: int = 0
    n_out: int = 0
    input_names: List[str] = field(default_factory=list)
    output_names: List[str] = field(default_factory=list)
    entries: List[Tuple[str, str]] = field(default_factory=list)
    pla_type: str = "fr"  # fr = fully specified, f = on-set only
    phase: Optional[str] = None
    comments: List[str] = field(default_factory=list)

    @property
    def n_products(self) -> int:
        return len(self.entries)

    def to_functions(self) -> List[BooleanFunction]:
        """Convert the PLA to a list of :class:`BooleanFunction` objects."""
        if self.n_in == 0:
            raise ValueError("PLA has no .i directive")
        if self.n_out == 0:
            self.n_out = 1
        if not self.input_names:
            self.input_names = var_names(self.n_in)
        if not self.output_names:
            self.output_names = [f"f{i}" for i in range(self.n_out)]
        per_output_mt: List[List[int]] = [[] for _ in range(self.n_out)]
        per_output_dc: List[List[int]] = [[] for _ in range(self.n_out)]
        for in_pat, out_pat in self.entries:
            if len(in_pat) != self.n_in:
                raise ValueError(
                    f"input pattern {in_pat!r} length {len(in_pat)} != .i ({self.n_in})"
                )
            if len(out_pat) != self.n_out:
                raise ValueError(
                    f"output pattern {out_pat!r} length {len(out_pat)} != .o ({self.n_out})"
                )
            minterms = _expand_pat(in_pat)
            for oi, sym in enumerate(out_pat):
                if sym == "1":
                    per_output_mt[oi].extend(minterms)
                elif sym in ("-", "2", "x", "X"):
                    per_output_dc[oi].extend(minterms)
                # 0 → nothing
        functions: List[BooleanFunction] = []
        for oi in range(self.n_out):
            functions.append(
                BooleanFunction(
                    n_vars=self.n_in,
                    minterms=per_output_mt[oi],
                    dontcare=per_output_dc[oi],
                    name=self.output_names[oi] if oi < len(self.output_names) else f"f{oi}",
                )
            )
        return functions

    @classmethod
    def from_functions(
        cls,
        functions: Sequence[BooleanFunction],
        input_names: Optional[List[str]] = None,
        output_names: Optional[List[str]] = None,
    ) -> "PLAData":
        """Create a PLA from a list of single-output functions sharing the same
        inputs.
        """
        if not functions:
            raise ValueError("need at least one function")
        n_in = functions[0].n_vars
        for f in functions:
            if f.n_vars != n_in:
                raise ValueError("all functions must have the same n_vars")
        if input_names is None:
            input_names = var_names(n_in)
        if output_names is None:
            output_names = [f.name for f in functions]
        # Build entries: for each minterm, determine the output pattern
        universe = range(1 << n_in)
        entries: List[Tuple[str, str]] = []
        # Build a map: minterm → output pattern
        for m in universe:
            in_pat = format(m, f"0{n_in}b")
            out_chars: List[str] = []
            for f in functions:
                if m in f.minterms:
                    out_chars.append("1")
                elif m in f.dontcare:
                    out_chars.append("-")
                else:
                    out_chars.append("0")
            # Only add entries that are not all-zero (optional, but common in PLA)
            if any(c != "0" for c in out_chars):
                entries.append((in_pat, "".join(out_chars)))
        return cls(
            n_in=n_in,
            n_out=len(functions),
            input_names=list(input_names),
            output_names=list(output_names),
            entries=entries,
        )

    def to_pla_text(self) -> str:
        """Serialize the PLA to text format."""
        lines: List[str] = []
        for c in self.comments:
            lines.append(f"# {c}")
        lines.append(f".i {self.n_in}")
        lines.append(f".o {self.n_out}")
        if self.input_names:
            lines.append(".ilb " + " ".join(self.input_names))
        if self.output_names:
            lines.append(".ob " + " ".join(self.output_names))
        if self.pla_type != "fr":
            lines.append(f".type {self.pla_type}")
        lines.append(f".p {len(self.entries)}")
        for in_pat, out_pat in self.entries:
            lines.append(f"{in_pat} {out_pat}")
        lines.append(".e")
        return "\n".join(lines) + "\n"

    def validate(self) -> List[str]:
        """Validate the PLA and return a list of error messages (empty if OK)."""
        errors: List[str] = []
        if self.n_in <= 0:
            errors.append("missing or invalid .i directive")
        if self.n_out <= 0:
            errors.append("missing or invalid .o directive")
        if self.input_names and len(self.input_names) != self.n_in:
            errors.append(
                f".ilb has {len(self.input_names)} names but .i={self.n_in}"
            )
        if self.output_names and len(self.output_names) != self.n_out:
            errors.append(
                f".ob has {len(self.output_names)} names but .o={self.n_out}"
            )
        for idx, (in_pat, out_pat) in enumerate(self.entries):
            if len(in_pat) != self.n_in:
                errors.append(
                    f"entry {idx}: input pattern length {len(in_pat)} != {self.n_in}"
                )
            if len(out_pat) != self.n_out:
                errors.append(
                    f"entry {idx}: output pattern length {len(out_pat)} != {self.n_out}"
                )
            for ch in in_pat:
                if ch not in "01-":
                    errors.append(f"entry {idx}: invalid input char {ch!r}")
            for ch in out_pat:
                if ch not in "01-xX2":
                    errors.append(f"entry {idx}: invalid output char {ch!r}")
        return errors

    def stats(self) -> Dict[str, int]:
        """Return PLA statistics."""
        functions = self.to_functions()
        stats: Dict[str, int] = {
            "n_in": self.n_in,
            "n_out": self.n_out,
            "n_products": self.n_products,
        }
        for i, f in enumerate(functions):
            stats[f"output_{i}_minterms"] = len(f.minterms)
            stats[f"output_{i}_dontcare"] = len(f.dontcare)
        return stats


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_pla_full(text: str) -> PLAData:
    """Parse a PLA text block into a structured :class:`PLAData`."""
    lines = text.strip().splitlines()
    pla = PLAData()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line:
            continue
        if line.startswith("#"):
            pla.comments.append(line[1:].strip())
            continue
        parts = line.split()
        directive = parts[0].lower()
        if directive == ".i":
            pla.n_in = int(parts[1])
        elif directive == ".o":
            pla.n_out = int(parts[1])
        elif directive == ".ilb":
            pla.input_names = parts[1:]
        elif directive in (".ob", ".obf"):
            pla.output_names = parts[1:]
        elif directive == ".p":
            pass  # number of product lines
        elif directive == ".type":
            if len(parts) > 1:
                pla.pla_type = parts[1]
        elif directive == ".phase":
            if len(parts) > 1:
                pla.phase = parts[1]
        elif directive in (".start-kiss", ".end-kiss"):
            pass  # KISS section markers (ignored)
        elif directive == ".default":
            pass  # default output values
        elif directive == ".e":
            break
        elif directive.startswith("."):
            continue  # skip unknown directives
        else:
            # product line
            if len(parts) >= 2:
                pla.entries.append((parts[0], parts[1]))
    return pla


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


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

def write_pla(functions: Sequence[BooleanFunction], path: Optional[str] = None) -> str:
    """Write a list of functions as a PLA file.

    If ``path`` is given, writes to file and returns the text.  Otherwise
    just returns the PLA text.
    """
    pla = PLAData.from_functions(functions)
    text = pla.to_pla_text()
    if path:
        with open(path, "w") as fh:
            fh.write(text)
    return text