"""
Simplex and SimplexTree data structures for simplicial complexes.
"""

from __future__ import annotations

from itertools import combinations
from typing import Iterable, Iterator, Optional, Set, Tuple


class Simplex:
    """An immutable simplex represented as a sorted tuple of vertices.

    Examples
    --------
    >>> s = Simplex((0, 1, 2))
    >>> s.dimension
    2
    >>> sorted(s.faces())
    [Simplex((0, 1)), Simplex((0, 2)), Simplex((1, 2))]
    """

    __slots__ = ("_vertices", "_hash")

    def __init__(self, vertices: Iterable[int]) -> None:
        # set() removes duplicates; sorted() ensures canonical ordering.
        self._vertices: Tuple[int, ...] = tuple(sorted(set(vertices)))
        # Validate non-negative vertices.
        for v in self._vertices:
            if v < 0:
                raise ValueError(f"Vertex labels must be non-negative, got {v}")
        self._hash = hash(self._vertices)

    # ---- core properties -------------------------------------------------

    @property
    def vertices(self) -> Tuple[int, ...]:
        return self._vertices

    @property
    def dimension(self) -> int:
        """Dimension of the simplex (0 = point, 1 = edge, 2 = triangle, ...)."""
        return len(self._vertices) - 1

    def __len__(self) -> int:
        return len(self._vertices)

    def __iter__(self) -> Iterator[int]:
        return iter(self._vertices)

    def __contains__(self, vertex: int) -> bool:
        return vertex in self._vertices

    # ---- boundary / faces ------------------------------------------------

    def faces(self) -> Iterator["Simplex"]:
        """Yield all (dim-1)-faces (codimension-1 boundary faces).

        A k-simplex has k+1 faces, each obtained by removing one vertex.
        """
        if self.dimension == 0:
            return  # 0-simplices have no faces
        for i in range(len(self._vertices)):
            yield Simplex(self._vertices[:i] + self._vertices[i + 1:])

    def boundary(self) -> Iterator[Tuple[int, "Simplex"]]:
        """Yield (sign, face) pairs for the oriented boundary.

        Sign alternates by position: (-1)^i.

        For a 0-simplex (vertex), yields nothing — a vertex has no boundary.
        """
        if self.dimension == 0:
            return  # 0-simplices have no boundary
        for i in range(len(self._vertices)):
            face = Simplex(self._vertices[:i] + self._vertices[i + 1:])
            yield (1 if i % 2 == 0 else -1, face)

    def cofaces(self) -> Iterator["Simplex"]:
        """Yield all codimension-1 cofaces — not generically available without
        context; this helper yields the simplex itself for convenience."""
        yield self

    def subsimplices(self, dim: int) -> Iterator["Simplex"]:
        """Yield all subsimplices of a given dimension (0 <= dim <= self.dim)."""
        if dim < 0 or dim > self.dimension:
            return
        for combo in combinations(self._vertices, dim + 1):
            yield Simplex(combo)

    def all_subsimplices(self) -> Iterator["Simplex"]:
        """Yield every proper subsimplex (including vertices, excluding self
        and the empty simplex)."""
        for k in range(1, len(self._vertices)):
            for combo in combinations(self._vertices, k):
                yield Simplex(combo)

    # ---- dunder ----------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Simplex):
            return NotImplemented
        return self._vertices == other._vertices

    def __hash__(self) -> int:
        return self._hash

    def __lt__(self, other: "Simplex") -> bool:
        if not isinstance(other, Simplex):
            return NotImplemented
        # Lexicographic order on sorted vertex tuples.
        return self._vertices < other._vertices

    def __repr__(self) -> str:
        return f"Simplex({self._vertices})"

    def __str__(self) -> str:
        return "{" + ", ".join(str(v) for v in self._vertices) + "}"


class SimplexTree:
    """A sparse simplex tree (a.k.a. compressed trie) for a filtered simplicial
    complex.

    Each node stores a vertex, a filtration value, and children (vertex → node).
    Traversal from root to a node gives the vertices of that simplex in sorted
    order.

    Parameters
    ----------
    max_dimension : int, optional
        Maximum dimension of simplices to retain. Default: no limit.

    Examples
    --------
    >>> st = SimplexTree()
    >>> st.insert(Simplex((0, 1)), filtration=0.5)
    >>> st.insert(Simplex((1, 2)), filtration=0.8)
    >>> (Simplex((0, 1, 2)) in st)
    False
    >>> st.num_simplices()
    4
    """

    class _Node:
        __slots__ = ("vertex", "filtration", "children", "parent")

        def __init__(self, vertex: int, filtration: float,
                     parent: Optional["SimplexTree._Node"] = None) -> None:
            self.vertex = vertex
            self.filtration = filtration
            self.children: dict[int, "SimplexTree._Node"] = {}
            self.parent = parent

        def __repr__(self) -> str:
            return f"_Node(v={self.vertex}, f={self.filtration})"

    def __init__(self, max_dimension: Optional[int] = None) -> None:
        self._root = self._Node(-1, -float("inf"))
        self.max_dimension = max_dimension
        self._size = 0
        self._id_map: dict[Simplex, int] = {}
        self._next_id = 0

    # ---- insertion -------------------------------------------------------

    def insert(self, simplex: Simplex, filtration: float) -> bool:
        """Insert a simplex with its filtration value.

        If the simplex already exists, the filtration value is updated to the
        minimum of the old and new values (filtration must be non-decreasing
        along chains, so we also propagate to children if needed).

        Returns True if a new simplex was inserted, False if it already existed.
        """
        verts = simplex.vertices
        if self.max_dimension is not None and len(verts) - 1 > self.max_dimension:
            return False

        node = self._root
        is_new = False
        for i, v in enumerate(verts):
            if v not in node.children:
                child = self._Node(v, filtration, parent=node)
                node.children[v] = child
                node = child
                is_new = True
                self._size += 1
                # Assign an ID to every newly created node (including
                # intermediate simplices like vertices and edges when
                # inserting a higher-dimensional simplex).
                self._assign_id(Simplex(self._path_to(node)))
            else:
                node = node.children[v]
                # Filtration must be non-decreasing along a chain.
                if filtration < node.filtration:
                    node.filtration = filtration
        return is_new

    def _path_to(self, node: _Node) -> Tuple[int, ...]:
        path = []
        cur = node
        while cur is not self._root:
            path.append(cur.vertex)
            cur = cur.parent
        return tuple(reversed(path))

    def _assign_id(self, simplex: Simplex) -> None:
        """Assign a unique integer ID to a simplex if it doesn't have one."""
        if simplex not in self._id_map:
            self._id_map[simplex] = self._next_id
            self._next_id += 1

    def insert_simplex_and_faces(self, simplex: Simplex,
                                  filtration: float) -> None:
        """Insert a simplex and all of its subsimplices with non-decreasing
        filtration values (faces get min(filtration, existing))."""
        for sub in simplex.all_subsimplices():
            self.insert(sub, filtration)
        self.insert(simplex, filtration)

    # ---- lookup ----------------------------------------------------------

    def __contains__(self, simplex: Simplex) -> bool:
        node = self._root
        for v in simplex.vertices:
            if v not in node.children:
                return False
            node = node.children[v]
        return True

    def filtration_value(self, simplex: Simplex) -> Optional[float]:
        """Return the filtration value of a simplex, or None if absent."""
        node = self._root
        for v in simplex.vertices:
            if v not in node.children:
                return None
            node = node.children[v]
        return node.filtration

    def node_id(self, simplex: Simplex) -> Optional[int]:
        """Return the integer column id assigned to a simplex."""
        return self._id_map.get(simplex)

    # ---- iteration -------------------------------------------------------

    def __iter__(self) -> Iterator[Simplex]:
        """Iterate over all simplices in lexicographic order."""
        yield from self._iter_from(self._root)

    def _iter_from(self, node: _Node) -> Iterator[Simplex]:
        for v in sorted(node.children):
            child = node.children[v]
            yield Simplex(self._path_to(child))
            yield from self._iter_from(child)

    def iter_with_filtration(self) -> Iterator[Tuple[Simplex, float]]:
        """Yield (simplex, filtration) pairs in sorted vertex order."""
        yield from self._iter_filt_from(self._root)

    def _iter_filt_from(self, node: _Node) -> Iterator[Tuple[Simplex, float]]:
        for v in sorted(node.children):
            child = node.children[v]
            yield (Simplex(self._path_to(child)), child.filtration)
            yield from self._iter_filt_from(child)

    # ---- statistics ------------------------------------------------------

    def num_simplices(self) -> int:
        return self._size

    def dimension(self) -> int:
        """Maximum dimension of any simplex in the tree."""
        max_dim = -1
        for s in self:
            if s.dimension > max_dim:
                max_dim = s.dimension
        return max_dim

    def simplices_of_dimension(self, dim: int) -> Iterator[Tuple[Simplex, float]]:
        for s, f in self.iter_with_filtration():
            if s.dimension == dim:
                yield (s, f)

    def all_simplex_ids(self) -> dict[Simplex, int]:
        """Return (and lazily build) the simplex → column-id mapping."""
        # Ensure every simplex has an id.
        for s in self:
            self._assign_id(s)
        return dict(self._id_map)


def simplex_from_path(path: Tuple[int, ...]) -> Simplex:
    return Simplex(path)