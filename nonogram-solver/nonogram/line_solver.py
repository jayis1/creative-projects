"""
Efficient per-line solver for nonogram clues.

Given a line (row or column) of cells and its clue, ``LineSolver`` computes the
cells that are definitely filled or definitely empty across **all** valid
arrangements.  It uses two techniques:

1. **Overlap method** — for a single clue block, the leftmost and rightmost
   placements may overlap; the overlap region is guaranteed filled.
2. **Constraint propagation** — iterate left-to-right and right-to-left
   combining existing knowledge, marking cells that must be empty.

The result is a new line with as many cells decided as can be proven.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from nonogram.board import Cell, Board


class LineSolver:
    """Solve a single line (row or column) as far as logic allows."""

    def __init__(self) -> None:
        self._cache: dict = {}

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def solve(self, line: List[Cell], clue: List[int]) -> List[Cell]:
        """Return a new line with all provable cells decided.

        If the line is already contradictory (no valid arrangement exists),
        raises ``ValueError``.
        """
        result = self._propagate(list(line), clue)
        if result is None:
            raise ValueError(f"No valid arrangement for clue {clue}")
        return result

    def is_feasible(self, line: List[Cell], clue: List[int]) -> bool:
        """True if at least one valid arrangement of *clue* fits *line*."""
        return self._propagate(list(line), clue) is not None

    # ------------------------------------------------------------------ #
    # Core algorithm
    # ------------------------------------------------------------------ #
    def _propagate(self, line: List[Cell], clue: List[int]) -> Optional[List[Cell]]:
        """Iteratively apply overlap + left/right propagation until fixpoint."""
        n = len(line)
        key = (tuple(c.value for c in line), tuple(clue), n)
        if key in self._cache:
            return self._cache[key]

        # Fast contradiction check: too many filled cells or clue too long.
        if sum(clue) > n:
            self._cache[key] = None
            return None
        if Board.clue_sum(clue) > n:
            self._cache[key] = None
            return None

        # Iterate to fixpoint: keep applying overlap until no change.
        current = list(line)
        for _ in range(n + 5):  # bounded iterations
            new = self._overlap_pass(current, clue)
            if new is None:
                self._cache[key] = None
                return None
            if new == current:
                break
            current = new

        # Verify feasibility: does at least one arrangement match?
        if not self._has_solution(current, clue):
            self._cache[key] = None
            return None

        self._cache[key] = current
        return current

    def _overlap_pass(self, line: List[Cell], clue: List[int]) -> Optional[List[Cell]]:
        """One pass of the overlap method + gap enforcement."""
        n = len(line)
        result = list(line)

        # Special case: empty clue → all cells must be EMPTY.
        if not clue:
            for pos in range(n):
                if result[pos] is Cell.FILLED:
                    return None  # contradiction: filled cell but clue is empty
                result[pos] = Cell.EMPTY
            return result

        # Compute leftmost and rightmost placement positions.
        left = self._leftmost_positions(line, clue)
        if left is None:
            return None
        right = self._rightmost_positions(line, clue)
        if right is None:
            return None

        # For each block, cells in [left[i], right[i]] overlap → filled.
        num_blocks = len(clue)
        for i in range(num_blocks):
            lo = left[i]
            hi = right[i]
            block_len = clue[i]
            # overlap region is [hi, lo + block_len - 1] when hi <= lo+block-1
            overlap_start = hi
            overlap_end = lo + block_len - 1
            if overlap_start <= overlap_end:
                for pos in range(overlap_start, overlap_end + 1):
                    if result[pos] is Cell.EMPTY:
                        return None  # contradiction
                    result[pos] = Cell.FILLED

        # Cells before the first block's leftmost start must be empty.
        if num_blocks > 0:
            for pos in range(0, left[0]):
                if result[pos] is Cell.FILLED:
                    return None
                result[pos] = Cell.EMPTY
            # Cells after the last block's rightmost end must be empty.
            last_end = right[-1] + clue[-1] - 1
            for pos in range(last_end + 1, n):
                if result[pos] is Cell.FILLED:
                    return None
                result[pos] = Cell.EMPTY

        # Enforce gaps between blocks: cells between block i end and block i+1
        # start (in the tightest packing) must be empty if both blocks are
        # constrained enough.  We use the gap between left[i]+clue[i] and
        # left[i+1].
        for i in range(num_blocks - 1):
            gap_start = left[i] + clue[i]
            gap_end = right[i + 1] - 1
            if gap_start <= gap_end:
                for pos in range(gap_start, gap_end + 1):
                    # Only mark empty if it's in the mandatory gap region.
                    # A cell is mandatory-gap if it is outside every possible
                    # block placement for *all* blocks.
                    if self._is_definitely_gap(pos, left, right, clue, i):
                        if result[pos] is Cell.FILLED:
                            return None
                        result[pos] = Cell.EMPTY

        return result

    def _is_definitely_gap(
        self,
        pos: int,
        left: List[int],
        right: List[int],
        clue: List[int],
        before_block: int,
    ) -> bool:
        """Check if *pos* cannot belong to any block → definitely a gap."""
        for i in range(len(clue)):
            lo = left[i]
            hi = right[i]
            if lo <= pos <= hi + clue[i] - 1:
                return False
        return True

    # ------------------------------------------------------------------ #
    # Leftmost / rightmost placements
    # ------------------------------------------------------------------ #
    def _leftmost_positions(
        self, line: List[Cell], clue: List[int]
    ) -> Optional[List[int]]:
        """Compute the leftmost valid start position for each block.

        Uses a greedy approach that respects both EMPTY cells (blocks can't
        overlap them) and FILLED cells (every FILLED cell must be covered by
        some block).  The algorithm packs blocks left-to-right, but when a
        FILLED cell is encountered before the next block's position, the
        block is shifted right to cover it.

        Returns the start index of each block, or ``None`` if impossible.
        """
        n = len(line)
        if not clue:
            # No blocks — all cells must be EMPTY (no FILLED allowed).
            for j in range(n):
                if line[j] is Cell.FILLED:
                    return None
            return []

        positions: List[int] = []
        pos = 0  # current scan position
        for i, block in enumerate(clue):
            remaining = clue[i:]
            min_space = Board.clue_sum(remaining)
            placed = False
            # Try each start position from pos up to the rightmost valid.
            while pos <= n - min_space:
                if not self._can_place(line, pos, block):
                    pos += 1
                    continue
                # Cell after block must not be forced FILLED (would merge blocks).
                after = pos + block
                if after < n and line[after] is Cell.FILLED:
                    pos += 1
                    continue
                # Check: are there any FILLED cells between pos and the end
                # of this block that would be left uncovered if we place
                # the block here?  Actually we need to check that there are
                # no FILLED cells *before* pos that aren't covered by a
                # previous block.
                # The critical check: if there's a FILLED cell at some position
                # j < pos, it must have been covered by a previous block.
                # Since we pack left-to-right and advance pos past each block,
                # any FILLED cell before pos that wasn't covered is a problem.
                # We check this after all blocks are placed (below).
                positions.append(pos)
                pos = pos + block + 1  # +1 for mandatory gap
                placed = True
                break
            if not placed:
                return None

        # Post-verification: check that every FILLED cell is covered by some
        # block in the leftmost arrangement.  If any FILLED cell is not
        # covered (it falls in a gap or before/after all blocks), we need to
        # reposition blocks to cover it.  We find the first uncovered FILLED
        # cell and retry with that constraint.
        if positions:
            # Build a set of covered positions.
            covered = set()
            for i, start in enumerate(positions):
                for j in range(start, start + clue[i]):
                    covered.add(j)
            # Find first uncovered FILLED cell.
            for j in range(n):
                if line[j] is Cell.FILLED and j not in covered:
                    # Find which block should cover this cell.
                    # It's the first block whose range can include j.
                    for i in range(len(clue)):
                        # Check if block i can cover position j
                        if positions[i] <= j < positions[i] + clue[i]:
                            break  # already covered (shouldn't happen)
                        # Can block i be repositioned to cover j?
                        # Block i starts at positions[i], covers [positions[i], positions[i]+clue[i]-1]
                        # To cover j, start in [j-clue[i]+1, j]
                        # Check if this is feasible (start >= end of previous block + gap)
                        prev_end = positions[i-1] + clue[i-1] if i > 0 else -1
                        next_start = positions[i+1] if i+1 < len(clue) else n
                        lo = max(prev_end + 1, j - clue[i] + 1)
                        hi = min(j, next_start - 1 - clue[i] + 1)
                        if lo <= hi:
                            return self._leftmost_positions_covering(
                                line, clue, j, i
                            )
                    # No block can cover this FILLED cell — infeasible.
                    return None
        return positions

    def _leftmost_positions_covering(
        self, line: List[Cell], clue: List[int], filled_pos: int,
        block_idx: int
    ) -> Optional[List[int]]:
        """Compute leftmost positions where block *block_idx* covers
        *filled_pos*. Used as a fallback when the greedy leftmost packing
        leaves a FILLED cell uncovered."""
        n = len(line)
        block = clue[block_idx]
        # The block must cover filled_pos, so its start is in
        # [filled_pos - block + 1, filled_pos], clamped to valid range.
        start_min = max(0, filled_pos - block + 1)
        # Recompute all positions with this constraint.
        # We rebuild from scratch: pack blocks 0..block_idx-1 as left as
        # possible, then place block_idx to cover filled_pos, then pack
        # the rest as left as possible.
        positions: List[int] = []
        pos = 0
        for i in range(len(clue)):
            blk = clue[i]
            remaining = clue[i:]
            min_space = Board.clue_sum(remaining)
            if i == block_idx:
                # Place this block to cover filled_pos.
                # Start must be >= pos, <= filled_pos, and >= filled_pos - blk + 1.
                lo = max(pos, filled_pos - blk + 1)
                placed = False
                for start in range(lo, filled_pos + 1):
                    if start + blk > n:
                        break
                    if not self._can_place(line, start, blk):
                        continue
                    after = start + blk
                    if after < n and line[after] is Cell.FILLED:
                        continue
                    positions.append(start)
                    pos = start + blk + 1
                    placed = True
                    break
                if not placed:
                    return None
            else:
                placed = False
                while pos <= n - min_space:
                    if not self._can_place(line, pos, blk):
                        pos += 1
                        continue
                    after = pos + blk
                    if after < n and line[after] is Cell.FILLED:
                        pos += 1
                        continue
                    positions.append(pos)
                    pos = pos + blk + 1
                    placed = True
                    break
                if not placed:
                    return None
        return positions

    def _rightmost_positions(
        self, line: List[Cell], clue: List[int]
    ) -> Optional[List[int]]:
        """Pack blocks as far right as possible (mirror of leftmost)."""
        n = len(line)
        rev_clue = list(reversed(clue))
        rev_line = list(reversed(line))
        rev_left = self._leftmost_positions(rev_line, rev_clue)
        if rev_left is None:
            return None
        # Convert reversed positions back to original indices.
        # rev_clue[j] == clue[len-1-j], so rev block j maps to original block
        # (len-1-j).  When we enumerate reversed(rev_left) with index i, we
        # get rev_left[len-1-i] = rev block (len-1-i) = original block i.
        # So the original block length for enumeration index i is clue[i],
        # and its start is (n - rev_left[len-1-i] - clue[i]).
        # reversed(rev_left) yields rev_left[len-1], rev_left[len-2], ...
        # i.e. enumeration index i gets rev_left[len-1-i], which is exactly
        # what we need.  The resulting list is already in original block
        # order (block 0, block 1, ...), so NO final reverse is needed.
        positions = []
        for i, start in enumerate(reversed(rev_left)):
            positions.append(n - start - clue[i])
        return positions

    @staticmethod
    def _can_place(line: List[Cell], pos: int, block: int) -> bool:
        """Can a block of *block* filled cells start at *pos* without
        contradicting existing EMPTY cells?"""
        n = len(line)
        if pos + block > n:
            return False
        for i in range(pos, pos + block):
            if line[i] is Cell.EMPTY:
                return False
        return True

    # ------------------------------------------------------------------ #
    # Full feasibility check (enumeration with pruning)
    # ------------------------------------------------------------------ #
    def _has_solution(self, line: List[Cell], clue: List[int]) -> bool:
        """Check whether at least one arrangement satisfies both *clue* and
        the existing known cells in *line*.

        Uses recursive backtracking with pruning — efficient for the line
        sizes typical in nonograms (≤ 50).
        """
        n = len(line)

        def backtrack(idx: int, block_idx: int, current: List[Cell]) -> bool:
            if block_idx == len(clue):
                # Remaining cells must not be FILLED.
                for j in range(idx, n):
                    if current[j] is Cell.FILLED:
                        return False
                    current[j] = Cell.EMPTY
                return True
            block = clue[block_idx]
            remaining_blocks = clue[block_idx + 1:]
            min_space_after = Board.clue_sum(remaining_blocks)
            # Try placing this block at each valid start position.
            last_start = n - block - min_space_after
            start = idx
            while start <= last_start:
                # Cells from idx to start-1 must be EMPTY.
                ok = True
                for j in range(idx, start):
                    if line[j] is Cell.FILLED:
                        ok = False
                        break
                    current[j] = Cell.EMPTY
                if not ok:
                    start += 1
                    continue
                # Place the block.
                can = True
                for j in range(start, start + block):
                    if line[j] is Cell.EMPTY:
                        can = False
                        break
                    current[j] = Cell.FILLED
                if not can:
                    start += 1
                    continue
                # Gap after block (unless last block).
                gap_pos = start + block
                if gap_pos < n:
                    if line[gap_pos] is Cell.FILLED:
                        start += 1
                        continue
                    current[gap_pos] = Cell.EMPTY
                    next_idx = gap_pos + 1
                else:
                    next_idx = gap_pos
                if backtrack(next_idx, block_idx + 1, current):
                    return True
                start += 1
            return False

        return backtrack(0, 0, list(line))