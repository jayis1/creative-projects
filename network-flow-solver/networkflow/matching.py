"""
Bipartite matching and assignment problem solvers.

  - BipartiteMatcher: maximum cardinality matching via Hopcroft-Karp (O(E√V))
  - AssignmentSolver: minimum-cost assignment via the Hungarian algorithm (O(n³))

Both operate on bipartite graphs.  The matching problem is also expressible as
a max-flow problem; the assignment problem as a min-cost flow problem.
"""

from __future__ import annotations

from collections import deque
from typing import Sequence


class BipartiteMatcher:
    """Maximum cardinality bipartite matching using Hopcroft-Karp.

    Left set: 0..L-1, Right set: 0..R-1.
    Edges are given as (left, right) pairs.

    Time complexity: O(E * sqrt(V))

    Example
    -------
    >>> m = BipartiteMatcher(3, 3)
    >>> m.add_edge(0, 0)
    >>> m.add_edge(0, 1)
    >>> m.add_edge(1, 1)
    >>> m.add_edge(2, 2)
    >>> m.match()  # max matching size
    3
    >>> m.get_matching()
    [(0, 0), (1, 1), (2, 2)]
    """

    def __init__(self, left_size: int, right_size: int):
        if left_size < 0 or right_size < 0:
            raise ValueError("Sizes must be non-negative")
        self.L: int = left_size
        self.R: int = right_size
        self.adj: list[list[int]] = [[] for _ in range(left_size)]
        self.pair_u: list[int] = [-1] * left_size   # left -> right match
        self.pair_v: list[int] = [-1] * right_size  # right -> left match
        self.dist: list[int] = [0] * left_size

    def add_edge(self, u: int, v: int) -> None:
        """Add edge between left vertex *u* and right vertex *v*."""
        if not (0 <= u < self.L):
            raise IndexError(f"Left vertex {u} out of range [0, {self.L})")
        if not (0 <= v < self.R):
            raise IndexError(f"Right vertex {v} out of range [0, {self.R})")
        self.adj[u].append(v)

    def _bfs(self) -> bool:
        """BFS to build layers of alternating paths from free left vertices."""
        q = deque()
        for u in range(self.L):
            if self.pair_u[u] == -1:
                self.dist[u] = 0
                q.append(u)
            else:
                self.dist[u] = -1
        found = False
        while q:
            u = q.popleft()
            for v in self.adj[u]:
                pu = self.pair_v[v]
                if pu != -1 and self.dist[pu] == -1:
                    self.dist[pu] = self.dist[u] + 1
                    q.append(pu)
                elif pu == -1:
                    found = True
        return found

    def _dfs(self, u: int) -> bool:
        """DFS to find augmenting path from vertex *u*."""
        for v in self.adj[u]:
            pu = self.pair_v[v]
            if pu == -1 or (self.dist[pu] == self.dist[u] + 1 and self._dfs(pu)):
                self.pair_u[u] = v
                self.pair_v[v] = u
                return True
        self.dist[u] = -1
        return False

    def match(self) -> int:
        """Compute maximum matching. Returns the cardinality."""
        self.pair_u = [-1] * self.L
        self.pair_v = [-1] * self.R
        result = 0
        while self._bfs():
            for u in range(self.L):
                if self.pair_u[u] == -1:
                    if self._dfs(u):
                        result += 1
        return result

    def get_matching(self) -> list[tuple[int, int]]:
        """Return list of (left, right) matched pairs. Call after match()."""
        return [(u, self.pair_u[u]) for u in range(self.L) if self.pair_u[u] != -1]

    def minimum_vertex_cover(self) -> tuple[list[int], list[int]]:
        """Kőnig's theorem: min vertex cover from max matching.

        Returns (left_vertices, right_vertices) forming a minimum vertex cover.
        Must be called after match().
        """
        # Find vertices reachable from free left vertices via alternating paths
        visited_u = [False] * self.L
        visited_v = [False] * self.R
        q = deque()
        for u in range(self.L):
            if self.pair_u[u] == -1:
                visited_u[u] = True
                q.append(u)
        while q:
            u = q.popleft()
            for v in self.adj[u]:
                if not visited_v[v] and self.pair_v[v] != u:
                    visited_v[v] = True
                    pu = self.pair_v[v]
                    if pu != -1 and not visited_u[pu]:
                        visited_u[pu] = True
                        q.append(pu)
        # Min vertex cover: (U \ Z) ∪ (V ∩ Z) where Z = reachable set
        left_cover = [u for u in range(self.L) if not visited_u[u]]
        right_cover = [v for v in range(self.R) if visited_v[v]]
        return left_cover, right_cover

    def maximum_independent_set(self) -> tuple[list[int], list[int]]:
        """Max independent set = complement of min vertex cover."""
        left_cover, right_cover = self.minimum_vertex_cover()
        cover_left = set(left_cover)
        cover_right = set(right_cover)
        left_is = [u for u in range(self.L) if u not in cover_left]
        right_is = [v for v in range(self.R) if v not in cover_right]
        return left_is, right_is


class AssignmentSolver:
    """Minimum-cost assignment via the Hungarian algorithm — O(n³).

    Given an n×n cost matrix, finds the assignment of rows to columns
    that minimizes total cost.  Handles rectangular cost matrices by
    padding with a large constant.

    Example
    -------
    >>> s = AssignmentSolver()
    >>> cost = [[4, 1, 3], [2, 0, 5], [3, 2, 2]]
    >>> s.solve(cost)
    5
    >>> s.get_assignment()
    [(0, 1), (1, 2), (2, 0)]
    """

    LARGE = 10 ** 18

    def __init__(self):
        self.assignment: list[int] = []  # row -> col
        self.total_cost: float = 0.0

    def solve(self, cost_matrix: Sequence[Sequence[float]]) -> float:
        """Solve the assignment problem. Returns minimum total cost.

        Also sets ``self.assignment`` (row→col) and ``self.total_cost``.
        """
        if not cost_matrix:
            self.assignment = []
            self.total_cost = 0
            return 0
        n = len(cost_matrix)
        m = len(cost_matrix[0])
        # Pad to square if needed
        size = max(n, m)
        # Use a large value for dummy entries
        INF = self.LARGE
        cost = [[INF] * size for _ in range(size)]
        for i in range(n):
            for j in range(m):
                cost[i][j] = cost_matrix[i][j]

        # Hungarian algorithm (Kuhn-Munkres) with potentials
        u = [0.0] * (size + 1)   # row potentials
        v = [0.0] * (size + 1)   # col potentials
        p = [0] * (size + 1)     # which row is matched to column j
        way = [0] * (size + 1)   # path array

        for i in range(1, size + 1):
            p[0] = i
            j0 = 0
            minv: list[float] = [float(INF)] * (size + 1)
            used = [False] * (size + 1)
            while True:
                used[j0] = True
                i0 = p[j0]
                delta = INF
                j1 = -1
                for j in range(1, size + 1):
                    if not used[j]:
                        cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                        if cur < minv[j]:
                            minv[j] = cur
                            way[j] = j0
                        if minv[j] < delta:
                            delta = minv[j]
                            j1 = j
                for j in range(size + 1):
                    if used[j]:
                        u[p[j]] += delta
                        v[j] -= delta
                    else:
                        minv[j] -= delta
                j0 = j1
                if p[j0] == 0:
                    break
            while j0:
                j1 = way[j0]
                p[j0] = p[j1]
                j0 = j1

        # Extract assignment and cost
        self.assignment = [0] * n
        self.total_cost = 0.0
        for j in range(1, size + 1):
            if p[j] != 0 and p[j] - 1 < n and j - 1 < m:
                self.assignment[p[j] - 1] = j - 1
                self.total_cost += cost_matrix[p[j] - 1][j - 1]
        return self.total_cost

    def get_assignment(self) -> list[tuple[int, int]]:
        """Return list of (row, col) pairs."""
        return [(i, self.assignment[i]) for i in range(len(self.assignment))]

    @staticmethod
    def max_assignment(cost_matrix: Sequence[Sequence[float]]) -> float:
        """Solve the *maximum* weight assignment (negate costs)."""
        if not cost_matrix:
            return 0
        max_val = max(max(row) for row in cost_matrix)
        neg = [[max_val - val for val in row] for row in cost_matrix]
        solver = AssignmentSolver()
        total = solver.solve(neg)
        return max_val * len(cost_matrix) - total