"""Two-phase Primal Simplex method with exact rational arithmetic.

The implementation here is deliberately *classical* — a dense, dictionary-style
simplex that operates on :class:`fractions.Fraction` so every pivot is
bit-exact.  Phase I minimises the sum of artificials to find a feasible basis;
Phase II optimises the original objective.  Anti-cycling is provided by
Bland's rule (selectable).

Design notes
------------
* The tableau is stored as a list of dicts (sparse rows) of
  :class:`Fraction`, keyed by non-basic column index.
* Slack/surplus variables are added automatically for ``<=`` / ``>=``
  constraints; artificial variables are added for ``=`` and ``>=`` rows.
* Free variables (both bounds ``None``) are split: ``x = x⁺ − x⁻`` with both
  parts non-negative.
* Upper bounds are handled by adding explicit ``x ≤ ub`` constraint rows —
  this keeps the simplex core simple and robust (no bounded-variable ratio
  test needed).
* Lower bounds other than 0 are shifted: ``x' = x − lb``.
* Negative-rhs rows are normalised by negating the entire row *before* fixing
  the basic variable's identity coefficient to +1, ensuring the initial basis
  is always feasible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction

from .problem import LPProblem, LPResult, LPStatus

__all__ = ["SimplexSolver", "Tableau"]

_EPS = Fraction(0)  # exact mode — zero tolerance is exact


@dataclass
class _Var:
    """Metadata for a tableau column."""

    name: str
    cost: Fraction = Fraction(0)        # original objective coefficient
    lb: Fraction | None = Fraction(0)   # None == -inf
    ub: Fraction | None = None          # None == +inf
    is_artificial: bool = False
    is_slack: bool = False
    # original problem variable index, if this is a structural var
    src: int | None = None
    # for free-variable split: partner column index (or None)
    partner: int | None = None


class Tableau:
    """Dense simplex tableau with bounded-variable support.

    Internally the tableau stores, for each constraint row ``i`` and each
    non-basic variable column ``j``::

        row i:  x[B[i]] + sum_j  T[i][j] * x[N[j]] = rhs[i]

    plus a cost row ``z - sum_j c_j x[N[j]] = z0``.  Bounded variables keep
    their bounds in :attr:`_Var.lb`/:attr:`_Var.ub`; the ratio test respects
    them.
    """

    def __init__(self) -> None:
        self.vars: list[_Var] = []
        self.basis: list[int] = []        # indices into self.vars
        self.nonbasis: list[int] = []    # indices into self.vars
        # row data: list of dict {nonbasis_col_idx: coeff}
        self.rows: list[dict[int, Fraction]] = []
        self.rhs: list[Fraction] = []
        self.obj_row: dict[int, Fraction] = {}
        self.obj_const: Fraction = Fraction(0)
        self.artificial_indices: list[int] = []

    # ------------------------------------------------------------------ #
    # introspection
    # ------------------------------------------------------------------ #
    @property
    def num_rows(self) -> int:
        return len(self.rows)

    @property
    def num_cols(self) -> int:
        return len(self.vars)

    def value_of(self, var_idx: int) -> Fraction:
        """Current value of variable ``var_idx`` (basic or non-basic)."""
        v = self.vars[var_idx]
        # If basic, take rhs (assuming non-basic at their lower bound).
        if var_idx in self.basis:
            i = self.basis.index(var_idx)
            return self.rhs[i]
        # Non-basic variables sit at their lower bound by default.
        lb = v.lb if v.lb is not None else Fraction(0)
        return lb

    # ------------------------------------------------------------------ #
    # construction from an LPProblem
    # ------------------------------------------------------------------ #
    @classmethod
    def from_problem(cls, problem: LPProblem) -> "Tableau":
        """Build a tableau from an :class:`LPProblem`.

        Transformations applied
        -----------------------
        * **Free variables** ``(lb=None, ub=None)``: split ``x = x⁺ − x⁻``
          with both parts non-negative.
        * **Lower bound only** ``(lb=None)`` (unbounded below, finite ub):
          substitute ``x = ub − y`` so ``y ≥ 0``; coefficients and rhs are
          adjusted.
        * **Lower bound shift** ``lb != 0``: substitute ``x' = x − lb`` so
          ``x' ≥ 0``; the objective constant absorbs ``c·lb``.
        * **Upper bounds** ``ub``: added as explicit ``x ≤ ub`` constraint rows
          (the bounded-variable ratio test is *not* used — explicit rows keep
          the simplex logic simple and robust).

        After these substitutions every structural variable is non-negative
        with no upper bound, so a classical Phase-I / Phase-II simplex with
        slack and artificial variables is sufficient.
        """
        t = cls()
        sign = Fraction(1) if problem.objective == "max" else Fraction(-1)
        # 1. Register structural variables.
        var_index: dict[str, int] = {}
        upper_bound_constraints: list[tuple[str, Fraction]] = []
        for i, vname in enumerate(problem.variables):
            lb, ub = problem.bounds.get(vname, (Fraction(0), None))
            coeff = problem.objective_coeffs.get(vname, Fraction(0))
            if lb is None and ub is None:
                # free variable: x = x⁺ − x⁻
                vp = _Var(name=vname, cost=coeff * sign, lb=Fraction(0), ub=None, src=i)
                vm = _Var(name=vname + "_neg", cost=-coeff * sign, lb=Fraction(0), ub=None, src=i, partner=None)
                ip = len(t.vars)
                t.vars.append(vp)
                im = len(t.vars)
                t.vars.append(vm)
                t.vars[ip].partner = im
                t.vars[im].partner = ip
                var_index[vname] = ip
            elif lb is None:
                # x <= ub, x unbounded below → substitute x = ub − y, y ≥ 0.
                y = _Var(name=vname + "_flip", cost=-coeff * sign, lb=Fraction(0), ub=None, src=i)
                idx = len(t.vars)
                t.vars.append(y)
                var_index[vname] = idx
                # store ub as a constant offset for back-substitution; we tag
                # the variable name suffix "_flip" so extract_solution can
                # recover x = ub − y.
                t.vars[idx].ub = ub
                # objective constant: original obj includes c*ub (constant).
                t.obj_const += coeff * sign * ub
            else:
                # lower-bounded: shift x' = x − lb, x' ≥ 0 (ub handled later).
                v = _Var(name=vname, cost=coeff * sign, lb=Fraction(0),
                         ub=None, src=i)
                idx = len(t.vars)
                t.vars.append(v)
                var_index[vname] = idx
                # objective shift: original obj = c·(x'+lb) → add c·lb.
                t.obj_const += coeff * sign * lb
                # queue an explicit upper-bound constraint if ub is finite.
                if ub is not None:
                    upper_bound_constraints.append((vname, ub))

        # 2. Build the user-supplied constraints.
        for ci, con in enumerate(problem.constraints):
            rel = con["relation"]
            rhs = Fraction(con["rhs"])
            row: dict[int, Fraction] = {}
            for vname, a in con["coeffs"].items():
                if vname not in var_index:
                    raise ValueError(f"constraint {ci} references unknown var {vname!r}")
                a = Fraction(a)
                idx = var_index[vname]
                v = t.vars[idx]
                if v.partner is not None:
                    # free split: x = x⁺ − x⁻
                    row[idx] = row.get(idx, Fraction(0)) + a
                    row[v.partner] = row.get(v.partner, Fraction(0)) - a
                elif v.name.endswith("_flip") and v.src is not None:
                    # flipped variable x = ub − y, so a·x = a·ub − a·y.
                    row[idx] = row.get(idx, Fraction(0)) - a
                    rhs = rhs - a * v.ub
                else:
                    # shifted variable x' = x − lb; coefficient unchanged,
                    # rhs adjusted by −a·lb.
                    row[idx] = row.get(idx, Fraction(0)) + a
                    src = problem.variables[v.src]
                    lb = problem.bounds.get(src, (Fraction(0), None))[0]
                    if lb:
                        rhs = rhs - a * lb
            t._add_constraint_row(ci, rel, rhs, row)

        # 3. Append explicit upper-bound constraints (one per finite ub).
        ub_start = len(problem.constraints)
        for k, (vname, ub) in enumerate(upper_bound_constraints):
            idx = var_index[vname]
            v = t.vars[idx]
            ci = ub_start + k
            row: dict[int, Fraction] = {idx: Fraction(1)}
            # The bound is x' <= ub − lb (in shifted space); for flipped vars
            # the substitution already encodes x <= ub so we skip.
            if v.name.endswith("_flip"):
                continue
            src = problem.variables[v.src]
            lb = problem.bounds.get(src, (Fraction(0), None))[0]
            ub_rhs = ub - (lb if lb is not None else Fraction(0))
            t._add_constraint_row(ci, "<=", ub_rhs, row, name_prefix="_ub")
        # 4. Build nonbasis list = all vars not in basis, and initialise the
        # objective row with the original reduced costs (artificials have cost
        # 0 and will be repriced during Phase I).
        basis_set = set(t.basis)
        t.nonbasis = [i for i in range(len(t.vars)) if i not in basis_set]
        t.obj_row = {}
        for j in t.nonbasis:
            c = t.vars[j].cost
            if c != 0:
                t.obj_row[j] = c
        return t

    def _add_constraint_row(self, ci: int, rel: str, rhs: Fraction,
                            row: dict[int, Fraction], name_prefix: str = "") -> None:
        """Append a constraint row with slack/surplus/artificial as needed.

        The basic variable for the row always ends up with coefficient +1
        (an identity column).  When the natural sign of the basic variable
        would be −1 (e.g. an artificial on a constraint with negative rhs), we
        multiply the entire row by −1 so the identity property holds and the
        rhs becomes non-negative — the basic variable then starts at a
        feasible value.
        """
        sname = f"{name_prefix}_slack_{ci}"
        aname = f"{name_prefix}_art_{ci}"
        surpname = f"{name_prefix}_surplus_{ci}"
        if rel == "<=":
            s = _Var(name=sname, cost=Fraction(0), lb=Fraction(0), ub=None, is_slack=True)
            sidx = len(self.vars)
            self.vars.append(s)
            if rhs >= 0:
                row[sidx] = Fraction(1)
                self.rhs.append(rhs)
                self.rows.append(row)
                self.basis.append(sidx)
            else:
                # rhs < 0: slack at +1 would be negative.  Use an artificial
                # as the basic variable.  We build the row with the artificial
                # at coefficient -1, then negate the *entire* row so the
                # artificial becomes +1 (identity column) and rhs becomes
                # positive.  The slack coefficient flips from +1 to -1
                # (surplus role, non-basic at 0) — harmless.
                row[sidx] = Fraction(1)   # pre-negation slack coeff
                a = _Var(name=aname, cost=Fraction(0), lb=Fraction(0), ub=None,
                         is_artificial=True)
                aidx = len(self.vars)
                self.vars.append(a)
                row[aidx] = Fraction(-1)  # pre-negation; becomes +1 after
                row = {k: -v for k, v in row.items()}
                self.rhs.append(-rhs)    # now positive
                self.rows.append(row)
                self.basis.append(aidx)
                self.artificial_indices.append(aidx)
        elif rel == ">=":
            s = _Var(name=surpname, cost=Fraction(0), lb=Fraction(0), ub=None, is_slack=True)
            sidx = len(self.vars)
            self.vars.append(s)
            row[sidx] = Fraction(-1)
            a = _Var(name=aname, cost=Fraction(0), lb=Fraction(0), ub=None, is_artificial=True)
            aidx = len(self.vars)
            self.vars.append(a)
            if rhs >= 0:
                row[aidx] = Fraction(1)
                self.rhs.append(rhs)
                self.rows.append(row)
                self.basis.append(aidx)
                self.artificial_indices.append(aidx)
            else:
                # rhs < 0: artificial at +1 would be negative.  Set the
                # artificial coefficient to -1 and negate the entire row so
                # the artificial becomes +1 (identity) and rhs becomes
                # positive.
                row[aidx] = Fraction(-1)
                row = {k: -v for k, v in row.items()}
                self.rhs.append(-rhs)
                self.rows.append(row)
                self.basis.append(aidx)
                self.artificial_indices.append(aidx)
        else:  # "="
            a = _Var(name=aname, cost=Fraction(0), lb=Fraction(0), ub=None, is_artificial=True)
            aidx = len(self.vars)
            self.vars.append(a)
            if rhs >= 0:
                row[aidx] = Fraction(1)
                self.rhs.append(rhs)
                self.rows.append(row)
                self.basis.append(aidx)
                self.artificial_indices.append(aidx)
            else:
                row[aidx] = Fraction(-1)
                row = {k: -v for k, v in row.items()}
                self.rhs.append(-rhs)
                self.rows.append(row)
                self.basis.append(aidx)
                self.artificial_indices.append(aidx)

    # ------------------------------------------------------------------ #
    # core simplex pivoting
    # ------------------------------------------------------------------ #
    def _basic_value(self, i: int) -> Fraction:
        return self.rhs[i]

    def _nonbasic_value(self, j: int) -> Fraction:
        v = self.vars[j]
        return v.lb if v.lb is not None else Fraction(0)

    def _reduced_cost(self, j: int) -> Fraction:
        """Compute reduced cost of non-basic var j (obj_row[j] - sum c_B * a_ij).

        With dictionary form we maintain obj_row directly as reduced costs.
        """
        return self.obj_row.get(j, Fraction(0))

    def _price_out(self, pivot_row: int, pivot_col: int) -> None:
        """Eliminate pivot column from the objective row after a pivot.

        Updates obj_row so that the reduced cost of the entering column is 0
        and other reduced costs are adjusted accordingly.
        """
        # reduced cost of entering var
        rc = self.obj_row.get(pivot_col, Fraction(0))
        if rc == 0:
            return
        # pivot row coefficient for entering col
        pivot_coeff = self.rows[pivot_row].get(pivot_col, Fraction(0))
        # factor = rc / pivot_coeff
        factor = rc / pivot_coeff
        # obj_row -= factor * row
        for k, v in self.rows[pivot_row].items():
            cur = self.obj_row.get(k, Fraction(0))
            cur -= factor * v
            if cur == 0:
                self.obj_row.pop(k, None)
            else:
                self.obj_row[k] = cur
        # entering var reduced cost should now be 0
        self.obj_row.pop(pivot_col, None)
        # adjust objective constant: z0 += factor * rhs
        self.obj_const += factor * self.rhs[pivot_row]

    def _pivot(self, pivot_row: int, pivot_col: int) -> None:
        """Gauss-Jordan pivot on (pivot_row, pivot_col)."""
        pivot_coeff = self.rows[pivot_row].get(pivot_col, Fraction(0))
        if pivot_coeff == 0:
            raise ValueError("pivot on zero coefficient")
        # Normalise pivot row.
        inv = Fraction(1) / pivot_coeff
        new_row = {k: v * inv for k, v in self.rows[pivot_row].items()}
        new_row[pivot_col] = Fraction(1)  # ensure exact 1
        self.rows[pivot_row] = new_row
        self.rhs[pivot_row] *= inv
        # Eliminate pivot column from all other rows.
        for i in range(len(self.rows)):
            if i == pivot_row:
                continue
            coeff = self.rows[i].get(pivot_col, Fraction(0))
            if coeff == 0:
                continue
            # row_i -= coeff * new_row
            for k, v in new_row.items():
                cur = self.rows[i].get(k, Fraction(0))
                cur -= coeff * v
                if cur == 0:
                    self.rows[i].pop(k, None)
                else:
                    self.rows[i][k] = cur
            self.rhs[i] -= coeff * self.rhs[pivot_row]
        # Price out the objective row.
        self._price_out(pivot_row, pivot_col)
        # Update basis/nonbasis.
        leaving = self.basis[pivot_row]
        entering = pivot_col
        self.basis[pivot_row] = entering
        self.nonbasis.remove(entering)
        self.nonbasis.append(leaving)
        # Re-sort nonbasis for determinism (not strictly required).
        # (We keep insertion order to preserve Bland-rule stability.)

    # ------------------------------------------------------------------ #
    # entering / leaving variable selection
    # ------------------------------------------------------------------ #
    def _select_entering(self, bland: bool = True) -> int | None:
        """Choose an entering non-basic variable.

        Returns the nonbasis *column index* (position in self.nonbasis) of the
        entering variable, or ``None`` if no improving direction exists
        (optimal).  With Bland's rule we pick the smallest-index variable
        with positive reduced cost (for a max problem stored in obj_row).
        """
        best: int | None = None
        best_var: int = -1
        best_rc: Fraction = Fraction(0)
        for pos, j in enumerate(self.nonbasis):
            # Artificial variables must never re-enter the basis once they
            # have been driven out (they are Phase-I constructs and allowing
            # them back destroys feasibility of the original objective).
            if self.vars[j].is_artificial:
                continue
            rc = self._reduced_cost(j)
            # For maximisation (we store obj as max internally) we want rc > 0.
            if rc > 0:
                if bland:
                    # smallest variable index among improving columns
                    if best is None or j < best_var:
                        best = pos
                        best_var = j
                        best_rc = rc
                else:
                    # Dantzig's rule: most positive reduced cost.
                    if best is None or rc > best_rc:
                        best = pos
                        best_var = j
                        best_rc = rc
        return best

    def _select_leaving(self, entering_pos: int) -> tuple[int, Fraction] | None:
        """Bounded-variable ratio test.

        Returns ``(pivot_row, step)`` or ``None`` if the problem is unbounded.
        ``step`` is the maximum feasible step length along the entering
        direction.  We consider both:

        * ratio tests against basic variables (their values hitting their
          bounds), and
        * the entering variable hitting its own upper bound.
        """
        entering = self.nonbasis[entering_pos]
        ev = self.vars[entering]
        # Direction coefficients: increasing the entering variable from its
        # current lower bound.  For each basic var i:
        #   x[B[i]] = rhs[i] - sum a_ij x[N[j]]
        # so dx[B[i]]/dx[entering] = -a_ij  (row coefficient).
        min_ratio: Fraction | None = None
        pivot_row: int = -1
        for i in range(len(self.rows)):
            a_ij = self.rows[i].get(entering, Fraction(0))
            if a_ij == 0:
                continue
            bvar = self.basis[i]
            bv = self.vars[bvar]
            cur = self.rhs[i]  # current basic value (relative to its lb)
            if a_ij < 0:
                # increasing entering increases basic var; check upper bound.
                if bv.ub is not None:
                    room = bv.ub - cur  # ≥ 0 if feasible
                    if room < 0:
                        room = Fraction(0)
                    ratio = room / (-a_ij)
                    if min_ratio is None or ratio < min_ratio:
                        min_ratio = ratio
                        pivot_row = i
            else:  # a_ij > 0
                # increasing entering decreases basic var; check lower bound (0).
                ratio = cur / a_ij
                if min_ratio is None or ratio < min_ratio:
                    min_ratio = ratio
                    pivot_row = i
        # Also check the entering variable's own upper bound.
        if ev.ub is not None:
            own = ev.ub  # distance from lower bound (0) to upper bound
            if min_ratio is None or own <= min_ratio:
                # entering hits its own bound before any basic var moves —
                # no pivot needed, just flip the variable to its upper bound.
                return (-1, own)  # sentinel: pivot_row == -1 means "bound flip"
        if min_ratio is None:
            return None  # unbounded
        return (pivot_row, min_ratio)

    # ------------------------------------------------------------------ #
    # solve
    # ------------------------------------------------------------------ #
    def solve(self, max_iter: int = 10_000, bland: bool = True) -> LPStatus:
        """Run Phase II simplex (assumes a feasible starting basis).

        Returns :class:`LPStatus`.  ``OPTIMAL``, ``UNBOUNDED``, or
        ``TIMEOUT`` if the iteration limit is reached.  The number of pivots
        performed is stored in :attr:`num_pivots`.
        """
        self.num_pivots = 0
        for _ in range(max_iter):
            entering_pos = self._select_entering(bland=bland)
            if entering_pos is None:
                return LPStatus.OPTIMAL
            res = self._select_leaving(entering_pos)
            if res is None:
                return LPStatus.UNBOUNDED
            pivot_row, step = res
            if pivot_row == -1:
                # Bound flip (only triggered if a variable has an upper bound,
                # which doesn't occur in the current construction since upper
                # bounds are converted to explicit constraint rows).  Kept
                # for correctness if the tableau is ever constructed with
                # bounded variables directly.
                entering = self.nonbasis[entering_pos]
                ev = self.vars[entering]
                ub = ev.ub
                for i in range(len(self.rows)):
                    a = self.rows[i].get(entering, Fraction(0))
                    if a != 0:
                        self.rhs[i] += a * ub
                rc = self.obj_row.get(entering, Fraction(0))
                if rc != 0:
                    self.obj_const += rc * ub
                for i in range(len(self.rows)):
                    a = self.rows[i].get(entering, Fraction(0))
                    if a != 0:
                        self.rows[i][entering] = -a
                if rc != 0:
                    self.obj_row[entering] = -rc
                self.num_pivots += 1
                continue
            # Perform the pivot.
            entering = self.nonbasis[entering_pos]
            self._pivot(pivot_row, entering)
            self.num_pivots += 1
        return LPStatus.TIMEOUT

    # ------------------------------------------------------------------ #
    # Phase I
    # ------------------------------------------------------------------ #
    def run_phase_one(self, max_iter: int = 10_000, bland: bool = True) -> LPStatus:
        """Minimise the sum of artificials.  Returns OPTIMAL/UNBOUNDED.

        After Phase I, if the optimal value of the artificial sum is > 0 the
        problem is INFEASIBLE.  Otherwise we drive artificials out of the
        basis and restore the original objective.
        """
        if not self.artificial_indices:
            return LPStatus.OPTIMAL
        # Save original objective row; build Phase-I objective (sum of
        # artificials with cost +1, treated as a minimisation → we store as
        # max of -sum → cost -1 on artificials).  Equivalently we want to
        # minimise Σ art  →  equivalently maximise  −Σ art  so the Phase-I
        # reduced-cost rule uses rc > 0 for entering.  We set artificial
        # costs to -1 in a *copy* of obj_row.
        saved_obj = dict(self.obj_row)
        # The construction-time obj_const includes the variable-shift constant
        # (sum c_v * lb_v for shifted vars, plus flip offsets).  We must
        # preserve this through Phase I and re-add it after restoration.
        saved_shift_const = self.obj_const
        # Phase-I objective row: reduced cost of artificials must be 0 if they
        # are basic (they are), and -1 if non-basic.  We compute the proper
        # reduced costs by pricing out: rc_j = c_j - c_B * A_B^-1 * A_j.
        # Since the basis is an identity (slack/artificial columns), c_B for
        # an artificial basic var is -1 (Phase-I cost), 0 otherwise.  So
        # rc_j = c_j - sum_{i: B[i] artificial} (-1) * a_{i,j}.
        self.obj_row = {}
        self.obj_const = Fraction(0)
        art_basic_rows = [
            i for i, b in enumerate(self.basis) if self.vars[b].is_artificial
        ]
        for j in self.nonbasis:
            c_j = Fraction(-1) if self.vars[j].is_artificial else Fraction(0)
            s = c_j
            for i in art_basic_rows:
                s -= Fraction(-1) * self.rows[i].get(j, Fraction(0))
            # s is the reduced cost under the Phase-I objective (max of -sum).
            # For artificials in the nonbasis (shouldn't happen initially)
            # c_j = -1; for structural/slack c_j = 0 and the row contribution
            # is +a_{i,j} (since c_B=-1, -c_B*a = +a).  So:
            #   rc_j = c_j + sum_{art rows} a_{i,j}
            s = c_j + sum(
                (self.rows[i].get(j, Fraction(0))) for i in art_basic_rows
            )
            if s != 0:
                self.obj_row[j] = s
        # obj_const for Phase I: z = -sum(artificials currently basic) = -|art_basic|
        self.obj_const = Fraction(-len(art_basic_rows))
        # Run simplex on Phase-I objective.
        status = self.solve(max_iter=max_iter, bland=bland)
        if status is LPStatus.UNBOUNDED:
            # Phase I cannot be unbounded (artificials are bounded ≥ 0).
            # This indicates a logic error; treat as numerical.
            self.obj_row = saved_obj
            self.obj_const = saved_shift_const
            return LPStatus.NUMERICAL
        if status is LPStatus.TIMEOUT:
            return status
        # Check artificial sum: if any artificial remains basic with a
        # positive value → infeasible.
        for i, b in enumerate(self.basis):
            if self.vars[b].is_artificial and self.rhs[i] > 0:
                # restore objective (best-effort) and report infeasible.
                self.obj_row = saved_obj
                self.obj_const = saved_shift_const
                return LPStatus.INFEASIBLE
        # Drive any remaining (zero-valued) artificials out of the basis.
        for i in range(len(self.basis)):
            if self.vars[self.basis[i]].is_artificial:
                # find a non-basic non-artificial column with nonzero coeff
                # in this row to pivot on.
                pivoted = False
                for j in list(self.nonbasis):
                    if self.vars[j].is_artificial:
                        continue
                    if self.rows[i].get(j, Fraction(0)) != 0:
                        self._pivot(i, j)
                        pivoted = True
                        break
                if not pivoted:
                    # Row is redundant (all zeros); leave artificial in basis
                    # at value 0.  It will be ignored in Phase II.
                    pass
        # Restore original objective row, recomputing reduced costs given the
        # current basis (which is now feasible for the original problem).
        self.obj_row = {}
        self.obj_const = Fraction(0)
        # Recompute c_B * B^-1 contributions.  Since the basis may not be
        # triangular (it's general), we recompute by pricing out from the
        # original costs:  rc_j = c_j - c_B * (B^-1 A_j).  We have, for each
        # basic var b_i with cost c_{b_i}, the row already represents
        # x[b_i] = rhs[i] - sum_j a_{i,j} x[N[j]].  So
        #   rc_j = c_j - sum_i c_{b_i} * a_{i,j}
        # where a_{i,j} = self.rows[i].get(j, 0).  And obj_const = sum_i c_{b_i} rhs[i].
        for j in self.nonbasis:
            c_j = self.vars[j].cost
            rc = c_j
            for i in range(len(self.rows)):
                cb = self.vars[self.basis[i]].cost
                if cb == 0:
                    continue
                rc -= cb * self.rows[i].get(j, Fraction(0))
            if rc != 0:
                self.obj_row[j] = rc
        # Objective constant: z = sum c_B * rhs[i], plus the original
        # construction-time shift constant (c·lb for shifted vars, c·ub for
        # flipped vars) which was saved before Phase I.
        z = Fraction(0)
        for i in range(len(self.rows)):
            cb = self.vars[self.basis[i]].cost
            z += cb * self.rhs[i]
        self.obj_const = z + saved_shift_const
        return LPStatus.OPTIMAL

    # ------------------------------------------------------------------ #
    # solution extraction
    # ------------------------------------------------------------------ #
    def extract_solution(self, problem: LPProblem) -> LPResult:
        """Build an :class:`LPResult` from the current tableau state."""
        # Recover primal values in the *transformed* space.
        raw: dict[int, Fraction] = {}
        for j in self.nonbasis:
            raw[j] = self._nonbasic_value(j)
        for i, b in enumerate(self.basis):
            raw[b] = self.rhs[i]
        # Map back to original variables.
        sol: dict[str, Fraction] = {}
        for vname in problem.variables:
            idx = self._find_var_index(vname)
            if idx is None:
                sol[vname] = Fraction(0)
                continue
            v = self.vars[idx]
            if v.partner is not None:
                # free split x = x⁺ − x⁻
                val = raw.get(idx, Fraction(0)) - raw.get(v.partner, Fraction(0))
            elif v.name.endswith("_flip") and v.src is not None:
                # x = ub − y
                ub = v.ub
                val = ub - raw.get(idx, Fraction(0))
            elif v.src is not None:
                # shifted: x = x' + lb
                lb = problem.bounds.get(problem.variables[v.src], (Fraction(0), None))[0]
                if lb is None:
                    lb = Fraction(0)
                val = raw.get(idx, Fraction(0)) + lb
            else:
                val = raw.get(idx, Fraction(0))
            sol[vname] = val
        # Compute objective.
        obj = Fraction(0)
        for vname in problem.variables:
            obj += problem.objective_coeffs.get(vname, Fraction(0)) * sol[vname]
        # Duals: y_i = c_{B[i]} of the slack/artificial?  For a standard max
        # problem, the dual value for constraint i is the reduced cost of the
        # slack variable (with sign).  We extract from the objective row of
        # non-basic slacks.
        duals: dict[str, Fraction] = {}
        for ci, con in enumerate(problem.constraints):
            cname = con.get("name", f"c{ci}")
            # find slack/surplus/artificial for this constraint
            sname = f"_slack_{ci}"
            aname = f"_art_{ci}"
            surpname = f"_surplus_{ci}"
            # Slack reduced cost = dual y_i (for <=).  For >= the surplus rc
            # gives -y_i.  For = constraints the artificial's rc (in Phase II,
            # 0) doesn't directly give the dual; but after Phase II the dual
            # can be read from the objective row of the artificial (cost 0)
            # as -rc.  We compute y_i = rc of the slack (<=), or -rc of
            # surplus (>=), or rc of artificial (=, sign as appropriate).
            # The objective row stores z = obj_const + sum_j rc_j * x[N[j]].
            # For a <= constraint the slack absorbs unused rhs, so
            #   dz/d(rhs) = y_i = -rc_slack
            # (rc_slack is the negative of the marginal value).  For a >=
            # constraint the surplus variable similarly gives y_i = rc_surplus.
            # For an = constraint the artificial (cost 0) plays the slack role
            # but with coefficient +1 in the row, so y_i = -rc_art.
            y = None
            for j in self.nonbasis:
                v = self.vars[j]
                if v.name == sname:        # <= : slack
                    y = -self.obj_row.get(j, Fraction(0))
                    break
                if v.name == surpname:     # >= : surplus
                    y = self.obj_row.get(j, Fraction(0))
                    break
                if v.name == aname:         # = : artificial
                    y = -self.obj_row.get(j, Fraction(0))
                    break
            else:
                # slack/surplus is basic → constraint is non-binding → y = 0.
                y = Fraction(0)
            # The internal tableau maximises (we flipped min objectives).
            # The dual sign convention above is correct for a max problem.
            # For a min problem we flipped the cost signs, which negates the
            # objective row and therefore negates every reduced cost; the
            # duals derived from those rc's must be negated to match the
            # original min-sense economic interpretation.
            if problem.objective == "min":
                y = -y if y is not None else Fraction(0)
            duals[cname] = y if y is not None else Fraction(0)
        # Reduced costs of structural variables.
        rc_out: dict[str, Fraction] = {}
        for vname in problem.variables:
            idx = self._find_var_index(vname)
            if idx is None:
                rc_out[vname] = Fraction(0)
                continue
            v = self.vars[idx]
            rc = Fraction(0)
            if v.partner is not None:
                # free variable: reduced cost = rc+ - rc-
                rc = self.obj_row.get(idx, Fraction(0)) - self.obj_row.get(v.partner, Fraction(0))
            elif idx in self.nonbasis:
                rc = self.obj_row.get(idx, Fraction(0))
                # if at upper bound, flip sign
                # (heuristic — for non-basic at upper bound the reduced cost
                # stored is for the complemented column; sign may need flip.
                # We leave as-is for the common lower-bound case.)
            # for min problems we flipped costs; reduced costs must be negated.
            if problem.objective == "min":
                rc = -rc
            rc_out[vname] = rc
        basis_names = [self.vars[b].name for b in self.basis]
        return LPResult(
            status=LPStatus.OPTIMAL,
            objective_value=float(obj),
            solution={k: float(val) for k, val in sol.items()},
            duals={k: float(val) for k, val in duals.items()},
            reduced_costs={k: float(val) for k, val in rc_out.items()},
            iterations=0,
            basis=basis_names,
            message="optimal",
        )

    def _find_var_index(self, vname: str) -> int | None:
        """Find the *primary* tableau column for original variable ``vname``."""
        for i, v in enumerate(self.vars):
            if v.name == vname and v.src is not None and not v.name.endswith("_neg") and not v.name.endswith("_flip"):
                return i
        # fallback: name match
        for i, v in enumerate(self.vars):
            if v.name == vname:
                return i
        return None


# ---------------------------------------------------------------------- #
# high-level solver façade
# ---------------------------------------------------------------------- #
@dataclass
class SimplexSolver:
    """High-level LP solver with configurable behaviour."""

    max_iter: int = 10_000
    bland: bool = True
    verbose: bool = False

    def solve(self, problem: LPProblem) -> LPResult:
        """Solve ``problem`` and return an :class:`LPResult`."""
        t = Tableau.from_problem(problem)
        total_pivots = 0
        # Phase I if needed.
        if t.artificial_indices:
            status = t.run_phase_one(max_iter=self.max_iter, bland=self.bland)
            total_pivots += getattr(t, "num_pivots", 0)
            if status is LPStatus.INFEASIBLE:
                return LPResult(status=LPStatus.INFEASIBLE, message="infeasible (Phase I)")
            if status is LPStatus.NUMERICAL:
                return LPResult(status=LPStatus.NUMERICAL, message="Phase I numerical issue")
            if status is LPStatus.TIMEOUT:
                return LPResult(status=LPStatus.TIMEOUT, message="Phase I iteration limit")
        # Phase II.
        status = t.solve(max_iter=self.max_iter, bland=self.bland)
        total_pivots += getattr(t, "num_pivots", 0)
        if status is LPStatus.UNBOUNDED:
            return LPResult(status=LPStatus.UNBOUNDED, message="unbounded objective",
                            iterations=total_pivots)
        if status is LPStatus.TIMEOUT:
            return LPResult(status=LPStatus.TIMEOUT, message="iteration limit reached",
                            iterations=total_pivots)
        res = t.extract_solution(problem)
        res.iterations = total_pivots
        return res