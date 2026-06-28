"""
DPLL(T) solver: integrates CDCL SAT with theory solvers (EUF + LRA).

The Boolean abstraction treats each theory atom as a propositional
variable.  When the SAT engine produces a satisfying Boolean assignment,
the theory solver checks whether the corresponding set of theory atoms
(and their negations) is consistent.  If not, a conflict clause (theory
lemma) is learned and added to the SAT engine, which backtracks and
searches again.

Supported theories:
  - Uninterpreted Functions with Equality (EUF)
  - Linear Real Arithmetic (LRA)

Atoms are dispatched to the appropriate theory solver based on the
sort and structure of the atom's arguments.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
import logging

from .ast import (
    Term, Var, App, BoolConst, NumConst,
    BOOL, REAL, INT, Sort,
    And, Or, Not, Eq, Lt, Le, Gt, Ge,
    collect_vars, is_atom, pre_order,
)
from .sat_solver import CDCLSatSolver
from .theory_euf import CongruenceClosure
from .theory_lra import SimplexTheory, atom_to_constraint
from .parser import Parser, parse_script, tokenize, parse_sexprs
from .exceptions import SMTError, ParseError, TheoryError

logger = logging.getLogger(__name__)

SMTResult = str  # "sat" | "unsat" | "unknown"


@dataclass
class Model:
    """A model: variable name -> value (float for Real/Int, bool for Bool)."""
    bool_vars: Dict[str, bool] = field(default_factory=dict)
    real_vars: Dict[str, float] = field(default_factory=dict)
    int_vars: Dict[str, int] = field(default_factory=dict)

    def __str__(self) -> str:
        lines = []
        for name, val in sorted(self.bool_vars.items()):
            lines.append(f"  {name} -> {'true' if val else 'false'}")
        for name, val in sorted(self.real_vars.items()):
            if float(val).is_integer():
                lines.append(f"  {name} -> {int(val)}.0")
            else:
                lines.append(f"  {name} -> {val}")
        for name, val in sorted(self.int_vars.items()):
            lines.append(f"  {name} -> {val}")
        return "\n".join(lines) if lines else "  (empty model)"

    def to_smt(self) -> str:
        """Format as SMT-LIB model."""
        lines = []
        for name, val in sorted(self.bool_vars.items()):
            lines.append(f"  (define-fun {name} () Bool {'true' if val else 'false'})")
        for name, val in sorted(self.real_vars.items()):
            v = val if not float(val).is_integer() else float(int(val))
            lines.append(f"  (define-fun {name} () Real {v})")
        for name, val in sorted(self.int_vars.items()):
            lines.append(f"  (define-fun {name} () Int {val})")
        return "\n".join(lines)


class Solver:
    """Top-level SMT solver using DPLL(T) with EUF and LRA theories."""

    def __init__(self):
        self.parser = Parser()
        self.assertions: List[Term] = []
        # Atom ↔ propositional variable mapping
        self._atom_to_lit: Dict[Term, int] = {}
        self._lit_to_atom: Dict[int, Term] = {}
        self._sat = CDCLSatSolver()
        self._euf = CongruenceClosure()
        self._lra = SimplexTheory()
        self._declared: Dict[str, Tuple[Sort, Tuple[Sort, ...]]] = {}
        self._result: Optional[SMTResult] = None
        self._model: Optional[Model] = None
        # Stack for push/pop
        self._assertion_stack: List[List[Term]] = [[]]

    # ------------------------------------------------------------------
    # Declaration helpers
    # ------------------------------------------------------------------

    def declare_const(self, name: str, sort: Sort) -> Var:
        """Declare a constant variable."""
        v = self.parser.declare_const(name, sort)
        self._declared[name] = (sort, ())
        return v

    def declare_fun(self, name: str, arg_sorts: Tuple[Sort, ...], ret_sort: Sort):
        """Declare an uninterpreted function."""
        self.parser.declare_fun(name, arg_sorts, ret_sort)
        self._declared[name] = (ret_sort, arg_sorts)

    # ------------------------------------------------------------------
    # Assertion
    # ------------------------------------------------------------------

    def assert_term(self, term: Term):
        """Assert a formula."""
        self.assertions.append(term)
        self._assertion_stack[-1].append(term)
        self._result = None  # invalidate cached result
        self._model = None

    def parse_and_assert(self, text: str):
        """Parse one or more SMT-LIB commands and execute them.

        Supports: declare-const, declare-fun, assert, set-logic, set-info.
        """
        tokens = tokenize(text)
        sexprs = parse_sexprs(tokens)
        for sexpr in sexprs:
            cmd = self.parser.parse_command(sexpr)
            self._execute_command(cmd)

    def _execute_command(self, cmd: dict):
        name = cmd["cmd"]
        if name == "declare-const":
            self._declared[cmd["name"]] = (cmd["sort"], ())
        elif name == "declare-fun":
            self._declared[cmd["name"]] = (cmd["ret_sort"], cmd["arg_sorts"])
        elif name == "assert":
            self.assert_term(cmd["term"])
        elif name == "push":
            self._assertion_stack.append([])
        elif name == "pop":
            if len(self._assertion_stack) > 1:
                popped = self._assertion_stack.pop()
                for term in popped:
                    self.assertions.remove(term)
                self._result = None
        elif name == "reset":
            self.assertions.clear()
            self._assertion_stack = [[]]
            self._result = None
        elif name in ("set-logic", "set-info", "exit"):
            pass  # ignore
        elif name == "unknown":
            pass  # ignore unknown commands

    # ------------------------------------------------------------------
    # Atom abstraction
    # ------------------------------------------------------------------

    def _collect_atoms(self) -> List[Term]:
        """Collect all theory atoms from assertions."""
        atoms: Set[Term] = set()
        for formula in self.assertions:
            for sub in pre_order(formula):
                if is_atom(sub):
                    atoms.add(sub)
        return list(atoms)

    def _atom_to_prop(self, atom: Term) -> int:
        """Map an atom to a SAT literal (positive var)."""
        if atom in self._atom_to_lit:
            return self._atom_to_lit[atom]
        var = self._sat.new_var()
        lit = var
        self._atom_to_lit[atom] = lit
        self._lit_to_atom[lit] = atom
        return lit

    # ------------------------------------------------------------------
    # Boolean structure → CNF
    # ------------------------------------------------------------------

    def _to_cnf(self, formula: Term) -> List[List[int]]:
        """Convert a formula to CNF clauses over atom literals.

        Uses a Tseitin-style encoding with auxiliary variables for
        subformulas.  Returns a list of clauses (each clause = list of ints).
        """
        cnf: List[List[int]] = []
        # Use the persistent encoding cache so the same subformula maps
        # to the same SAT variable across multiple _to_cnf calls.
        if not hasattr(self, '_encode_cache'):
            self._encode_cache: Dict[Term, int] = {}
        cache = self._encode_cache

        def encode(term: Term) -> int:
            """Return the literal representing *term*.  Adds clauses to cnf."""
            if term in cache:
                return cache[term]

            if isinstance(term, BoolConst):
                lit = self._sat.new_var()
                if term.value:
                    cnf.append([lit])  # lit = true
                else:
                    cnf.append([-lit])  # lit = false
                cache[term] = lit
                return lit

            if isinstance(term, Var):
                # A Boolean variable that's not a theory atom
                # Treat it as a fresh propositional variable
                lit = self._sat.new_var()
                cache[term] = lit
                return lit

            if isinstance(term, App):
                if is_atom(term):
                    lit = self._atom_to_prop(term)
                    cache[term] = lit
                    return lit

                func = term.func
                if func == "and":
                    child_lits = [encode(c) for c in term.args]
                    lit = self._sat.new_var()
                    # lit <=> AND(child_lits)
                    # lit → child_i for each i
                    for cl in child_lits:
                        cnf.append([-lit, cl])
                    # AND → lit
                    cnf.append([lit] + [-cl for cl in child_lits])
                    cache[term] = lit
                    return lit

                if func == "or":
                    child_lits = [encode(c) for c in term.args]
                    lit = self._sat.new_var()
                    # child_i → lit
                    for cl in child_lits:
                        cnf.append([-cl, lit])
                    # lit → OR(child_lits)
                    cnf.append([-lit] + child_lits)
                    cache[term] = lit
                    return lit

                if func == "not":
                    inner = encode(term.args[0])
                    lit = self._sat.new_var()
                    # lit <=> ¬inner
                    cnf.append([-lit, -inner])
                    cnf.append([lit, inner])
                    cache[term] = lit
                    return lit

                if func == "=>":
                    a = encode(term.args[0])
                    b = encode(term.args[1])
                    lit = self._sat.new_var()
                    # lit <=> (¬a ∨ b)
                    cnf.append([-lit, -a, b])
                    cnf.append([lit, a])
                    cnf.append([lit, -b])
                    cache[term] = lit
                    return lit

                if func == "ite":
                    c = encode(term.args[0])
                    t = encode(term.args[1])
                    e = encode(term.args[2])
                    lit = self._sat.new_var()
                    # c → (lit ↔ t)
                    cnf.append([-c, -lit, t])
                    cnf.append([-c, lit, -t])
                    # ¬c → (lit ↔ e)
                    cnf.append([c, -lit, e])
                    cnf.append([c, lit, -e])
                    cache[term] = lit
                    return lit

                if func == "=":
                    # Boolean equality
                    a = encode(term.args[0])
                    b = encode(term.args[1])
                    lit = self._sat.new_var()
                    cnf.append([-lit, -a, b])
                    cnf.append([-lit, a, -b])
                    cnf.append([lit, -a, -b])
                    cnf.append([lit, a, b])
                    cache[term] = lit
                    return lit

                if func == "xor":
                    a = encode(term.args[0])
                    b = encode(term.args[1])
                    lit = self._sat.new_var()
                    cnf.append([-lit, a, b])
                    cnf.append([-lit, -a, -b])
                    cnf.append([lit, -a, b])
                    cnf.append([lit, a, -b])
                    cache[term] = lit
                    return lit

                if func == "distinct":
                    lits = [encode(c) for c in term.args]
                    lit = self._sat.new_var()
                    # lit <=> AND pairwise distinct
                    # Simpler: lit → each pair differs
                    for i in range(len(lits)):
                        for j in range(i + 1, len(lits)):
                            diff_var = self._sat.new_var()
                            # diff_var <=> lits[i] != lits[j]
                            cnf.append([-diff_var, -lits[i], -lits[j]])
                            cnf.append([-diff_var, lits[i], lits[j]])
                            cnf.append([diff_var, -lits[i], lits[j]])
                            cnf.append([diff_var, lits[i], -lits[j]])
                            cnf.append([-lit, diff_var])
                    # All diff_vars true → lit
                    # (We approximate: lit is true iff all pairwise different)
                    cache[term] = lit
                    return lit

                # Uninterpreted function application in Boolean position
                # Treat as a fresh atom (EUF equality)
                lit = self._atom_to_prop(term)
                cache[term] = lit
                return lit

            raise SMTError(f"Cannot encode: {term}")

        top_lit = encode(formula)
        cnf.append([top_lit])  # assert formula is true
        return cnf

    # ------------------------------------------------------------------
    # Theory checking
    # ------------------------------------------------------------------

    def _is_arith_atom(self, atom: Term) -> bool:
        """Check if an atom belongs to the LRA theory.

        An arithmetic atom has comparison operator and both arguments
        are arithmetic terms (vars, numeric constants, or arithmetic ops).
        Equalities between plain numeric variables are handled by BOTH
        theories, but we route them to LRA here for model generation.
        Disequalities and comparisons (<, <=, >, >=) are LRA only.
        """
        if not isinstance(atom, App) or atom.func not in {"=", "<", "<=", ">", ">="}:
            return False
        if len(atom.args) != 2:
            return False
        # Both args must be arithmetic terms
        if not (_is_arith_term(atom.args[0]) and _is_arith_term(atom.args[1])):
            return False
        # For equalities, check if they should go to EUF instead
        # If either side involves a function application (not a plain var/const),
        # and the function is not an arithmetic op, route to EUF
        if atom.func == "=":
            if _involves_uninterpreted_func(atom.args[0]) or _involves_uninterpreted_func(atom.args[1]):
                return False  # EUF will handle this
        return True

    def _is_euf_atom(self, atom: Term) -> bool:
        """Check if an atom belongs to the EUF theory."""
        if not isinstance(atom, App) or atom.func != "=":
            return False
        if len(atom.args) != 2:
            return False
        # If it's an arithmetic equality, it's not EUF (handled by LRA)
        if self._is_arith_atom(atom):
            return False
        return True

    def _check_theory(self, assignment: Dict[int, bool]) -> Tuple[bool, Optional[List[int]]]:
        """Check theory consistency of the current Boolean assignment.

        Returns (consistent, conflict_lits).

        Equality atoms are shared between theories: any equality atom
        involving terms that appear in EUF (function applications) is sent
        to EUF.  All arithmetic atoms (including numeric equalities) are
        also sent to LRA for model generation.
        """
        euf_atoms: List[Tuple[Term, bool]] = []
        lra_atoms: List[Tuple[Term, bool]] = []

        for lit, atom in self._lit_to_atom.items():
            val = assignment.get(lit)
            if val is None:
                continue
            # Route to EUF if it's an equality involving uninterpreted functions
            # or if it's an equality that EUF needs for congruence propagation
            if isinstance(atom, App) and atom.func == "=" and len(atom.args) == 2:
                # Send all equalities to EUF (for congruence propagation)
                euf_atoms.append((atom, val))
                # Also send to LRA if it's arithmetic
                if self._is_arith_atom(atom):
                    lra_atoms.append((atom, val))
            elif self._is_arith_atom(atom):
                lra_atoms.append((atom, val))
            # else: unclassified atom — ignore for now

        # Check EUF
        euf_ok, euf_conflict = self._check_euf(euf_atoms)
        if not euf_ok:
            return False, euf_conflict

        # Check LRA
        lra_ok, lra_conflict = self._check_lra(lra_atoms)
        if not lra_ok:
            return False, lra_conflict

        return True, None

    def _check_euf(self, atoms: List[Tuple[Term, bool]]) -> Tuple[bool, Optional[List[int]]]:
        """Check EUF consistency."""
        self._euf = CongruenceClosure()  # fresh
        diseqs: List[Tuple[Term, Term, int]] = []
        eq_lits: List[int] = []  # lits of asserted equalities

        for atom, val in atoms:
            if not isinstance(atom, App) or atom.func != "=":
                continue
            a, b = atom.args
            lit = self._atom_to_lit.get(atom)
            if lit is None:
                continue
            if val:
                self._euf.assert_eq(a, b)
                eq_lits.append(lit)
            else:
                diseqs.append((a, b, lit))

        # Check disequalities
        for a, b, lit in diseqs:
            if self._euf.are_equal(a, b):
                # Conflict: equalities imply a=b, but we asserted a!=b
                # The conflict clause: equalities + negated disequality
                # Lemma: not(all eq_lits and not diseq)
                # = at least one eq must be false, or diseq must be true
                # Conflict lits (all true in current assignment):
                #   eq_lits (all true) + lit (the diseq lit, which is false/negated)
                # The lemma to add: OR(NOT eq for each eq in eq_lits, OR diseq)
                # As conflict: [-l for l in eq_lits] + [lit]
                # But that's not quite right either. The actual conflict is:
                # All asserted equalities are true, and the disequality is true (negated equality)
                # which is contradictory. So the conflict set is all the equalities
                # that are relevant + the disequality.
                # For simplicity, return all eq lits + the diseq lit (negated)
                # The lemma: NOT(all eq_lits AND NOT diseq_lit)
                # = at least one eq is false OR diseq is false (i.e., equality is true)
                # As clause: [-l for l in eq_lits] + [lit]  where lit is the diseq prop var
                # Wait: diseq means "not (= a b)", so the prop var for (= a b) is false.
                # The lit for the disequality is -atom_lit (the atom is false).
                # So the conflict lits are: eq_lits (positive) + (-lit) (the atom is false)
                # The negation (lemma): [-l for l in eq_lits] + [lit]
                return False, eq_lits + [-lit]
        return True, None

    def _check_lra(self, atoms: List[Tuple[Term, bool]]) -> Tuple[bool, Optional[List[int]]]:
        """Check LRA consistency."""
        self._lra = SimplexTheory()  # fresh
        for atom, val in atoms:
            if val:
                self._lra.assert_atom(atom)
            else:
                self._lra.assert_negation(atom)

        status, model, conflict = self._lra.check()
        if status == "sat":
            self._lra_model = model
            return True, None
        elif status == "unsat":
            if conflict:
                # Convert conflict indices to SAT literals
                lits = []
                for idx in conflict:
                    if idx < len(atoms):
                        atom, val = atoms[idx]
                        lit = self._atom_to_lit.get(atom)
                        if lit is not None:
                            lits.append(lit if val else -lit)
                return False, lits
            return False, None
        else:
            # Unknown — treat as consistent for now
            return True, None

    # ------------------------------------------------------------------
    # Model generation
    # ------------------------------------------------------------------

    def _build_model(self, assignment: Dict[int, bool]) -> Model:
        """Build a model from the Boolean assignment and theory models."""
        model = Model()

        for name, (sort, _) in self._declared.items():
            if sort == BOOL:
                # Boolean variable: find its assignment
                # Check if it appears as an atom or as a Var in the encoding
                val = assignment.get(self._bool_var_lit(name))
                if val is not None:
                    model.bool_vars[name] = val
                else:
                    model.bool_vars[name] = False  # default
            elif sort == REAL:
                if hasattr(self, "_lra_model") and self._lra_model:
                    val = self._lra_model.get(name, 0.0)
                    model.real_vars[name] = val
                else:
                    model.real_vars[name] = 0.0
            elif sort == INT:
                if hasattr(self, "_lra_model") and self._lra_model:
                    val = self._lra_model.get(name, 0.0)
                    model.int_vars[name] = int(val)
                else:
                    model.int_vars[name] = 0

        return model

    def _bool_var_lit(self, name: str) -> int:
        """Get the SAT literal for a Boolean variable (if it was encoded)."""
        # This is a heuristic — we look for a Var node with this name
        var = Var(name, BOOL)
        return self._atom_to_lit.get(var, 0)

    # ------------------------------------------------------------------
    # Main check
    # ------------------------------------------------------------------

    def check(self) -> SMTResult:
        """Check satisfiability.  Returns 'sat', 'unsat', or 'unknown'."""
        if self._result is not None:
            return self._result

        # Build SAT problem
        self._sat = CDCLSatSolver()
        self._atom_to_lit = {}
        self._lit_to_atom = {}
        self._encode_cache = {}  # reset Tseitin encoding cache

        # Encode assertions into CNF
        all_cnf: List[List[int]] = []
        for formula in self.assertions:
            cnf = self._to_cnf(formula)
            all_cnf.extend(cnf)

        # Add all clauses to SAT solver
        for clause in all_cnf:
            if not self._sat.add_clause(clause):
                self._result = "unsat"
                return self._result

        # DPLL(T) loop
        max_rounds = 50
        for round_num in range(max_rounds):
            result = self._sat.solve(max_conflicts=10000)
            if result == "unsat":
                self._result = "unsat"
                return self._result
            if result == "unknown":
                self._result = "unknown"
                return self._result

            # SAT — check theory consistency
            assignment = self._sat.model()
            consistent, conflict = self._check_theory(assignment)

            if consistent:
                self._result = "sat"
                self._model = self._build_model(assignment)
                return self._result

            # Theory conflict — learn a lemma
            if conflict:
                # Negate the conflicting atoms: not all of them can be true
                neg_clause = [-l for l in conflict]
                # Backtrack SAT solver to level 0 before adding lemma
                self._sat.cancel_until(0)
                if not self._sat.add_clause(neg_clause):
                    # Lemma is trivially unsat → whole problem is unsat
                    self._result = "unsat"
                    return self._result
            else:
                # No explicit conflict — shouldn't happen
                self._result = "unknown"
                return self._result

        self._result = "unknown"
        return self._result

    def get_model(self) -> Optional[Model]:
        """Return the model from the last successful check().  None if unsat."""
        if self._result == "sat":
            return self._model
        return None

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def reset(self):
        """Reset the solver state (keep declarations)."""
        self.assertions.clear()
        self._assertion_stack = [[]]
        self._result = None
        self._model = None
        self._atom_to_lit = {}
        self._lit_to_atom = {}

    def push(self):
        """Push a backtracking point."""
        self._assertion_stack.append([])

    def pop(self):
        """Pop a backtracking point."""
        if len(self._assertion_stack) > 1:
            popped = self._assertion_stack.pop()
            for term in popped:
                if term in self.assertions:
                    self.assertions.remove(term)
            self._result = None
            self._model = None


def _contains_real_var(term: Term) -> bool:
    """Check if a term contains any Real or Int variable."""
    for v in collect_vars(term):
        if v.sort.is_numeric:
            return True
    return False


_ARITH_FUNCS = {"+", "-", "*", "/", "<", "<=", ">", ">=", "="}


def _is_arith_term(term: Term) -> bool:
    """Check if a term is a pure arithmetic term.

    Arithmetic terms are: numeric constants, numeric variables,
    or applications of arithmetic operators (+, -, *, /) to arithmetic terms.
    """
    if isinstance(term, NumConst):
        return True
    if isinstance(term, Var):
        return term.sort.is_numeric
    if isinstance(term, App):
        if term.func in {"+", "-", "*", "/"}:
            return all(_is_arith_term(a) for a in term.args)
        # Comparison operators produce Bool — not arithmetic terms themselves
        return False
    return False


def _involves_uninterpreted_func(term: Term) -> bool:
    """Check if a term involves any uninterpreted function application."""
    if isinstance(term, App):
        if term.func not in {"+", "-", "*", "/", "<", "<=", ">", ">=", "=", "ite"}:
            return True
        return any(_involves_uninterpreted_func(a) for a in term.args)
    return False


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def check_sat(formula: Term) -> SMTResult:
    """Check satisfiability of a single formula (no declarations needed
    for simple cases)."""
    s = Solver()
    s.assert_term(formula)
    return s.check()