from smt_solver import Solver
from smt_solver.ast import App, Var, NumConst, REAL, BOOL, Eq, Gt, Neg, And, Or, Not, Lt

x = Var("x", REAL)
y = Var("y", REAL)

formula1 = Or(
    And(Gt(x, NumConst(0.0)), Eq(y, x)),
    And(Not(Gt(x, NumConst(0.0))), Eq(y, Neg(x)))
)
formula2 = Lt(x, NumConst(0.0))
formula3 = Eq(y, NumConst(5.0))

s = Solver()
s.declare_const("x", REAL)
s.declare_const("y", REAL)
s.assert_term(formula1)
s.assert_term(formula2)
s.assert_term(formula3)

# Manually trace
s._sat = type(s._sat)()
s._atom_to_lit = {}
s._lit_to_atom = {}
s._encode_cache = {}

all_cnf = []
for formula in s.assertions:
    cnf = s._to_cnf(formula)
    all_cnf.extend(cnf)

print("Atom to lit:", {str(k): v for k, v in s._atom_to_lit.items()})
print("CNF clauses:", len(all_cnf))

for clause in all_cnf:
    s._sat.add_clause(clause)

# Run DPLL(T) loop manually
for round_num in range(10):
    result = s._sat.solve(max_conflicts=10000)
    print(f"\nRound {round_num}: SAT={result}")
    if result != "sat":
        break

    assignment = s._sat.model()
    print(f"  Assignment: {assignment}")

    # Classify atoms
    for lit, atom in s._lit_to_atom.items():
        val = assignment.get(lit)
        is_arith = s._is_arith_atom(atom)
        print(f"    {str(atom)}: lit={lit}, val={val}, arith={is_arith}")

    consistent, conflict = s._check_theory(assignment)
    print(f"  Theory consistent: {consistent}, conflict: {conflict}")

    if consistent:
        print("SAT!")
        break

    if conflict:
        neg_clause = [-l for l in conflict]
        s._sat.cancel_until(0)
        ok = s._sat.add_clause(neg_clause)
        print(f"  Added lemma {neg_clause}: {ok}")
        if not ok:
            print("UNSAT!")
            break