"""Prolog inference engine with backtracking search and predicate indexing.

This is the core solver implementing depth-first SLD resolution with
backtracking, predicate indexing for efficient clause lookup, and a
configurable execution environment.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Callable, Dict, Set, Any, Iterator
from collections import defaultdict

from prolog_engine.ast_nodes import (
    Atom, Variable, Number, String, Compound, Clause, Query, Program, Term,
    variables_in, term_to_str, substitute,
)
from prolog_engine.unifier import Unifier, Substitution, UnificationError
from prolog_engine.errors import EngineError, EvaluationError

logger = logging.getLogger(__name__)


class Engine:
    """Mini-Prolog inference engine with backtracking search.

    Features:
    - Predicate indexing for O(1) clause lookup by name/arity
    - Standardizing apart (variable renaming) for each clause use
    - Built-in predicate dispatch
    - Arithmetic evaluation
    - Tracing mode for debugging
    - Dynamic clause management (assert/retract)
    - Configurable depth and solution limits

    Example:
        >>> from prolog_engine import create_engine
        >>> engine = create_engine()
        >>> engine.load_source("parent(tom, bob).")
        >>> results = engine.query("?- parent(X, Y).")
        >>> for r in results:
        ...     print(engine.format_solution(r))
        X = tom, Y = bob
    """

    def __init__(
        self,
        max_depth: int = 1000,
        max_solutions: int = 10000,
        trace: bool = False,
    ):
        """Initialize a new Prolog engine.

        Args:
            max_depth: Maximum inference depth to prevent infinite loops.
            max_solutions: Maximum number of solutions before raising an error.
            trace: Enable trace mode for debugging.
        """
        self._clauses: List[Clause] = []
        # Index: "name/arity" -> list of clause indices in self._clauses
        self._index: Dict[str, List[int]] = defaultdict(list)
        self._builtins: Dict[str, Callable] = {}
        self._var_counter = 0
        self._trace = trace
        self._max_depth = max_depth
        self._max_solutions = max_solutions
        self._solution_count = 0
        logger.debug("Engine initialized (max_depth=%d, max_solutions=%d)",
                     max_depth, max_solutions)

    # ------------------------------------------------------------------
    # Knowledge base management
    # ------------------------------------------------------------------

    def add_clause(self, clause: Clause) -> None:
        """Add a clause to the knowledge base and update the index.

        Args:
            clause: The Clause to add.

        Raises:
            TypeError: If clause is not a Clause instance.
        """
        if not isinstance(clause, Clause):
            raise TypeError(f"Expected Clause, got {type(clause).__name__}")
        idx = len(self._clauses)
        self._clauses.append(clause)
        key = f"{clause.head.name}/{clause.head.arity}"
        self._index[key].append(idx)
        logger.debug("Added clause: %s", clause)

    def remove_clause(self, clause: Clause) -> bool:
        """Remove the first clause matching the given clause from the KB.

        Args:
            clause: The Clause to remove.

        Returns:
            True if a clause was removed, False otherwise.
        """
        for i, c in enumerate(self._clauses):
            if c == clause:
                key = f"{c.head.name}/{c.head.arity}"
                self._clauses.pop(i)
                # Rebuild index (simplest correct approach)
                self._rebuild_index()
                logger.debug("Removed clause: %s", clause)
                return True
        return False

    def retract_clause_by_head(self, head: Compound) -> bool:
        """Remove the first clause whose head matches the given compound.

        Uses unification to find matching clauses.

        Args:
            head: A Compound term to match against clause heads.

        Returns:
            True if a clause was removed, False otherwise.
        """
        key = f"{head.name}/{head.arity}"
        if key not in self._index:
            return False
        for idx in self._index[key]:
            clause = self._clauses[idx]
            try:
                Unifier.unify(head, clause.head)
                # Found a match — remove it
                self._clauses.pop(idx)
                self._rebuild_index()
                logger.debug("Retracted clause with head: %s", term_to_str(head))
                return True
            except UnificationError:
                continue
        return False

    def _rebuild_index(self) -> None:
        """Rebuild the predicate index from scratch."""
        self._index = defaultdict(list)
        for i, clause in enumerate(self._clauses):
            key = f"{clause.head.name}/{clause.head.arity}"
            self._index[key].append(i)

    def load_program(self, program: Program) -> None:
        """Load all clauses from a Program object.

        Args:
            program: A Program instance containing clauses.
        """
        for clause in program.clauses:
            self.add_clause(clause)
        logger.info("Loaded %d clause(s) from program", len(program.clauses))

    def load_source(self, source: str) -> None:
        """Parse and load Prolog source code.

        Args:
            source: A string of Prolog source code.

        Raises:
            PrologError: If the source cannot be parsed.
        """
        from prolog_engine.parser import Parser
        parser = Parser.from_source(source)
        program = parser.parse_program()
        self.load_program(program)

    def load_file(self, filepath: str) -> None:
        """Load and parse a Prolog source file.

        Args:
            filepath: Path to the .pl file to load.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            PrologError: If the file cannot be parsed.
        """
        with open(filepath, "r") as f:
            source = f.read()
        self.load_source(source)
        logger.info("Loaded clauses from file: %s", filepath)

    def clear(self) -> None:
        """Clear the knowledge base and reset variable counter."""
        self._clauses.clear()
        self._index.clear()
        self._var_counter = 0
        logger.debug("Engine cleared")

    @property
    def clauses(self) -> List[Clause]:
        """Return a copy of the current clause list."""
        return list(self._clauses)

    def predicate_index(self) -> Dict[str, int]:
        """Return a summary of predicates and their clause counts.

        Returns:
            Dict mapping "name/arity" to number of clauses.
        """
        return {key: len(indices) for key, indices in self._index.items()}

    # ------------------------------------------------------------------
    # Built-in registration
    # ------------------------------------------------------------------

    def register_builtin(self, name_arity: str, func: Callable) -> None:
        """Register a built-in predicate.

        Args:
            name_arity: Predicate indicator like "is/2" or "=/2".
            func: Callable with signature (engine, args, subst) -> iterable of Substitution.
        """
        self._builtins[name_arity] = func
        logger.debug("Registered builtin: %s", name_arity)

    def get_builtins(self) -> Dict[str, Callable]:
        """Return a copy of the currently registered built-ins."""
        return dict(self._builtins)

    # ------------------------------------------------------------------
    # Built-in calling helper
    # ------------------------------------------------------------------

    @staticmethod
    def _call_builtin(key: str, args: tuple, subst: Substitution, engine: "Engine"):
        """Call a builtin, ensuring it returns an iterable of Substitutions.

        Args:
            key: Built-in predicate indicator (e.g., "is/2").
            args: Arguments to the built-in.
            subst: Current substitution.
            engine: The engine instance.

        Yields:
            Substitution objects for each successful resolution.
        """
        builtin_func = engine._builtins[key]
        result = builtin_func(engine, args, subst)
        if result is None:
            return  # Builtin returned None → no solutions
        try:
            yield from result
        except TypeError:
            if isinstance(result, Substitution):
                yield result
            return

    # ------------------------------------------------------------------
    # Query execution
    # ------------------------------------------------------------------

    def query(self, source: str) -> List[Substitution]:
        """Execute a Prolog query string and return all solutions.

        Args:
            source: A Prolog query string (e.g., "?- father(X, Y).").

        Returns:
            List of Substitution objects representing solutions.
        """
        from prolog_engine.parser import Parser
        parser = Parser.from_source(source)
        query_obj = parser.parse_query()
        self._solution_count = 0
        results = list(self.execute(query_obj))
        logger.info("Query '%s' returned %d solution(s)",
                     source.strip(), len(results))
        return results

    def query_one(self, source: str) -> Optional[Substitution]:
        """Execute a Prolog query and return the first solution, or None.

        Args:
            source: A Prolog query string.

        Returns:
            First Substitution if a solution exists, None otherwise.
        """
        from prolog_engine.parser import Parser
        parser = Parser.from_source(source)
        query_obj = parser.parse_query()
        for subst in self.execute(query_obj):
            logger.debug("query_one found solution")
            return subst
        return None

    def execute(self, query: Query) -> Iterator[Substitution]:
        """Execute a Query object, yielding Substitutions.

        Args:
            query: A Query object containing goal terms.

        Yields:
            Substitution objects for each solution found.
        """
        goals = query.goals
        subst = Substitution()
        self._solution_count = 0
        yield from self._solve(goals, 0, subst, depth=0)

    # ------------------------------------------------------------------
    # Core solver
    # ------------------------------------------------------------------

    def _solve(
        self,
        goals: list,
        goal_index: int,
        subst: Substitution,
        depth: int,
    ) -> Iterator[Substitution]:
        """Solve goals[goal_index:] under the given substitution.

        Uses depth-first SLD resolution with backtracking.
        Implements predicate indexing for efficient clause lookup.

        Args:
            goals: List of goal terms to solve.
            goal_index: Current position in the goals list.
            subst: Current substitution environment.
            depth: Current inference depth (for stack overflow protection).

        Yields:
            Substitution objects for each solution.

        Raises:
            EngineError: If max depth or max solutions exceeded.
        """
        if depth > self._max_depth:
            raise EngineError(
                f"Maximum inference depth ({self._max_depth}) exceeded"
            )

        # All goals solved
        if goal_index >= len(goals):
            self._solution_count += 1
            if self._solution_count > self._max_solutions:
                raise EngineError(
                    f"Maximum solution count ({self._max_solutions}) exceeded — "
                    "query may have infinite solutions"
                )
            yield subst
            return

        goal = subst.apply(goals[goal_index])

        # Tracing
        if self._trace:
            indent = "  " * min(depth, 20)
            print(f"{indent}Call: {term_to_str(goal)}")

        # Handle compound terms
        if isinstance(goal, Compound):
            # Check for cut
            if goal.name == "!" and goal.arity == 0:
                yield from self._solve(goals, goal_index + 1, subst, depth + 1)
                if self._trace:
                    indent = "  " * min(depth, 20)
                    print(f"{indent}Cut: committing to current choice")
                return

            # Check built-in first
            builtin_key = f"{goal.name}/{goal.arity}"
            if builtin_key in self._builtins:
                found = False
                for new_subst in self._call_builtin(builtin_key, goal.args, subst, self):
                    found = True
                    yield from self._solve(goals, goal_index + 1, new_subst, depth + 1)
                if self._trace:
                    indent = "  " * min(depth, 20)
                    result_str = "succeeded" if found else "failed"
                    print(f"{indent}Exit: {term_to_str(goal)} ({result_str})")
                return

            # Find matching clauses using the index
            matching_indices = self._index.get(builtin_key, [])

            for idx in matching_indices:
                clause = self._clauses[idx]
                renamed_clause = self._rename_clause(clause)
                try:
                    new_subst = Unifier.unify(goal, renamed_clause.head, subst.copy())
                except UnificationError:
                    continue

                if renamed_clause.is_fact:
                    yield from self._solve(goals, goal_index + 1, new_subst, depth + 1)
                else:
                    # Replace current goal with body goals, then continue solving
                    body = renamed_clause.body if renamed_clause.body else []
                    combined_goals = list(goals)
                    combined_goals[goal_index:goal_index + 1] = body
                    yield from self._solve(combined_goals, goal_index, new_subst, depth + 1)

        elif isinstance(goal, Atom):
            # Atom as goal — check built-ins or find matching facts/rules
            builtin_key = f"{goal.name}/0"
            if builtin_key in self._builtins:
                for new_subst in self._call_builtin(builtin_key, (), subst, self):
                    yield from self._solve(goals, goal_index + 1, new_subst, depth + 1)
                return

            matching_indices = self._index.get(builtin_key, [])
            for idx in matching_indices:
                clause = self._clauses[idx]
                renamed_clause = self._rename_clause(clause)
                head = renamed_clause.head

                # Match atom goal against clause head
                if isinstance(head, Compound) and head.arity == 0 and head.name == goal.name:
                    match = True
                elif isinstance(head, Atom) and head.name == goal.name:
                    match = True
                else:
                    continue

                if renamed_clause.is_fact:
                    yield from self._solve(goals, goal_index + 1, subst, depth + 1)
                else:
                    # Replace current goal with body goals
                    body = renamed_clause.body if renamed_clause.body else []
                    combined_goals = list(goals)
                    combined_goals[goal_index:goal_index + 1] = body
                    yield from self._solve(combined_goals, goal_index, subst, depth + 1)

    # ------------------------------------------------------------------
    # Variable renaming (standardizing apart)
    # ------------------------------------------------------------------

    def _rename_clause(self, clause: Clause) -> Clause:
        """Rename variables in a clause to avoid capture.

        Each time a clause is used in resolution, its variables are
        renamed with fresh names to prevent variable capture.

        Args:
            clause: The clause to rename.

        Returns:
            A new Clause with renamed variables.
        """
        mapping: dict[Variable, Variable] = {}
        new_head = self._rename_term(clause.head, mapping)
        if clause.is_fact:
            return Clause(new_head)
        body = clause.body if clause.body else []
        new_body = [self._rename_term(g, mapping) for g in body]
        return Clause(new_head, new_body)

    def _rename_term(self, term: Term, mapping: dict[Variable, Variable]) -> Term:
        """Rename variables in a term using the given mapping.

        Args:
            term: The term to rename.
            mapping: Dict mapping old variables to new ones.

        Returns:
            A new term with renamed variables.
        """
        if isinstance(term, Variable):
            if term not in mapping:
                self._var_counter += 1
                mapping[term] = Variable(f"_{term.name}_{self._var_counter}")
            return mapping[term]
        if isinstance(term, Compound):
            new_args = tuple(self._rename_term(a, mapping) for a in term.args)
            return Compound(term.name, new_args)
        return term

    def copy_term(self, term: Term) -> Term:
        """Create a fresh copy of a term with new variables.

        Args:
            term: The term to copy.

        Returns:
            A new term with fresh variable names.
        """
        mapping: dict[Variable, Variable] = {}
        return self._rename_term(term, mapping)

    # ------------------------------------------------------------------
    # Tracing
    # ------------------------------------------------------------------

    @property
    def trace(self) -> bool:
        """Whether trace mode is enabled."""
        return self._trace

    @trace.setter
    def trace(self, value: bool) -> None:
        """Enable or disable trace mode."""
        self._trace = value
        logger.info("Trace mode %s", "enabled" if value else "disabled")

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    @property
    def max_depth(self) -> int:
        """Maximum inference depth."""
        return self._max_depth

    @max_depth.setter
    def max_depth(self, value: int) -> None:
        """Set maximum inference depth."""
        if value < 1:
            raise ValueError("max_depth must be at least 1")
        self._max_depth = value

    @property
    def max_solutions(self) -> int:
        """Maximum number of solutions before raising an error."""
        return self._max_solutions

    @max_solutions.setter
    def max_solutions(self, value: int) -> None:
        """Set maximum number of solutions."""
        if value < 1:
            raise ValueError("max_solutions must be at least 1")
        self._max_solutions = value

    # ------------------------------------------------------------------
    # Pretty-printing solutions
    # ------------------------------------------------------------------

    def format_solution(self, subst: Substitution, original_goals: list | None = None) -> str:
        """Format a substitution as a human-readable solution string.

        Args:
            subst: The substitution to format.
            original_goals: Optional list of goals to extract variables from.

        Returns:
            A formatted string like "X = tom, Y = bob" or "yes".
        """
        if not subst:
            return "yes"

        # Determine which variables to show
        if original_goals:
            target_vars = set()
            for g in original_goals:
                target_vars |= variables_in(g)
            bindings = [(v, subst.apply(v)) for v in target_vars if v in subst]
        else:
            bindings = [(v, subst.apply(v)) for v, _ in subst.items()]

        if not bindings:
            return "yes"

        parts = []
        for var, val in bindings:
            if not (isinstance(val, Variable) and val.name.startswith("_")):
                parts.append(f"{var.name} = {term_to_str(val)}")

        if not parts:
            return "yes"
        return ", ".join(parts)

    # ------------------------------------------------------------------
    # Arithmetic evaluation helper
    # ------------------------------------------------------------------

    def evaluate(self, term: Term, subst: Substitution) -> Number:
        """Evaluate an arithmetic expression to a Number.

        Supports: +, -, *, /, //, mod, rem, **, ^, abs, max, min,
        sqrt, sin, cos, tan, log, exp, floor, ceiling, round,
        and constants pi, e.

        Args:
            term: The term to evaluate.
            subst: Current substitution environment.

        Returns:
            A Number representing the evaluated result.

        Raises:
            EngineError: If division by zero or other runtime error.
            EvaluationError: If the term cannot be evaluated.
        """
        term = subst.apply(term)

        if isinstance(term, Number):
            return term

        if isinstance(term, Compound):
            name = term.name
            args = term.args

            # Unary minus
            if name == "-" and len(args) == 1:
                val = self.evaluate(args[0], subst).value
                return Number(-val)

            # Unary plus
            if name == "+" and len(args) == 1:
                return self.evaluate(args[0], subst)

            # Evaluate all arguments for binary ops
            evaluated = [self.evaluate(a, subst) for a in args]
            vals = [a.value for a in evaluated]

            if name == "+" and len(vals) == 2:
                return Number(vals[0] + vals[1])
            if name == "-" and len(vals) == 2:
                return Number(vals[0] - vals[1])
            if name == "*" and len(vals) == 2:
                return Number(vals[0] * vals[1])
            if name == "/" and len(vals) == 2:
                if vals[1] == 0:
                    raise EngineError("Division by zero")
                return Number(vals[0] / vals[1])
            if name == "//" and len(vals) == 2:
                if vals[1] == 0:
                    raise EngineError("Division by zero")
                # Prolog integer division rounds toward zero
                result = int(vals[0]) / int(vals[1])
                return Number(float(int(result)))
            if name == "mod" and len(vals) == 2:
                return Number(int(vals[0]) % int(vals[1]))
            if name == "rem" and len(vals) == 2:
                # Prolog rem: remainder from toward-zero division
                a, b = int(vals[0]), int(vals[1])
                return Number(float(a - (int(a / b)) * b))
            if name == "abs" and len(vals) == 1:
                return Number(abs(vals[0]))
            if name == "max" and len(vals) == 2:
                return Number(max(vals[0], vals[1]))
            if name == "min" and len(vals) == 2:
                return Number(min(vals[0], vals[1]))
            if name == "**" and len(vals) == 2:
                return Number(vals[0] ** vals[1])
            if name == "^" and len(vals) == 2:
                return Number(vals[0] ** vals[1])
            if name == "sqrt" and len(vals) == 1:
                import math
                return Number(math.sqrt(vals[0]))
            if name == "sin" and len(vals) == 1:
                import math
                return Number(math.sin(vals[0]))
            if name == "cos" and len(vals) == 1:
                import math
                return Number(math.cos(vals[0]))
            if name == "tan" and len(vals) == 1:
                import math
                return Number(math.tan(vals[0]))
            if name == "log" and len(vals) == 1:
                import math
                return Number(math.log(vals[0]))
            if name == "exp" and len(vals) == 1:
                import math
                return Number(math.exp(vals[0]))
            if name == "floor" and len(vals) == 1:
                return Number(float(int(vals[0])))
            if name == "ceiling" and len(vals) == 1:
                import math
                return Number(float(math.ceil(vals[0])))
            if name == "round" and len(vals) == 1:
                return Number(float(round(vals[0])))

            raise EvaluationError(f"Unknown arithmetic function: {name}/{len(vals)}")

        if isinstance(term, Atom):
            if term.name == "pi":
                return Number(3.141592653589793)
            if term.name == "e":
                return Number(2.718281828459045)
            raise EvaluationError(f"Unknown arithmetic constant: {term.name}")

        raise EngineError(f"Cannot evaluate {term} as arithmetic")

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def statistics(self) -> Dict[str, Any]:
        """Return engine statistics.

        Returns:
            Dict with keys: clauses, predicates, builtins, max_depth,
            max_solutions, trace.
        """
        return {
            "clauses": len(self._clauses),
            "predicates": self.predicate_index(),
            "builtins": len(self._builtins),
            "max_depth": self._max_depth,
            "max_solutions": self._max_solutions,
            "trace": self._trace,
        }