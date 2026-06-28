"""
A compact CDCL (Conflict-Driven Clause Learning) SAT solver used as the
Boolean backbone of the DPLL(T) SMT solver.

Features:
  - Unit propagation with watched literals
  - VSIDS decision heuristic
  - Conflict analysis with 1-UIP clause learning
  - Non-chronological backtracking
  - Luby restart schedule

The solver is designed to be called from the DPLL(T) loop, which can
inject theory lemmas and inspect the current Boolean assignment.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

# Literal = nonzero int.  Variable v ∈ {1..n}; literal ±v.
# Clause = list of literals (mutable, for watch swapping).


class CDCLSatSolver:
    """Mini-CDCL with watched literals and VSIDS."""

    def __init__(self):
        self.num_vars: int = 0
        self.clauses: List[List[int]] = []
        self.assignment: Dict[int, Optional[bool]] = {}
        self.level: Dict[int, int] = {}
        self.reason: Dict[int, Optional[List[int]]] = {}
        self.trail: List[int] = []
        self.trail_lim: List[int] = []
        # Watched literals: lit -> list of clause indices that watch lit
        self.watches: Dict[int, List[int]] = {}
        self.activity: Dict[int, float] = {}
        self.var_inc: float = 1.0
        self.var_decay: float = 0.95
        self.conflicts: int = 0
        self._propagated: int = 0  # trail pointer for propagation
        self._conflict: Optional[List[int]] = None

    # ------------------------------------------------------------------
    # Variable / clause management
    # ------------------------------------------------------------------

    def new_var(self) -> int:
        self.num_vars += 1
        v = self.num_vars
        self.assignment[v] = None
        self.level[v] = 0
        self.reason[v] = None
        self.activity[v] = 0.0
        return v

    def ensure_var(self, v: int):
        while self.num_vars < v:
            self.new_var()

    def add_clause(self, lits: List[int]) -> bool:
        """Add a clause.  Returns False if the empty clause is added."""
        # Remove duplicates, detect tautology
        s = set(lits)
        if any(-l in s for l in s):
            return True  # tautology
        lits = list(s)
        for lit in lits:
            self.ensure_var(abs(lit))
        if not lits:
            return False
        # Simplify: if any literal already true, skip
        for lit in lits:
            if self._value(lit) is True:
                return True
        # If all false except possibly one → unit / conflict
        unassigned = [lit for lit in lits if self._value(lit) is None]
        if len(unassigned) <= 1:
            if not unassigned:
                return False  # all false → conflict
            return self._enqueue(unassigned[0], None)

        idx = len(self.clauses)
        self.clauses.append(lits)
        self._watch(idx, lits[0])
        self._watch(idx, lits[1])
        return True

    def _watch(self, clause_idx: int, lit: int):
        """Watch *lit* in clause *clause_idx*."""
        self.watches.setdefault(lit, []).append(clause_idx)

    # ------------------------------------------------------------------
    # Values / propagation
    # ------------------------------------------------------------------

    def _value(self, lit: int) -> Optional[bool]:
        v = abs(lit)
        a = self.assignment[v]
        if a is None:
            return None
        return a if lit > 0 else (not a)

    def _enqueue(self, lit: int, reason: Optional[List[int]]) -> bool:
        v = abs(lit)
        val = lit > 0
        cur = self.assignment[v]
        if cur is not None:
            return cur == val
        self.assignment[v] = val
        self.level[v] = self._decision_level()
        self.reason[v] = reason
        self.trail.append(lit)
        return True

    def _decision_level(self) -> int:
        return len(self.trail_lim)

    def new_decision_level(self):
        self.trail_lim.append(len(self.trail))

    def propagate(self) -> Optional[List[int]]:
        """Propagate.  Returns conflict clause (list of lits) or None."""
        while self._propagated < len(self.trail):
            lit = self.trail[self._propagated]
            self._propagated += 1
            # Clauses watching -lit need attention (since lit is now true, -lit is false)
            neg = -lit
            watch_list = self.watches.get(neg, [])
            i = 0
            new_watch_list: List[int] = []
            while i < len(watch_list):
                cidx = watch_list[i]
                clause = self.clauses[cidx]
                # Ensure clause[1] is the falsified literal
                if clause[0] == neg:
                    clause[0], clause[1] = clause[1], clause[0]
                # If clause[0] is true, clause is satisfied
                if self._value(clause[0]) is True:
                    new_watch_list.append(cidx)
                    i += 1
                    continue
                # Find new literal to watch
                found = False
                for k in range(2, len(clause)):
                    if self._value(clause[k]) is not False:
                        clause[1], clause[k] = clause[k], clause[1]
                        self._watch(cidx, clause[1])
                        found = True
                        break
                if found:
                    i += 1
                    continue
                # No new watch: clause is unit or conflict
                new_watch_list.append(cidx)
                i += 1
                if self._value(clause[0]) is False:
                    # Conflict
                    self.watches[neg] = new_watch_list + watch_list[i:]
                    self._conflict = clause
                    return clause
                else:
                    if not self._enqueue(clause[0], clause):
                        self.watches[neg] = new_watch_list + watch_list[i:]
                        self._conflict = [clause[0], -clause[0]]
                        return self._conflict
            self.watches[neg] = new_watch_list
        self._conflict = None
        return None

    # ------------------------------------------------------------------
    # Conflict analysis (1-UIP)
    # ------------------------------------------------------------------

    def _analyze(self, conflict: List[int]) -> Tuple[List[int], int]:
        learnt: List[int] = []
        seen: Set[int] = set()
        counter = 0
        p: int = 0
        current = conflict
        trail_idx = len(self.trail) - 1

        while True:
            for lit in current:
                v = abs(lit)
                if v in seen:
                    continue
                self._bump(v)
                seen.add(v)
                if self.level.get(v, 0) == self._decision_level():
                    counter += 1
                elif self.level.get(v, 0) > 0:
                    learnt.append(lit)

            while trail_idx >= 0 and abs(self.trail[trail_idx]) not in seen:
                trail_idx -= 1
            if trail_idx < 0:
                break
            p = self.trail[trail_idx]
            trail_idx -= 1
            counter -= 1
            if counter <= 0:
                break
            r = self.reason.get(abs(p))
            if r is None:
                break
            current = r

        learnt.append(-p)

        # Backtrack level = highest level in learnt[1:]
        bt = 0
        for lit in learnt[1:]:
            lv = self.level.get(abs(lit), 0)
            if lv > bt:
                bt = lv
        return learnt, bt

    def _bump(self, v: int):
        self.activity[v] = self.activity.get(v, 0.0) + self.var_inc
        if self.activity[v] > 1e100:
            for k in self.activity:
                self.activity[k] *= 1e-100
            self.var_inc *= 1e-100

    # ------------------------------------------------------------------
    # Backtracking
    # ------------------------------------------------------------------

    def cancel_until(self, level: int):
        while len(self.trail_lim) > level:
            limit = self.trail_lim.pop()
            while len(self.trail) > limit:
                lit = self.trail.pop()
                v = abs(lit)
                self.assignment[v] = None
                self.reason[v] = None
                self.level[v] = 0
        # Fix: reset _propagated pointer to match the trail length.
        # This is critical for the DPLL(T) loop: after cancel_until(0),
        # the trail is empty so _propagated must also be 0, ensuring
        # the next solve() call starts a fresh search from level 0.
        self._propagated = len(self.trail)

    # ------------------------------------------------------------------
    # Solve
    # ------------------------------------------------------------------

    def solve(self, max_conflicts: int = 50000, assumption: Optional[List[int]] = None) -> str:
        """Solve with optional assumption literals.  Returns 'sat'/'unsat'/'unknown'."""
        # Enqueue assumptions at level 0
        if assumption:
            for lit in assumption:
                if not self._enqueue(lit, None):
                    return "unsat"
            if self.propagate() is not None:
                return "unsat"

        restart_base = 100
        luby_i = 1
        restart_count = 0
        total_conflicts = 0

        while True:
            conflict = self.propagate()
            if conflict is not None:
                total_conflicts += 1
                self.conflicts += 1
                if self._decision_level() == 0:
                    return "unsat"
                learnt, bt = self._analyze(conflict)
                self.cancel_until(bt)
                # Add learned clause
                if len(learnt) == 1:
                    self._enqueue(learnt[0], None)
                else:
                    cidx = len(self.clauses)
                    self.clauses.append(learnt)
                    self._watch(cidx, learnt[0])
                    self._watch(cidx, learnt[1])
                    self._enqueue(learnt[0], learnt)
                self.var_inc /= self.var_decay
                restart_count += 1
                if restart_count >= restart_base * _luby(luby_i):
                    luby_i += 1
                    restart_count = 0
                    self.cancel_until(0)
                continue

            if total_conflicts >= max_conflicts:
                return "unknown"

            # All assigned?
            unassigned = [v for v in range(1, self.num_vars + 1) if self.assignment[v] is None]
            if not unassigned:
                return "sat"

            # Decide: VSIDS
            var = max(unassigned, key=lambda v: self.activity.get(v, 0.0))
            self.new_decision_level()
            self._enqueue(var if self.activity.get(var, 0.0) >= 0 else -var, None)

    # ------------------------------------------------------------------
    # Inspection (for DPLL(T))
    # ------------------------------------------------------------------

    def model(self) -> Dict[int, bool]:
        return {v: self.assignment[v] for v in range(1, self.num_vars + 1) if self.assignment[v] is not None}


def _luby(i: int) -> int:
    """Luby sequence value (1-indexed): 1,1,2,1,1,2,4,1,1,2,1,1,2,4,8,..."""
    # Find k such that (2^k - 1) is the largest <= i
    k = 1
    while (1 << k) - 1 <= i:
        k += 1
    k -= 1
    # If i is exactly 2^k - 1, return 2^(k-1)
    if i == (1 << k) - 1:
        return 1 << (k - 1)
    # Otherwise recurse
    return _luby(i - (1 << (k - 1)) + 1) if k > 1 else 1