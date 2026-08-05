"""
Persistence diagrams and barcodes.
"""

from __future__ import annotations

from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

Infinity = float("inf")
Point = Tuple[float, float]


class PersistencePair:
    """A single persistence pair (birth, death) in a given dimension.

    Attributes
    ----------
    birth : float
    death : float
    dimension : int
    persistence : float
        death - birth (inf if death is infinite).
    """

    __slots__ = ("birth", "death", "dimension")

    def __init__(self, birth: float, death: float, dimension: int) -> None:
        if death != Infinity and death < birth:
            raise ValueError(
                f"Death ({death}) must be >= birth ({birth}) for a valid pair"
            )
        self.birth = float(birth)
        self.death = float(death)
        self.dimension = int(dimension)

    @property
    def persistence(self) -> float:
        return self.death - self.birth

    @property
    def is_essential(self) -> bool:
        return self.death == Infinity

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PersistencePair):
            return NotImplemented
        return (
            self.birth == other.birth
            and self.death == other.death
            and self.dimension == other.dimension
        )

    def __hash__(self) -> int:
        return hash((self.birth, self.death, self.dimension))

    def __repr__(self) -> str:
        return (
            f"PersistencePair(birth={self.birth}, death={self.death}, "
            f"dim={self.dimension})"
        )

    def __str__(self) -> str:
        d = "∞" if self.death == Infinity else f"{self.death:.4f}"
        return f"[H{self.dimension}] ({self.birth:.4f} → {d})"


class PersistenceDiagram:
    """A persistence diagram: collection of (birth, death) points by dimension.

    Attributes
    ----------
    dimension : int
        The homology dimension this diagram corresponds to.
    pairs : list of PersistencePair
    """

    def __init__(self, dimension: int,
                 pairs: Optional[Iterable[PersistencePair]] = None) -> None:
        self.dimension = int(dimension)
        self.pairs: List[PersistencePair] = list(pairs) if pairs else []

    def add(self, birth: float, death: float) -> None:
        """Add a persistence pair to this diagram."""
        self.pairs.append(PersistencePair(birth, death, self.dimension))

    @property
    def num_features(self) -> int:
        return len(self.pairs)

    @property
    def num_essential(self) -> int:
        return sum(1 for p in self.pairs if p.is_essential)

    @property
    def max_persistence(self) -> float:
        """Largest persistence value among all pairs."""
        if not self.pairs:
            return 0.0
        return max(p.persistence for p in self.pairs)

    def points(self, include_diagonal: bool = False,
               diagonal_value: Optional[float] = None) -> List[Point]:
        """Return diagram points as (birth, death) tuples.

        If ``include_diagonal`` is True, a single diagonal point at
        ``diagonal_value`` (or the midpoint of the diagram range) is added.
        This is required for bottleneck distance computation.
        """
        pts = [(p.birth, p.death) for p in self.pairs]
        if include_diagonal:
            if diagonal_value is None:
                if pts:
                    finite = [d for _, d in pts if d != Infinity]
                    if finite:
                        diagonal_value = (min(b for b, _ in pts) +
                                          max(finite)) / 2
                    else:
                        diagonal_value = min(b for b, _ in pts)
                else:
                    diagonal_value = 0.0
            pts.append((diagonal_value, diagonal_value))
        return pts

    def betti_number(self, epsilon: float) -> int:
        """The Betti number at scale epsilon: number of features alive.

        A feature is alive at epsilon if birth <= epsilon < death.
        """
        return sum(
            1 for p in self.pairs
            if p.birth <= epsilon and (p.death == Infinity or epsilon < p.death)
        )

    def __iter__(self) -> Iterator[PersistencePair]:
        return iter(self.pairs)

    def __len__(self) -> int:
        return len(self.pairs)

    def __repr__(self) -> str:
        return (f"PersistenceDiagram(dim={self.dimension}, "
                f"features={self.num_features})")

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "dimension": self.dimension,
            "pairs": [
                {
                    "birth": p.birth,
                    "death": p.death if p.death != Infinity else None,
                    "persistence": (p.persistence
                                    if p.death != Infinity else None),
                }
                for p in self.pairs
            ],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PersistenceDiagram":
        """Deserialize from a dictionary."""
        diag = cls(d["dimension"])
        for p in d["pairs"]:
            death = p["death"]
            if death is None:
                death = Infinity
            diag.add(p["birth"], death)
        return diag


def diagrams_from_persistence(
    persistence: Dict[int, List[Tuple[float, float]]],
) -> Dict[int, PersistenceDiagram]:
    """Convert raw persistence dict into PersistenceDiagram objects."""
    result: Dict[int, PersistenceDiagram] = {}
    for dim, pairs in persistence.items():
        diag = PersistenceDiagram(dim)
        for birth, death in pairs:
            diag.add(birth, death)
        result[dim] = diag
    return result


def barcode_string(diagrams: Dict[int, PersistenceDiagram],
                   max_width: int = 60) -> str:
    """Render an ASCII barcode representation of persistence diagrams.

    Each feature is shown as a horizontal bar from birth to death.
    """
    lines: List[str] = []
    for dim in sorted(diagrams):
        diag = diagrams[dim]
        if diag.num_features == 0:
            lines.append(f"H{dim}: (no features)")
            continue
        # Determine scale.
        all_births = [p.birth for p in diag]
        all_deaths = [p.death for p in diag if p.death != Infinity]
        if all_deaths:
            max_val = max(max(all_deaths), max(all_births))
        else:
            max_val = max(all_births) if all_births else 1.0
        if max_val == 0:
            max_val = 1.0

        lines.append(f"H{dim} ({diag.num_features} features):")
        for p in diag:
            start_col = int(p.birth / max_val * max_width)
            if p.death == Infinity:
                bar = "█" * (max_width - start_col) + "→∞"
            else:
                end_col = int(p.death / max_val * max_width)
                bar = "█" * max(1, end_col - start_col)
            pad = " " * start_col
            lines.append(f"  {pad}{bar}  ({p.birth:.3f} → "
                         f"{'∞' if p.death == Infinity else f'{p.death:.3f}'})")
    return "\n".join(lines)