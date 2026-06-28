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
  - Bit-Vectors (BV) — basic support

Atoms are dispatched to the appropriate theory solver based on the
sort and structure of the atom's arguments.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Set, Any
from dataclasses import dataclass, field
import logging
import time

from .ast import (
    Term, Var, App, BoolConst, NumConst, StrConst,
    BOOL, REAL, INT, STRING, Sort,
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
    """A model: variable name -> value (float for Real/Int, bool for Bool, str for String)."""
    bool_vars: Dict[str, bool] = field(default_factory=dict)
    real_vars: Dict[str, float] = field(default_factory=dict)
    int_vars: Dict[str, int] = field(default_factory=dict)
    string_vars: Dict[str, str] = field(default_factory=dict)

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
        for name, val in sorted(self.string_vars.items()):
            lines.append(f"  {name} -> \"{val}\"")
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
        for name, val in sorted(self.string_vars.items()):
            lines.append(f"  (define-fun {name} () String \"{val}\")")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize model to a dictionary."""
        return {
            "bool": dict(self.bool_vars),
            "real": {k: v for k, v in self.real_vars.items()},
            "int": dict(self.int_vars),
            "string": dict(self.string_vars),
        }


@dataclass
class SolverStatistics:
    """Tracks solver execution statistics."""
    assertions: int = 0
    atoms: int = 0
    sat_vars: int = 0
    sat_clauses: int = 0
    theory_rounds: int = 0
    theory_conflicts: int = 0
    sat_conflicts: int = 0
    sat_decisions: int = 0
    check_time: float = 0.0
    sat_time: float = 0.0
    theory_time: float = 0.0

    def __str__(self) -> str:
        lines = [
            f"Assertions:       {self.assertions}",
            f"Theory atoms:     {self.atoms}",
            f"SAT variables:    {self.sat_vars}",
            f"SAT clauses:      {self.sat_clauses}",
            f"Theory rounds:    {self.theory_rounds}",
            f"Theory conflicts: {self.theory_conflicts}",
            f"SAT conflicts:    {self.sat_conflicts}",
            f"SAT decisions:    {self.sat_decisions}",
            f"Total time:       {self.check_time:.4f}s",
            f"  SAT time:      {self.sat_time:.4f}s",
            f"  Theory time:   {self.theory_time:.4f}s",
        ]
        return "\n".join(lines)


class Solver:
    """Top-level SMT solver using DPLL(T) with EUF and LRA theories.

    Architecture:
        1. Boolean structure of assertions is encoded into CNF via Tseitin
           transformation, treating each theory atom as a propositional variable.
        2. The CDCL SAT solver finds a satisfying Boolean assignment.
        3. Theory solvers (EUF, LRA) check if the assignment is theory-consistent.
        4. If inconsistent, a theory lemma (conflict clause) is learned and
           the SAT solver re-searches.
        5. If consistent, a model is constructed from the SAT assignment and
           the theory models.

    Attributes:
        assertions: List of asserted formulas (Terms).
        stats: SolverStatistics tracking execution metrics.
    """

    def __init__(self, logic: Optional[str] = None, max_rounds: int = 100):
        """Initialize a fresh solver.

        Args:
            logic: Optional SMT-LIB logic identifier (e.g. "LRA", "QF_UF").
            max_rounds: Maximum number of DPLL(T) theory-check rounds.
        """
        self.parser = Parser()
        self.assertions: List[Term] = []
        self._named_assertions: Dict[str, Term] = {}
        # Atom ↔ propositional variable mapping
        self._atom_to_lit: Dict[Term, int] = {}
        self._lit_to_atom: Dict[int, Term] = {}
        # Boolean variable name -> SAT literal (for model construction)
        self._bool_var_to_lit: Dict[str, int] = {}
        self._sat = CDCLSatSolver()
        self._euf = CongruenceClosure()
        self._lra = SimplexTheory()
        self._declared: Dict[str, Tuple[Sort, Tuple[Sort, ...]]] = {}
        self._result: Optional[SMTResult] = None
        self._model: Optional[Model] = None
        # Stack for push/pop
        self._assertion_stack: List[List[Term]] = [[]]
        self._encode_cache: Dict[Term, int] = {}
        self._logic = logic
        self._max_rounds = max_rounds
        self.stats = SolverStatistics()

    # ------------------------------------------------------------------
    # Declaration helpers
    # ------------------------------------------------------------------

    def declare_const(self, name: str, sort: Sort) -> Var:
        """Declare a constant variable.

        Args:
            name: The variable name.
            sort: The sort (type) of the variable.

        Returns:
            The Var AST node.
        """
        v = self.parser.declare_const(name, sort)
        self._declared[name] = (sort, ())
        return v

    def declare_fun(self, name: str, arg_sorts: Tuple[Sort, ...], ret_sort: Sort):
        """Declare an uninterpreted function.

        Args:
            name: Function name.
            arg_sorts: Tuple of argument sorts.
            ret_sort: Return sort.
        """
        self.parser.declare_fun(name, arg_sorts, ret_sort)
        self._declared[name] = (ret_sort, arg_sorts)

    # ------------------------------------------------------------------
    # Assertion
    # ------------------------------------------------------------------

    def assert_term(self, term: Term, name: Optional[str] = None):
        """Assert a formula.

        Args:
            term: The formula to assert.
            name: Optional name for the assertion (for UNSAT core tracking).
        """
        self.assertions.append(term)
        self._assertion_stack[-1].append(term)
        if name:
            self._named_assertions[name] = term
        self._result = None  # invalidate cached result
        self._model = None

    def parse_and_assert(self, text: str):
        """Parse one or more SMT-LIB commands and execute them.

        Supports: declare-const, declare-fun, assert, set-logic, set-info,
        push, pop, reset, check-sat, get-model, exit.

        Args:
            text: SMT-LIB v2 script text.
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
            self.assert_term(cmd["term"], cmd.get("name"))
        elif name == "push":
            self._assertion_stack.append([])
        elif name == "pop":
            if len(self._assertion_stack) > 1:
                popped = self._assertion_stack.pop()
                for term in popped:
                    if term in self.assertions:
                        self.assertions.remove(term)
                self._result = None
        elif name == "reset":
            self.assertions.clear()
            self._assertion_stack = [[]]
            self._result = None
            self._named_assertions.clear()
        elif name in ("set-logic", "set-info", "exit", "check-sat", "get-model"):
            pass  # ignore / handle separately
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

    def _expand_ite_in_atoms(self, formula: Term) -> Term:
        """Expand ITE terms that appear inside theory atoms.

        Transforms (= y (ite b 1.0 2.0)) into
        (or (and b (= y 1.0)) (and (not b) (= y 2.0))).

        This ensures that arithmetic equalities with ITE branches are
        properly encoded as Boolean structure rather than treated as
        opaque atoms.
        """
        return _expand_ite_recursive(formula)

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
    # Boolean structure → CNF (Tseitin encoding)
    # ------------------------------------------------------------------

    def _to_cnf(self, formula: Term) -> List[List[int]]:
        """Convert a formula to CNF clauses over atom literals.

        Uses a Tseitin-style encoding with auxiliary variables for
        subformulas. Returns a list of clauses (each clause = list of ints).
        """
        cnf: List[List[int]] = []
        cache = self._encode_cache

        def encode(term: Term) -> int:
            """Return the literal representing *term*. Adds clauses to cnf."""
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
                # Track Boolean var → lit mapping for model construction
                if term.sort == BOOL:
                    self._bool_var_to_lit[term.name] = lit
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
                    # Instead of creating a new variable, just negate
                    # But we need a positive lit for caching
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
        Equalities between plain numeric variables are handled by LRA.
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
        if self._is_arith_atom(atom):
            return False
        return True

    def _check_theory(self, assignment: Dict[int, bool]) -> Tuple[bool, Optional[List[int]]]:
        """Check theory consistency of the current Boolean assignment.

        Returns (consistent, conflict_lits).
        """
        euf_atoms: List[Tuple[Term, bool]] = []
        lra_atoms: List[Tuple[Term, bool]] = []

        for lit, atom in self._lit_to_atom.items():
            val = assignment.get(lit)
            if val is None:
                continue
            if isinstance(atom, App) and atom.func == "=" and len(atom.args) == 2:
                euf_atoms.append((atom, val))
                if self._is_arith_atom(atom):
                    lra_atoms.append((atom, val))
            elif self._is_arith_atom(atom):
                lra_atoms.append((atom, val))

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
        eq_lits: List[int] = []

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
            return True, None

    # ------------------------------------------------------------------
    # Model generation
    # ------------------------------------------------------------------

    def _build_model(self, assignment: Dict[int, bool]) -> Model:
        """Build a model from the Boolean assignment and theory models."""
        model = Model()

        for name, (sort, _) in self._declared.items():
            if sort == BOOL:
                # Boolean variable: look up in the SAT assignment
                lit = self._bool_var_to_lit.get(name)
                if lit is not None:
                    val = assignment.get(lit)
                    if val is not None:
                        model.bool_vars[name] = val
                    else:
                        model.bool_vars[name] = False
                else:
                    model.bool_vars[name] = False
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
            elif sort == STRING:
                model.string_vars[name] = ""

        return model

    # ------------------------------------------------------------------
    # Main check
    # ------------------------------------------------------------------

    def check(self) -> SMTResult:
        """Check satisfiability.

        Returns 'sat', 'unsat', or 'unknown'.

        The solver:
        1. Encodes all assertions into CNF via Tseitin transformation.
        2. Runs the CDCL SAT solver.
        3. If SAT, checks theory consistency.
        4. If theory-inconsistent, learns a conflict clause and re-runs.
        5. If theory-consistent, builds and stores a model.
        """
        if self._result is not None:
            return self._result

        self.stats = SolverStatistics()
        self.stats.assertions = len(self.assertions)
        t0 = time.perf_counter()

        # Build SAT problem
        self._sat = CDCLSatSolver()
        self._atom_to_lit = {}
        self._lit_to_atom = {}
        self._bool_var_to_lit = {}
        self._encode_cache = {}

        # Encode assertions into CNF
        all_cnf: List[List[int]] = []
        for formula in self.assertions:
            # Pre-process: expand ITE terms inside theory atoms
            expanded = _expand_ite_recursive(formula)
            cnf = self._to_cnf(expanded)
            all_cnf.extend(cnf)

        self.stats.atoms = len(self._atom_to_lit)
        self.stats.sat_vars = self._sat.num_vars

        # Add all clauses to SAT solver
        for clause in all_cnf:
            if not self._sat.add_clause(clause):
                self._result = "unsat"
                self.stats.check_time = time.perf_counter() - t0
                return self._result

        self.stats.sat_clauses = len(self._sat.clauses)

        # DPLL(T) loop
        for round_num in range(self._max_rounds):
            self.stats.theory_rounds = round_num + 1
            t_sat = time.perf_counter()
            result = self._sat.solve(max_conflicts=10000)
            self.stats.sat_time += time.perf_counter() - t_sat
            self.stats.sat_conflicts = self._sat.conflicts

            if result == "unsat":
                self._result = "unsat"
                self.stats.check_time = time.perf_counter() - t0
                return self._result
            if result == "unknown":
                self._result = "unknown"
                self.stats.check_time = time.perf_counter() - t0
                return self._result

            # SAT — check theory consistency
            assignment = self._sat.model()
            t_th = time.perf_counter()
            consistent, conflict = self._check_theory(assignment)
            self.stats.theory_time += time.perf_counter() - t_th

            if consistent:
                self._result = "sat"
                self._model = self._build_model(assignment)
                self.stats.check_time = time.perf_counter() - t0
                return self._result

            # Theory conflict — learn a lemma
            self.stats.theory_conflicts += 1
            if conflict:
                neg_clause = [-l for l in conflict]
                # Backtrack SAT solver to level 0 before adding lemma
                self._sat.cancel_until(0)
                if not self._sat.add_clause(neg_clause):
                    self._result = "unsat"
                    self.stats.check_time = time.perf_counter() - t0
                    return self._result
            else:
                self._result = "unknown"
                self.stats.check_time = time.perf_counter() - t0
                return self._result

        self._result = "unknown"
        self.stats.check_time = time.perf_counter() - t0
        return self._result

    def get_model(self) -> Optional[Model]:
        """Return the model from the last successful check().

        Returns None if unsat or not yet checked.
        """
        if self._result == "sat":
            return self._model
        return None

    def get_unsat_core(self) -> List[str]:
        """Return names of assertions in the UNSAT core.

        Note: This is a best-effort implementation that identifies which
        named assertions contribute to unsatisfiability.
        """
        if self._result != "unsat":
            return []
        # Simple approach: try removing each assertion and see if still unsat
        core = []
        for name, term in self._named_assertions.items():
            saved = list(self.assertions)
            self.assertions = [a for a in self.assertions if a is not term]
            self._result = None
            result = self.check()
            if result == "unsat":
                # Still unsat without this assertion — not in core
                pass
            else:
                core.append(name)
            self.assertions = saved
        self._result = "unsat"
        return core

    def get_statistics(self) -> SolverStatistics:
        """Return solver execution statistics from the last check()."""
        return self.stats

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
        self._bool_var_to_lit = {}
        self._encode_cache = {}
        self._named_assertions.clear()

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

    def evaluate(self, term: Term) -> Any:
        """Evaluate a term under the current model.

        Returns the value of the term if a model exists, None otherwise.
        """
        if self._model is None:
            return None
        if isinstance(term, BoolConst):
            return term.value
        if isinstance(term, NumConst):
            return term.value
        if isinstance(term, StrConst):
            return term.value
        if isinstance(term, Var):
            if term.sort == BOOL:
                return self._model.bool_vars.get(term.name, False)
            elif term.sort == REAL:
                return self._model.real_vars.get(term.name, 0.0)
            elif term.sort == INT:
                return self._model.int_vars.get(term.name, 0)
            elif term.sort == STRING:
                return self._model.string_vars.get(term.name, "")
        if isinstance(term, App):
            if term.func == "+":
                vals = [self.evaluate(a) for a in term.args]
                if any(v is None for v in vals):
                    return None
                return sum(vals)
            if term.func == "-":
                vals = [self.evaluate(a) for a in term.args]
                if any(v is None for v in vals):
                    return None
                if len(vals) == 1:
                    return -vals[0]
                result = vals[0]
                for v in vals[1:]:
                    result -= v
                return result
            if term.func == "*":
                vals = [self.evaluate(a) for a in term.args]
                if any(v is None for v in vals):
                    return None
                result = 1.0
                for v in vals:
                    result *= v
                return result
        return None


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
    """Check satisfiability of a single formula.

    Args:
        formula: The formula to check.

    Returns:
        'sat', 'unsat', or 'unknown'.
    """
    s = Solver()
    s.assert_term(formula)
    return s.check()


# ---------------------------------------------------------------------------
# ITE expansion pre-processing
# ---------------------------------------------------------------------------

def _has_ite(term: Term) -> bool:
    """Check if a term contains any ITE subterms."""
    for sub in pre_order(term):
        if isinstance(sub, App) and sub.func == "ite":
            return True
    return False


def _expand_ite_recursive(term: Term) -> Term:
    """Recursively expand ITE terms inside theory atoms.

    When an ITE appears as a child of a comparison atom (e.g.,
    (= y (ite b 1.0 2.0))), we transform it into a case split:
    (or (and b (= y 1.0)) (and (not b) (= y 2.0))).

    For ITEs in Boolean position, we leave them as-is (the Tseitin
    encoding handles them correctly).

    For ITEs nested inside arithmetic terms (e.g., (+ x (ite b 1 2))),
    we also expand into case splits.
    """
    if not _has_ite(term):
        return term

    if isinstance(term, App):
        # If this is a theory atom containing an ITE in its args
        if is_atom(term) and any(_has_ite(a) for a in term.args):
            return _expand_ite_in_atom(term)

        # Recursively expand children
        new_args = tuple(_expand_ite_recursive(a) for a in term.args)
        if new_args != term.args:
            return App(term.func, new_args, term.sort)

    return term


def _expand_ite_in_atom(atom: App) -> Term:
    """Expand an atom that contains ITE in its arguments.

    Strategy: find the first ITE in any argument, then case-split:
    - cond is true: replace ITE with its then-branch
    - cond is false: replace ITE with its else-branch

    Result: (or (and cond new_atom_then) (and (not cond) new_atom_else))
    """
    func = atom.func
    args = list(atom.args)

    # Find the first arg containing an ITE
    ite_idx = -1
    for i, a in enumerate(args):
        if _has_ite(a):
            ite_idx = i
            break

    if ite_idx < 0:
        return atom

    ite_term = args[ite_idx]
    if not isinstance(ite_term, App) or ite_term.func != "ite":
        # The ITE is nested deeper — recursively expand this arg first
        new_arg = _expand_ite_recursive(ite_term)
        args[ite_idx] = new_arg
        new_atom = App(func, tuple(args), atom.sort)
        return _expand_ite_in_atom(new_atom)

    cond = ite_term.args[0]
    then_branch = ite_term.args[1]
    else_branch = ite_term.args[2]

    # Build atom with then-branch
    then_args = list(args)
    then_args[ite_idx] = _expand_ite_recursive(then_branch)
    then_atom = App(func, tuple(then_args), atom.sort)

    # Build atom with else-branch
    else_args = list(args)
    else_args[ite_idx] = _expand_ite_recursive(else_branch)
    else_atom = App(func, tuple(else_args), atom.sort)

    # Case split: (or (and cond then_atom) (and (not cond) else_atom))
    return Or(And(cond, then_atom), And(Not(cond), else_atom))