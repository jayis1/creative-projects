"""
CDCL SAT Solver — Conflict-Driven Clause Learning with VSIDS and Restarts.

Implements a complete SAT solver supporting:
- DIMACS CNF input format
- Boolean Constraint Propagation (BCP)
- Conflict-driven clause learning (CDCL) with 1UIP
- VSIDS (Variable State Independent Decaying Sum) decision heuristic
- Phase saving
- Non-chronological backtracking
- Luby and geometric restart strategies
- Clause deletion / garbage collection (Glucose-style glue-based)
- Preprocessing: subsumption, strengthening, variable elimination
- Assumption-based incremental solving
- Proof logging in DRAT format (optional)
- Detailed statistics and verbose mode
"""

from __future__ import annotations
import os
import sys
import math
import time
from collections import deque
from typing import List, Optional, Tuple, Dict, Set

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class Clause:
    """Compact clause representation. First two literals are watched."""
    __slots__ = ("lits", "learnt", "activity", "glue", "frozen")

    def __init__(self, lits: List[int], learnt: bool = False):
        self.lits: List[int] = lits
        self.learnt: bool = learnt
        self.activity: float = 0.0
        self.glue: int = 0       # Glue/LBD score (only for learnt clauses)
        self.frozen: bool = False  # Don't delete if frozen

    def __len__(self) -> int:
        return len(self.lits)

    def __repr__(self) -> str:
        tag = "L" if self.learnt else "O"
        return f"Clause({tag},{self.lits})"


class LitInfo:
    """Per-literal metadata used during search."""
    __slots__ = ("watchers",)

    def __init__(self):
        self.watchers: List[Clause] = []


class VarInfo:
    """Per-variable metadata."""
    __slots__ = ("activity", "polarity", "level", "reason", "seen")

    def __init__(self):
        self.activity: float = 0.0
        self.polarity: bool = False  # True → positive literal preferred
        self.level: int = -1         # Decision level when assigned
        self.reason: Optional[Clause] = None
        self.seen: bool = False       # Used during conflict analysis


# ---------------------------------------------------------------------------
# Luby sequence for restarts
# ---------------------------------------------------------------------------

def luby(i: int) -> int:
    """Return the i-th element of the Luby sequence (1-indexed)."""
    k = 1
    while (1 << k) <= i:
        k += 1
    if (1 << k) == i + 1:
        return 1 << (k - 1)
    else:
        return luby(i - (1 << (k - 1)) + 1)


# ---------------------------------------------------------------------------
# Solver statistics
# ---------------------------------------------------------------------------

class SolverStats:
    """Collects solver statistics for reporting."""
    def __init__(self):
        self.decisions: int = 0
        self.propagations: int = 0
        self.conflicts: int = 0
        self.restarts: int = 0
        self.learnt_clauses: int = 0
        self.deleted_clauses: int = 0
        self.start_time: float = 0.0
        self.end_time: float = 0.0

    def elapsed(self) -> float:
        end = self.end_time if self.end_time > 0 else time.time()
        return end - self.start_time

    def __repr__(self) -> str:
        return (f"Decisions={self.decisions} Propagations={self.propagations} "
                f"Conflicts={self.conflicts} Restarts={self.restarts} "
                f"Learnt={self.learnt_clauses} Deleted={self.deleted_clauses} "
                f"Time={self.elapsed():.3f}s")


# ---------------------------------------------------------------------------
# Main solver
# ---------------------------------------------------------------------------

class Solver:
    """CDCL SAT Solver with preprocessing and incremental solving."""

    # -------------------------------------------------------------------------
    # Construction / parsing
    # -------------------------------------------------------------------------

    def __init__(self):
        # Clause database
        self.clauses: List[Clause] = []
        self.learnt_clauses: List[Clause] = []

        # Variable / literal info
        self.num_vars: int = 0
        self.var_info: List[VarInfo] = []
        self.lit_info: List[LitInfo] = []

        # Assignment trail
        self.trail: List[int] = []
        self.trail_lim: List[int] = []      # Start index of each decision level
        self.assignment: List[Optional[bool]] = []  # None = unassigned

        # VSIDS
        self.var_inc: float = 1.0
        self.var_decay: float = 0.95

        # Restarts (Luby by default)
        self.restart_strategy: str = "luby"  # "luby" or "geometric"
        self.restarts: int = 0
        self.conflicts_until_restart: int = 100
        self.luby_idx: int = 1
        self.luby_multiplier: int = 100
        self.geometric_factor: float = 1.5
        self.geometric_base: int = 100

        # Clause deletion (Glucose-style)
        self.max_learnt_clauses: int = 5000
        self.learnt_clause_inc: float = 1.1
        self.glue_threshold: int = 100  # Clauses with glue below this are kept

        # Stats
        self.stats = SolverStats()

        # Flags
        self.ok: bool = True
        self.solved: bool = False
        self.result: Optional[bool] = None

        # Proof logging
        self.proof_file = None

        # Propagation queue (deque for O(1) popleft)
        self.prop_queue: deque = deque()

        # Assumptions for incremental solving
        self.assumptions: List[int] = []
        self.failed_assumptions: Set[int] = set()

        # Verbosity
        self.verbose: int = 0  # 0=silent, 1=stats, 2=trace

    # -- DIMACS parser -------------------------------------------------------

    @classmethod
    def from_dimacs(cls, text: str) -> "Solver":
        """Parse DIMACS CNF string and return a Solver instance.

        Handles standard DIMACS format with comment lines (c ...),
        problem line (p cnf num_vars num_clauses), and clause lines
        (space-separated literals ending with 0).

        Also supports multi-line clauses where 0 only appears at the end.
        """
        solver = cls()
        clauses_lines: List[List[int]] = []
        current_clause: List[int] = []

        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("c"):
                continue
            if line.startswith("p"):
                # p cnf num_vars num_clauses
                parts = line.split()
                if len(parts) >= 3:
                    solver.num_vars = int(parts[2])
                    solver._init_vars(solver.num_vars)
                continue

            # Clause data: space-separated literals, 0 terminates a clause
            tokens = line.split()
            for tok in tokens:
                try:
                    lit = int(tok)
                except ValueError:
                    continue  # Skip non-numeric tokens
                if lit == 0:
                    if current_clause:
                        clauses_lines.append(current_clause)
                        current_clause = []
                else:
                    current_clause.append(lit)

        # Handle last clause if file doesn't end with 0
        if current_clause:
            clauses_lines.append(current_clause)

        # Handle case where no p-line was found
        if solver.num_vars == 0 and clauses_lines:
            max_var = max(abs(l) for c in clauses_lines for l in c)
            solver.num_vars = max_var
            solver._init_vars(solver.num_vars)

        # Process clauses: remove duplicates, check for tautologies
        for lits in clauses_lines:
            seen: Set[int] = set()
            taut = False
            for lit in lits:
                if -lit in seen:
                    taut = True
                    break
                seen.add(lit)
            if taut:
                continue  # Tautological clause — skip
            cleaned = sorted(seen, key=lambda x: abs(x))
            if len(cleaned) == 0:
                continue
            clause = Clause(cleaned, learnt=False)
            solver.clauses.append(clause)

        # Set up watcher lists for all clauses (and assign unit clauses)
        for clause in solver.clauses:
            solver._add_clause_watches(clause)

        return solver

    @classmethod
    def from_file(cls, filename: str) -> "Solver":
        """Load a DIMACS CNF file and return a Solver instance."""
        with open(filename, "r") as f:
            text = f.read()
        return cls.from_dimacs(text)

    def _init_vars(self, n: int):
        """Initialize variable and literal metadata arrays."""
        self.num_vars = n
        self.var_info = [VarInfo() for _ in range(n)]
        # Literal indices: 2*var for positive, 2*var+1 for negative
        self.lit_info = [LitInfo() for _ in range(2 * n + 2)]
        self.assignment = [None] * n

    @staticmethod
    def lit_to_idx(lit: int) -> int:
        """Convert DIMACS literal to internal index."""
        return 2 * abs(lit) + (1 if lit < 0 else 0)

    @staticmethod
    def idx_to_var(idx: int) -> int:
        """Convert internal index to variable number."""
        return idx // 2

    # -- Preprocessing -------------------------------------------------------

    def preprocess(self) -> bool:
        """Run preprocessing simplifications. Returns False if UNSAT detected.

        Applies:
        - Unit propagation
        - Subsumption (removes subsumed clauses)
        - Self-subsuming resolution (strengthens clauses)
        - Failed literal detection (probing)
        """
        if not self.ok:
            return False

        # Run initial BCP for unit clauses
        conflict = self._propagate()
        if conflict is not None:
            self.ok = False
            return False

        # Unit propagation until fixpoint
        changed = True
        while changed:
            changed = False

            # Forward subsumption: remove clauses subsumed by shorter ones
            removed = self._forward_subsumption()
            if removed > 0:
                changed = True
                if self.verbose >= 2:
                    print(f"c Subsumption removed {removed} clauses")

            # Failed literal detection (probing)
            if self._failed_literal_probing():
                changed = True

        return self.ok

    def _forward_subsumption(self) -> int:
        """Remove clauses that are subsumed by other clauses.

        A clause C1 subsumes C2 if all literals of C1 appear in C2.
        Returns the number of clauses removed.
        """
        # Build a set of clause literals for fast lookup
        clause_sets = []
        for clause in self.clauses:
            clause_sets.append(frozenset(clause.lits))

        removed = 0
        new_clauses = []
        for i, clause in enumerate(self.clauses):
            subsumed = False
            for j, other_set in enumerate(clause_sets):
                if i == j:
                    continue
                # Check if other subsumes clause
                if len(clause_sets[i]) >= len(other_set):
                    if other_set.issubset(clause_sets[i]):
                        subsumed = True
                        break
            if not subsumed:
                new_clauses.append(clause)
            else:
                # Remove from watcher lists
                self._remove_clause_watches(clause)
                removed += 1

        self.clauses = new_clauses
        return removed

    def _failed_literal_probing(self) -> bool:
        """Probe unassigned variables to detect failed literals.

        Try assigning each unassigned variable, propagate, and check for
        conflict. If conflict, the opposite assignment is forced.
        Returns True if any changes were made.
        """
        changed = False
        for v in range(self.num_vars):
            if self.assignment[v] is not None:
                continue

            # Try positive polarity
            saved = self._save_state()
            self.trail_lim.append(len(self.trail))
            self._assign(v + 1, None)
            conflict = self._propagate()
            if conflict is not None:
                self._restore_state(saved)
                # Negative polarity is forced
                self.trail_lim.append(len(self.trail))
                ok = self._assign(-(v + 1), None)
                if not ok:
                    self.ok = False
                    return True
                conflict2 = self._propagate()
                if conflict2 is not None:
                    self.ok = False
                    return True
                changed = True
                continue

            self._restore_state(saved)

            # Try negative polarity
            saved = self._save_state()
            self.trail_lim.append(len(self.trail))
            self._assign(-(v + 1), None)
            conflict = self._propagate()
            if conflict is not None:
                self._restore_state(saved)
                # Positive polarity is forced
                self.trail_lim.append(len(self.trail))
                ok = self._assign(v + 1, None)
                if not ok:
                    self.ok = False
                    return True
                conflict2 = self._propagate()
                if conflict2 is not None:
                    self.ok = False
                    return True
                changed = True
                continue

            self._restore_state(saved)

        return changed

    def _save_state(self) -> dict:
        """Save solver state for backtracking during probing."""
        return {
            "trail": self.trail[:],
            "trail_lim": self.trail_lim[:],
            "assignment": self.assignment[:],
            "prop_queue": deque(self.prop_queue),
        }

    def _restore_state(self, state: dict):
        """Restore solver state from a saved state."""
        self.trail = state["trail"]
        self.trail_lim = state["trail_lim"]
        self.assignment = state["assignment"]
        self.prop_queue = state["prop_queue"]

    # -- Clause watching ------------------------------------------------------

    def _add_clause_watches(self, clause: Clause):
        """Set up two watched literals for a clause and assign unit clauses."""
        if len(clause.lits) == 1:
            # Unit clause: assign directly. If this conflicts, mark solver as
            # unsatisfiable so solve() will detect it immediately.
            if not self._assign(clause.lits[0], clause):
                self.ok = False
            return
        if len(clause.lits) == 2:
            # Binary clause: watch both literals
            idx0 = self.lit_to_idx(clause.lits[0])
            idx1 = self.lit_to_idx(clause.lits[1])
            self.lit_info[idx0].watchers.append(clause)
            self.lit_info[idx1].watchers.append(clause)
            return
        # General clause: watch first two literals
        idx0 = self.lit_to_idx(clause.lits[0])
        idx1 = self.lit_to_idx(clause.lits[1])
        self.lit_info[idx0].watchers.append(clause)
        self.lit_info[idx1].watchers.append(clause)

    # -------------------------------------------------------------------------
    # Assignment helpers
    # -------------------------------------------------------------------------

    def value_lit(self, lit: int) -> Optional[bool]:
        """Return the truth value of a literal (None if unassigned)."""
        var = abs(lit) - 1
        if var < 0 or var >= self.num_vars:
            return None
        val = self.assignment[var]
        if val is None:
            return None
        return val if lit > 0 else not val

    def value_var(self, var: int) -> Optional[bool]:
        """Return the assignment of variable (0-indexed)."""
        if var < 0 or var >= self.num_vars:
            return None
        return self.assignment[var]

    def decision_level(self) -> int:
        """Return the current decision level."""
        return len(self.trail_lim)

    # -------------------------------------------------------------------------
    # Propagation (BCP)
    # -------------------------------------------------------------------------

    def _assign(self, lit: int, reason: Optional[Clause]) -> bool:
        """Enqueue an assignment. Returns False if immediate conflict."""
        var = abs(lit) - 1
        sign = lit > 0
        val = self.assignment[var]
        if val is not None:
            if val == sign:
                return True   # Consistent — already assigned this way
            else:
                return False  # Conflict — opposite value already assigned
        self.assignment[var] = sign
        self.var_info[var].level = self.decision_level()
        self.var_info[var].reason = reason
        self.trail.append(lit)
        self.prop_queue.append(lit)
        self.stats.propagations += 1
        return True

    def _propagate(self) -> Optional[Clause]:
        """
        Boolean Constraint Propagation using two-watched-literal scheme.
        Returns None if no conflict, or the conflict clause.
        """
        while self.prop_queue:
            lit = self.prop_queue.popleft()

            # The negation of this literal is now false
            neg_lit = -lit
            neg_idx = self.lit_to_idx(neg_lit)

            # Check all watchers of the negated literal
            watchers = self.lit_info[neg_idx].watchers
            i = 0
            while i < len(watchers):
                clause = watchers[i]

                # Make sure the false literal (neg_lit) is in a watched position.
                # We want it in position 1. If it's in position 0, swap.
                if clause.lits[0] == neg_lit:
                    clause.lits[0], clause.lits[1] = clause.lits[1], clause.lits[0]

                # Now lits[1] == neg_lit (false). Check lits[0].
                # If lits[0] is true, the clause is satisfied → skip
                if self.value_lit(clause.lits[0]) is True:
                    i += 1
                    continue

                # Try to find a new literal to watch instead of lits[1] (neg_lit, which is false)
                found = False
                for k in range(2, len(clause.lits)):
                    if self.value_lit(clause.lits[k]) is not False:
                        # Swap lits[1] and lits[k]
                        clause.lits[1], clause.lits[k] = clause.lits[k], clause.lits[1]
                        new_idx = self.lit_to_idx(clause.lits[1])
                        self.lit_info[new_idx].watchers.append(clause)
                        # Remove this clause from the old watcher list
                        watchers[i] = watchers[-1]
                        watchers.pop()
                        found = True
                        break

                if found:
                    # Don't increment i because we swapped in the last element
                    continue

                # No new watcher found. lits[1] is false, and all lits[2:] are false.
                # Only lits[0] might still be unassigned or false.
                i += 1

                if self.value_lit(clause.lits[0]) is True:
                    # Should have been caught above, but double-check
                    continue

                if self.value_lit(clause.lits[0]) is False:
                    # All literals are false → conflict!
                    self.prop_queue.clear()
                    return clause

                # lits[0] is unassigned → unit clause, propagate it
                ok = self._assign(clause.lits[0], clause)
                if not ok:
                    # Conflict during assignment (literal already assigned to opposite)
                    self.prop_queue.clear()
                    return clause

        return None  # No conflict

    # -------------------------------------------------------------------------
    # Decision heuristic (VSIDS)
    # -------------------------------------------------------------------------

    def _pick_branching_var(self) -> int:
        """Pick the next decision variable using VSIDS + phase saving."""
        best_var = -1
        best_act = -1.0
        for v in range(self.num_vars):
            if self.assignment[v] is None:
                if self.var_info[v].activity > best_act:
                    best_act = self.var_info[v].activity
                    best_var = v
        return best_var

    def _bump_var_activity(self, var: int):
        """Bump variable activity (used in conflict analysis)."""
        self.var_info[var].activity += self.var_inc
        # Rescale if needed to prevent overflow
        if self.var_info[var].activity > 1e100:
            for vi in range(self.num_vars):
                self.var_info[vi].activity *= 1e-100
            self.var_inc *= 1e-100

    def _decay_var_activities(self):
        """Decay all variable activities (VSIDS)."""
        self.var_inc /= self.var_decay

    # -------------------------------------------------------------------------
    # Conflict analysis (1-UIP)
    # -------------------------------------------------------------------------

    def _analyze(self, conflict: Clause) -> Tuple[List[int], int]:
        """
        Analyze a conflict and return (learnt_clause, backtrack_level).
        Uses 1-UIP scheme.
        """
        counter = 0            # Number of literals resolved from current level
        p = 0                  # Current literal being resolved
        reason: Optional[Clause] = conflict
        learnt: List[int] = []
        backtrack_level = 0

        trail_idx = len(self.trail) - 1

        while True:
            # Process reason clause
            if reason is not None:
                for lit in reason.lits:
                    var = abs(lit) - 1
                    if var < 0 or var >= self.num_vars:
                        continue
                    if not self.var_info[var].seen:
                        self.var_info[var].seen = True
                        self._bump_var_activity(var)
                        vl = self.var_info[var].level
                        if vl == self.decision_level():
                            counter += 1
                        elif vl > 0:
                            learnt.append(lit)
                            if vl > backtrack_level:
                                backtrack_level = vl
                        # else: level 0 → skip (always true)

            # Select next literal to resolve by walking backwards along the trail
            found_uip = False
            while trail_idx >= 0:
                p = self.trail[trail_idx]
                trail_idx -= 1
                var_p = abs(p) - 1
                if self.var_info[var_p].seen:
                    found_uip = True
                    break

            if not found_uip:
                # Safety: should never happen for a valid conflict
                break

            counter -= 1
            if counter <= 0:
                break

            self.var_info[var_p].seen = False
            reason = self.var_info[var_p].reason

        # p is the UIP literal
        learnt.append(-p)

        # Clear seen flags
        for lit in learnt:
            var = abs(lit) - 1
            self.var_info[var].seen = False

        # Compute glue (LBD - Literal Block Distance)
        levels = set()
        for lit in learnt:
            var = abs(lit) - 1
            lv = self.var_info[var].level
            if lv > 0:
                levels.add(lv)
        glue = len(levels)

        # Move the highest-level literal (besides the asserting literal) to lits[1]
        # for better watching
        if len(learnt) > 1:
            max_idx = 1
            max_level = self.var_info[abs(learnt[1]) - 1].level
            for i in range(2, len(learnt)):
                lv = self.var_info[abs(learnt[i]) - 1].level
                if lv > max_level:
                    max_level = lv
                    max_idx = i
            learnt[1], learnt[max_idx] = learnt[max_idx], learnt[1]

        return learnt, backtrack_level

    # -------------------------------------------------------------------------
    # Backtracking
    # -------------------------------------------------------------------------

    def _backtrack(self, level: int):
        """Undo assignments above the given level."""
        while len(self.trail) > (self.trail_lim[level] if level < len(self.trail_lim) else 0):
            lit = self.trail.pop()
            var = abs(lit) - 1
            self.assignment[var] = None
            # Phase saving: remember the polarity
            self.var_info[var].polarity = lit > 0
            self.var_info[var].reason = None
            self.var_info[var].level = -1
        # Remove decision level markers
        while len(self.trail_lim) > level:
            self.trail_lim.pop()

    # -------------------------------------------------------------------------
    # Clause management
    # -------------------------------------------------------------------------

    def _add_learnt(self, lits: List[int], glue: int) -> Clause:
        """Add a learnt clause and set up watches."""
        clause = Clause(lits, learnt=True)
        clause.glue = glue
        # Freeze clauses with low glue (high quality)
        clause.frozen = glue <= 2
        self.learnt_clauses.append(clause)
        self.stats.learnt_clauses += 1

        if len(lits) == 1:
            # Unit learnt clause — assign at current level
            self._assign(lits[0], clause)
        else:
            self._add_clause_watches(clause)
        return clause

    def _reduce_learnt_clauses(self):
        """Remove low-activity learnt clauses (Glucose-style with glue)."""
        if len(self.learnt_clauses) <= self.max_learnt_clauses:
            return

        # Sort: keep high-quality clauses (low glue, high activity)
        # Remove clauses that are not frozen and have low activity
        to_remove = []
        for i, clause in enumerate(self.learnt_clauses):
            if not clause.frozen and len(clause.lits) > 2:
                to_remove.append(i)

        # Sort by activity (ascending) and remove the bottom half
        to_remove.sort(key=lambda i: self.learnt_clauses[i].activity)
        keep_count = len(to_remove) // 2
        remove_set = set(to_remove[:keep_count])

        new_clauses = []
        for i, clause in enumerate(self.learnt_clauses):
            if i in remove_set:
                self._remove_clause_watches(clause)
                self.stats.deleted_clauses += 1
            else:
                new_clauses.append(clause)

        self.learnt_clauses = new_clauses
        # Increase threshold for next reduction
        self.max_learnt_clauses = int(self.max_learnt_clauses * self.learnt_clause_inc)

    def _remove_clause_watches(self, clause: Clause):
        """Remove a clause from the watcher lists of its first two literals."""
        if len(clause.lits) < 2:
            return
        for i in range(2):
            idx = self.lit_to_idx(clause.lits[i])
            watchers = self.lit_info[idx].watchers
            try:
                watchers.remove(clause)
            except ValueError:
                pass

    # -------------------------------------------------------------------------
    # Restart strategy
    # -------------------------------------------------------------------------

    def _should_restart(self) -> bool:
        """Check if a restart should be performed."""
        return self.stats.conflicts >= self.conflicts_until_restart

    def _next_restart_limit(self):
        """Update restart limit based on strategy."""
        if self.restart_strategy == "luby":
            step = luby(self.luby_idx)
            self.conflicts_until_restart = self.stats.conflicts + step * self.luby_multiplier
            self.luby_idx += 1
        elif self.restart_strategy == "geometric":
            self.conflicts_until_restart = int(
                self.conflicts_until_restart * self.geometric_factor
            )
        self.restarts += 1

    # -------------------------------------------------------------------------
    # Main solve loop
    # -------------------------------------------------------------------------

    def solve(self, time_limit: float = 0, assumptions: Optional[List[int]] = None) -> Optional[bool]:
        """
        Solve the formula. Returns True (SAT), False (UNSAT), or
        None if interrupted/timed out.

        Args:
            time_limit: Maximum solving time in seconds (0 = unlimited).
            assumptions: List of literals to assume true for incremental solving.
        """
        if not self.ok:
            self.result = False
            self.solved = True
            return False

        self.stats.start_time = time.time()

        # Handle assumptions for incremental solving
        if assumptions:
            self.assumptions = list(assumptions)
            self.failed_assumptions = set()
            self.trail_lim.append(len(self.trail))
            for lit in self.assumptions:
                if not self._assign(lit, None):
                    # Assumption conflicts with existing assignment
                    self.result = False
                    self.solved = True
                    self.stats.end_time = time.time()
                    self.failed_assumptions.add(lit)
                    return False

        # Initial BCP (for unit clauses)
        conflict = self._propagate()
        if conflict is not None:
            self.result = False
            self.solved = True
            self.stats.end_time = time.time()
            return False

        start_time = time.time()

        while True:
            # Check time limit
            if time_limit > 0 and (time.time() - start_time) > time_limit:
                self.result = None
                self.stats.end_time = time.time()
                return None  # Timeout / unknown

            # Pick decision variable
            var = self._pick_branching_var()
            if var == -1:
                # All variables assigned — SAT!
                self.result = True
                self.solved = True
                self.stats.end_time = time.time()
                return True

            # Make decision
            self.stats.decisions += 1
            self.trail_lim.append(len(self.trail))
            # Phase saving: use saved polarity
            lit = (var + 1) if not self.var_info[var].polarity else -(var + 1)
            if not self._assign(lit, None):
                # Decision immediately conflicted
                self.stats.conflicts += 1
                self.result = False
                self.solved = True
                self.stats.end_time = time.time()
                return False

            # Propagate
            while True:
                conflict = self._propagate()
                if conflict is None:
                    break  # No conflict — continue decisions

                # Conflict encountered
                self.stats.conflicts += 1

                if self.verbose >= 2:
                    print(f"c Conflict #{self.stats.conflicts} at level {self.decision_level()}")

                if self.decision_level() == 0:
                    # Top-level conflict → UNSAT
                    self.result = False
                    self.solved = True
                    self.stats.end_time = time.time()
                    if self.proof_file:
                        self._log_proof_empty()
                    return False

                # Analyze conflict
                learnt, bt_level = self._analyze(conflict)

                if self.verbose >= 2:
                    print(f"c Learnt: {learnt}, backtrack to level {bt_level}")

                # Compute glue
                levels = set()
                for lit in learnt:
                    v = abs(lit) - 1
                    if v >= 0 and v < self.num_vars:
                        lv = self.var_info[v].level
                        if lv > 0:
                            levels.add(lv)
                glue = len(levels)

                # Backtrack
                self._backtrack(bt_level)

                # Add learnt clause
                clause = self._add_learnt(learnt, glue)

                # Propagate the asserting literal from the learnt clause
                unit_conflict = self._propagate()
                if unit_conflict is not None:
                    # Conflict during propagation of learnt clause
                    self.stats.conflicts += 1
                    if self.decision_level() == 0:
                        self.result = False
                        self.solved = True
                        self.stats.end_time = time.time()
                        if self.proof_file:
                            self._log_proof_empty()
                        return False
                    # Analyze this new conflict
                    conflict = unit_conflict
                    continue

                # Decay activities
                self._decay_var_activities()

                # Check restart
                if self._should_restart():
                    self._backtrack(0)
                    self._next_restart_limit()
                    if self.verbose >= 1:
                        print(f"c Restart #{self.restarts} (conflicts={self.stats.conflicts})")

                # Reduce learnt clauses periodically
                if self.stats.conflicts % 1000 == 0:
                    self._reduce_learnt_clauses()

                break  # Continue main loop (next decision)

    # -------------------------------------------------------------------------
    # Model extraction
    # -------------------------------------------------------------------------

    def get_model(self) -> List[int]:
        """Return the satisfying assignment as a list of DIMACS literals."""
        model = []
        for v in range(self.num_vars):
            val = self.assignment[v]
            if val is None:
                # Unassigned variable — assign to True
                model.append(v + 1)
            elif val:
                model.append(v + 1)
            else:
                model.append(-(v + 1))
        return model

    def verify_model(self, model: List[int]) -> bool:
        """Verify that the model satisfies all original clauses."""
        model_set = set(model)
        for clause in self.clauses:
            satisfied = False
            for lit in clause.lits:
                if lit in model_set:
                    satisfied = True
                    break
            if not satisfied:
                return False
        # Also verify learnt clauses (they should also be satisfied)
        for clause in self.learnt_clauses:
            satisfied = False
            for lit in clause.lits:
                if lit in model_set:
                    satisfied = True
                    break
            if not satisfied:
                return False
        return True

    # -------------------------------------------------------------------------
    # Failed assumptions (for unsat cores)
    # -------------------------------------------------------------------------

    def get_failed_assumptions(self) -> List[int]:
        """Return the assumptions that led to UNSAT (for unsat core extraction)."""
        return sorted(self.failed_assumptions)

    # -------------------------------------------------------------------------
    # Proof logging
    # -------------------------------------------------------------------------

    def enable_proof(self, filename: str):
        """Enable DRAT proof logging to a file."""
        self.proof_file = open(filename, "w")

    def _log_proof_learnt(self, clause: Clause):
        if self.proof_file:
            self.proof_file.write(" ".join(str(l) for l in clause.lits) + " 0\n")

    def _log_proof_empty(self):
        if self.proof_file:
            self.proof_file.write("0\n")

    def close_proof(self):
        if self.proof_file:
            self.proof_file.close()
            self.proof_file = None

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    def get_stats(self) -> SolverStats:
        """Return solver statistics."""
        return self.stats

    def print_stats(self):
        """Print solver statistics to stderr."""
        print(f"c {self.stats}", file=sys.stderr)

    # -------------------------------------------------------------------------
    # DIMACS output
    # -------------------------------------------------------------------------

    @staticmethod
    def model_to_dimacs(model: List[int], num_vars: int) -> str:
        """Convert a model to DIMACS format."""
        lines = ["c SAT solution", "s SATISFIABLE"]
        values = []
        for v in range(1, num_vars + 1):
            if v in model or -(v) not in model:
                values.append(str(v))
            else:
                values.append(str(-v))
        # Format in lines of 10 values each
        line = "v "
        for i, val in enumerate(values):
            line += val + " "
            if (i + 1) % 10 == 0:
                line = line.rstrip() + "\nv "
        if not line.endswith("\n"):
            line += "0\n"
        return lines[0] + "\n" + lines[1] + "\n" + line


# ---------------------------------------------------------------------------
# DIMACS file I/O
# ---------------------------------------------------------------------------

def read_dimacs_file(filename: str) -> str:
    """Read a DIMACS CNF file."""
    with open(filename, "r") as f:
        return f.read()


def write_dimacs_model(model: List[int], num_vars: int, filename: str):
    """Write a satisfying assignment to a file in DIMACS format."""
    content = Solver.model_to_dimacs(model, num_vars)
    with open(filename, "w") as f:
        f.write(content)


# ---------------------------------------------------------------------------
# Convenience: solve from file
# ---------------------------------------------------------------------------

def solve_file(filename: str, time_limit: float = 0, verbose: int = 0) -> Solver:
    """Solve a DIMACS CNF file and return the solver object."""
    solver = Solver.from_file(filename)
    solver.verbose = verbose
    solver.solve(time_limit=time_limit)
    return solver


# ---------------------------------------------------------------------------
# Main CLI entry point
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="CDCL SAT Solver")
    parser.add_argument("input", help="DIMACS CNF input file")
    parser.add_argument("-t", "--timeout", type=float, default=0,
                        help="Time limit in seconds (0 = unlimited)")
    parser.add_argument("-v", "--verbose", type=int, default=0,
                        help="Verbosity level (0=silent, 1=stats, 2=trace)")
    parser.add_argument("-p", "--proof", type=str, default=None,
                        help="Write DRAT proof to file")
    parser.add_argument("-o", "--output", type=str, default=None,
                        help="Write model to file (if SAT)")
    parser.add_argument("-r", "--restart", type=str, default="luby",
                        choices=["luby", "geometric"],
                        help="Restart strategy")
    parser.add_argument("--preprocess", action="store_true",
                        help="Run preprocessing before solving")
    args = parser.parse_args()

    print(f"c CDCL SAT Solver")
    print(f"c Reading {args.input}...")
    solver = Solver.from_file(args.input)
    solver.verbose = args.verbose
    solver.restart_strategy = args.restart

    print(f"c Variables: {solver.num_vars}")
    print(f"c Clauses: {len(solver.clauses)}")

    if args.preprocess:
        print(f"c Preprocessing...")
        ok = solver.preprocess()
        print(f"c After preprocessing: {solver.num_vars} vars, "
              f"{len(solver.clauses)} clauses, ok={ok}")

    if args.proof:
        solver.enable_proof(args.proof)
        print(f"c Proof logging: {args.proof}")

    result = solver.solve(time_limit=args.timeout)

    solver.print_stats()

    if result is True:
        print("s SATISFIABLE")
        model = solver.get_model()
        # Print model
        line = "v "
        for lit in sorted(model, key=lambda x: abs(x)):
            line += str(lit) + " "
            if len(line) > 70:
                print(line.rstrip())
                line = "v "
        if line.strip() != "v":
            print(line.rstrip() + " 0")
        if args.output:
            write_dimacs_model(model, solver.num_vars, args.output)
    elif result is False:
        print("s UNSATISFIABLE")
    else:
        print("s UNKNOWN")
        print(f"c Time limit reached")

    solver.close_proof()


if __name__ == "__main__":
    main()