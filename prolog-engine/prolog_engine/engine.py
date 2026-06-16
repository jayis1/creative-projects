"""Prolog inference engine with backtracking search."""

from __future__ import annotations

from typing import List, Optional, Callable, Dict, Any
from prolog_engine.ast_nodes import (
    Atom, Variable, Number, String, Compound, Clause, Query, Program, Term,
    variables_in, term_to_str, substitute,
)
from prolog_engine.unifier import Unifier, Substitution, UnificationError


class EngineError(Exception):
    """Raised when the engine encounters an error during evaluation."""
    pass


class Engine:
    """Mini-Prolog inference engine with backtracking search."""

    def __init__(self):
        self._clauses: List[Clause] = []
        self._builtins: Dict[str, Callable] = {}
        self._var_counter = 0
        self._trace = False
        self._max_depth = 1000

    # ------------------------------------------------------------------
    # Knowledge base management
    # ------------------------------------------------------------------

    def add_clause(self, clause: Clause) -> None:
        """Add a clause to the knowledge base."""
        self._clauses.append(clause)

    def load_program(self, program: Program) -> None:
        """Load all clauses from a Program object."""
        for clause in program.clauses:
            self.add_clause(clause)

    def load_source(self, source: str) -> None:
        """Parse and load Prolog source code."""
        from prolog_engine.parser import Parser
        parser = Parser.from_source(source)
        program = parser.parse_program()
        self.load_program(program)

    def clear(self) -> None:
        """Clear the knowledge base and reset."""
        self._clauses.clear()
        self._var_counter = 0

    @property
    def clauses(self) -> List[Clause]:
        return list(self._clauses)

    # ------------------------------------------------------------------
    # Built-in registration
    # ------------------------------------------------------------------

    def register_builtin(self, name_arity: str, func: Callable) -> None:
        """Register a built-in predicate.

        name_arity should be like "is/2" or "=/2".
        func signature: (engine, args, subst) -> iterable of Substitution
        """
        self._builtins[name_arity] = func

    # ------------------------------------------------------------------
    # Built-in calling helper
    # ------------------------------------------------------------------

    @staticmethod
    def _call_builtin(key: str, args: tuple, subst: Substitution, engine: "Engine"):
        """Call a builtin, ensuring it returns an iterable of Substitutions."""
        # Import here to avoid circular imports
        builtin_func = engine._builtins[key]
        result = builtin_func(engine, args, subst)
        if result is None:
            return  # Builtin returned None → no solutions
        try:
            yield from result
        except TypeError:
            # Not iterable — builtin returned a single Substitution
            if isinstance(result, Substitution):
                yield result
            return

    # ------------------------------------------------------------------
    # Query execution
    # ------------------------------------------------------------------

    def query(self, source: str) -> List[Substitution]:
        """Execute a Prolog query string and return all solutions."""
        from prolog_engine.parser import Parser
        parser = Parser.from_source(source)
        query_obj = parser.parse_query()
        return list(self.execute(query_obj))

    def query_one(self, source: str) -> Optional[Substitution]:
        """Execute a Prolog query and return the first solution, or None."""
        from prolog_engine.parser import Parser
        parser = Parser.from_source(source)
        query_obj = parser.parse_query()
        for subst in self.execute(query_obj):
            return subst
        return None

    def execute(self, query: Query) -> Any:
        """Execute a Query object, yielding Substitutions."""
        goals = query.goals
        subst = Substitution()
        yield from self._solve(goals, 0, subst, depth=0)

    # ------------------------------------------------------------------
    # Core solver
    # ------------------------------------------------------------------

    def _solve(self, goals: list, goal_index: int, subst: Substitution, depth: int) -> Any:
        """Solve goals[goal_index:] under the given substitution."""
        if depth > self._max_depth:
            raise EngineError(f"Maximum inference depth ({self._max_depth}) exceeded")

        # All goals solved
        if goal_index >= len(goals):
            yield subst
            return

        goal = subst.apply(goals[goal_index])

        # Handle compound terms
        if isinstance(goal, Compound):
            # Check for cut
            if goal.name == "!" and goal.arity == 0:
                yield from self._solve(goals, goal_index + 1, subst, depth + 1)
                return

            # Check built-in first
            builtin_key = f"{goal.name}/{goal.arity}"
            if builtin_key in self._builtins:
                for new_subst in self._call_builtin(builtin_key, goal.args, subst, self):
                    yield from self._solve(goals, goal_index + 1, new_subst, depth + 1)
                return

            # Find matching clauses
            matching = []
            for clause in self._clauses:
                head = clause.head
                if isinstance(head, Compound):
                    if goal.name == head.name and goal.arity == head.arity:
                        matching.append(clause)

            for clause in matching:
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

            for clause in self._clauses:
                head = clause.head
                if isinstance(head, Compound) and head.arity == 0 and head.name == goal.name:
                    yield from self._solve(goals, goal_index + 1, subst, depth + 1)
                elif isinstance(head, Atom) and head.name == goal.name:
                    yield from self._solve(goals, goal_index + 1, subst, depth + 1)

    # ------------------------------------------------------------------
    # Variable renaming (standardizing apart)
    # ------------------------------------------------------------------

    def _rename_clause(self, clause: Clause) -> Clause:
        """Rename variables in a clause to avoid capture."""
        mapping: dict[Variable, Variable] = {}
        new_head = self._rename_term(clause.head, mapping)
        if clause.is_fact:
            return Clause(new_head)
        body = clause.body if clause.body else []
        new_body = [self._rename_term(g, mapping) for g in body]
        return Clause(new_head, new_body)

    def _rename_term(self, term: Term, mapping: dict[Variable, Variable]) -> Term:
        """Rename variables in a term using the given mapping."""
        if isinstance(term, Variable):
            if term not in mapping:
                self._var_counter += 1
                mapping[term] = Variable(f"_{term.name}_{self._var_counter}")
            return mapping[term]
        if isinstance(term, Compound):
            new_args = tuple(self._rename_term(a, mapping) for a in term.args)
            return Compound(term.name, new_args)
        return term

    # ------------------------------------------------------------------
    # Pretty-printing solutions
    # ------------------------------------------------------------------

    def format_solution(self, subst: Substitution, original_goals: list | None = None) -> str:
        """Format a substitution as a human-readable solution string."""
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
        """Evaluate an arithmetic expression to a Number."""
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
                return Number(int(vals[0]) // int(vals[1]))
            if name == "mod" and len(vals) == 2:
                return Number(int(vals[0]) % int(vals[1]))
            if name == "rem" and len(vals) == 2:
                return Number(int(vals[0]) % int(vals[1]))
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

            raise EngineError(f"Unknown arithmetic function: {name}/{len(vals)}")

        if isinstance(term, Atom):
            if term.name == "pi":
                return Number(3.141592653589793)
            raise EngineError(f"Unknown arithmetic constant: {term.name}")

        raise EngineError(f"Cannot evaluate {term} as arithmetic")