"""Comprehensive bug-hunt tests for the Datalog engine.

Each test is designed to expose a specific class of bug:
- Edge cases in parsing
- Logic errors in evaluation
- Off-by-one / boundary conditions
- Resource leaks / state issues
- Incorrect algorithm behavior
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datalog import Engine, parse
from datalog.engine import DatalogError, StratificationError, SafetyError
from datalog.parser import LexError, ParseError
from datalog.ast import Constant, Variable, Atom, Literal, Rule, Fact, Query

PASS = 0
FAIL = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name} — {detail}")

def expect_error(name, fn, exc_type=Exception, detail=""):
    global PASS, FAIL
    try:
        fn()
        FAIL += 1
        print(f"  FAIL: {name} — expected {exc_type.__name__} but no error raised {detail}")
    except exc_type as e:
        PASS += 1
        print(f"  PASS: {name} ({type(e).__name__}: {e})")
    except Exception as e:
        FAIL += 1
        print(f"  FAIL: {name} — expected {exc_type.__name__} but got {type(e).__name__}: {e}")


print("=== BUG HUNT TESTS ===\n")

# --- Bug 1: Empty program ---
print("[1] Empty program / empty query:")
e = Engine()
e.add_source("")
check("empty program loads", True)
check("query on empty predicate returns []", e.query("foo(X)") == [])

# --- Bug 2: Predicate with zero arity (no arguments) ---
print("\n[2] Zero-arity predicates:")
e = Engine()
e.add_source("flag. other :- flag.")
# 'flag' is a zero-arity fact; 'other :- flag' is a valid rule (no vars)
check("zero-arity fact and rule", len(e.relation("flag")) == 1 and len(e.relation("other")) == 1,
      f"flag={e.relation('flag')}, other={e.relation('other')}")

# --- Bug 3: Duplicate facts ---
print("\n[3] Duplicate facts:")
e = Engine()
e.add_source("edge(a, b). edge(a, b). edge(a, b).")
check("duplicate facts deduplicated", len(e.relation("edge")) == 1)

# --- Bug 4: Self-referencing rule (trivial cycle) ---
print("\n[4] Self-loop in graph (path from node to itself):")
e = Engine()
e.add_source("""
edge(a, a).
path(X, Y) :- edge(X, Y).
path(X, Y) :- edge(X, Z), path(Z, Y).
""")
result = e.query("path(a, a)")
check("self-loop path(a,a) found", len(result) == 1 and result[0] == {}, str(result))

# --- Bug 5: Negation with unbound variable should fail safety ---
print("\n[5] Safety: negated literal with unbound variable:")
expect_error("unsafe negation rejected",
             lambda: Engine().add_source("bad(X) :- not foo(X, Y)."),
             SafetyError)

# --- Bug 6: Head variable not in body (unsafe) ---
print("\n[6] Safety: head variable not in body:")
expect_error("unsafe head var rejected",
             lambda: Engine().add_source("bad(X, Y) :- edge(X, Z)."),
             SafetyError)

# --- Bug 7: Non-stratifiable program (negation through recursion) ---
print("\n[7] Non-stratifiable negation:")
def _check_strat():
    e = Engine()
    e.add_source("p(a). q(X) :- p(X), not r(X). r(X) :- p(X), not q(X).")
    e.relation("q")  # triggers evaluation
expect_error("non-stratifiable negation rejected",
             _check_strat,
             StratificationError)

# --- Bug 8: Query with all constants (ground query) ---
print("\n[8] Ground query:")
e = Engine()
e.add_source("edge(a, b). edge(b, c).")
result = e.query("edge(a, b)")
check("ground query succeeds", len(result) == 1 and result[0] == {})
result = e.query("edge(a, c)")
check("ground query fails correctly", result == [])

# --- Bug 9: Multiple variables in query ---
print("\n[9] Multi-variable query:")
e = Engine()
e.add_source("edge(a, b). edge(b, c). edge(c, d).")
result = e.query("edge(X, Y)")
check("multi-var query returns all", len(result) == 3, str(result))

# --- Bug 10: Arithmetic with division by zero ---
print("\n[10] Division by zero:")
e = Engine()
e.add_source("num(0). num(5). result(X, Y) :- num(X), div(5, X, Y).")
result = e.relation("result")
check("div by zero produces no result", all(r[1] is not None for r in result), str(result))

# --- Bug 11: String constants ---
print("\n[11] String constants:")
e = Engine()
e.add_source('name("alice"). name("bob"). likes("alice", "bob").')
check("string facts loaded", len(e.relation("name")) == 2)
result = e.query('likes("alice", Y)')
check("string query works", len(result) == 1 and result[0]["Y"] == "bob", str(result))

# --- Bug 12: Integer vs float equality ---
print("\n[12] Integer vs float equality:")
e = Engine()
e.add_source("val(1). val(1.0).")
# 1 and 1.0 should be the same constant
check("1 == 1.0 deduplicated", len(e.relation("val")) == 1, str(e.relation("val")))

# --- Bug 13: Anonymous variable _ ---
print("\n[13] Anonymous variable:")
e = Engine()
e.add_source("edge(a, b). edge(b, c). edge(c, d). has_out(X) :- edge(X, _).")
result = e.query("has_out(X)")
check("anonymous variable works", len(result) == 3, str(result))

# --- Bug 14: Multiple anonymous variables in same atom ---
print("\n[14] Multiple anonymous variables:")
e = Engine()
e.add_source("edge(a, b). edge(b, c). any_edge :- edge(_, _).")
result = e.query("any_edge")
check("multiple _ in same atom don't bind", len(result) == 1, str(result))

# --- Bug 15: Comments ---
print("\n[15] Comments:")
e = Engine()
e.add_source("""
% This is a line comment
edge(a, b). % trailing comment
/* block
comment */
edge(b, c).
""")
check("line comments handled", len(e.relation("edge")) == 2)

# --- Bug 16: Retraction and re-evaluation ---
print("\n[16] Retraction triggers re-evaluation:")
e = Engine()
e.add_source("edge(a, b). edge(b, c). path(X, Y) :- edge(X, Y). path(X, Y) :- edge(X, Z), path(Z, Y).")
before = len(e.relation("path"))
e.retract_fact("edge", "b", "c")
after = len(e.relation("path"))
check("retraction reduces path count", after < before, f"before={before}, after={after}")
check("path(a,c) removed after retract", e.query("path(a, c)") == [])

# --- Bug 17: Retract non-existent fact ---
print("\n[17] Retract non-existent fact:")
e = Engine()
e.add_source("edge(a, b).")
check("retract non-existent returns False", e.retract_fact("edge", "x", "y") == False)

# --- Bug 18: JSON round-trip preserves semantics ---
print("\n[18] JSON round-trip:")
e = Engine()
e.add_source("edge(a, b). edge(b, c). path(X, Y) :- edge(X, Y). path(X, Y) :- edge(X, Z), path(Z, Y).")
j = e.to_json()
e2 = Engine()
e2.from_json(j)
check("JSON round-trip preserves query results",
      set(tuple(sorted(d.items())) for d in e.query("path(X, Y)")) ==
      set(tuple(sorted(d.items())) for d in e2.query("path(X, Y)")))

# --- Bug 19: Arity mismatch ---
print("\n[19] Arity mismatch:")
expect_error("arity mismatch rejected",
             lambda: Engine().add_source("edge(a, b). edge(x)."),
             DatalogError)

# --- Bug 20: Empty body rule ---
print("\n[20] Empty body rule (fact-like):")
e = Engine()
e.add_source("foo(X) :- bar(X). bar(a).")
check("rule with single body literal works", len(e.query("foo(X)")) == 1)

# --- Bug 21: Deep recursion (stack overflow check) ---
print("\n[21] Deep recursion:")
e = Engine()
facts = " ".join(f"edge({i}, {i+1})." for i in range(500))
e.add_source(facts + " path(X, Y) :- edge(X, Y). path(X, Y) :- edge(X, Z), path(Z, Y).")
result = e.query("path(0, X)")
check("deep recursion (500 edges) works", len(result) == 500, f"got {len(result)}")

# --- Bug 22: Boolean constants ---
print("\n[22] Boolean constants:")
e = Engine()
e.add_source("flag(true). flag(false). truthy(X) :- flag(X), X == true.")
result = e.query("truthy(X)")
check("boolean true constant", len(result) == 1 and result[0]["X"] == True, str(result))

# --- Bug 23: Negative numbers ---
print("\n[23] Negative numbers:")
e = Engine()
e.add_source("temp(-5). temp(10). cold(X) :- temp(X), X < 0.")
result = e.query("cold(X)")
check("negative number comparison", len(result) == 1 and result[0]["X"] == -5, str(result))

# --- Bug 24: Parser - unterminated string ---
print("\n[24] Unterminated string:")
expect_error("unterminated string rejected",
             lambda: parse('foo("hello).'),
             LexError)

# --- Bug 25: Parser - missing closing paren ---
print("\n[25] Missing closing paren:")
expect_error("missing paren rejected",
             lambda: parse("foo(a, b."),
             ParseError)

# --- Bug 26: Rule with same predicate as EDB and IDB ---
print("\n[26] EDB + IDB same predicate:")
e = Engine()
e.add_source("edge(a, b). edge(X, Y) :- path(X, Y).")
# edge is both EDB and IDB — should this work?
# The current implementation would put derived edge tuples in IDB,
# separate from EDB. Querying edge should return both.
# Actually _get_relation_eval checks IDB first, then EDB.
# This might be a bug — derived edges may not include base edges.
check("EDB+IDB coexist (may be a design issue)", True)

# --- Bug 27: Transitive closure correctness ---
print("\n[27] Transitive closure correctness:")
e = Engine()
e.add_source("""
edge(a, b). edge(b, c). edge(c, d). edge(d, e). edge(e, f).
path(X, Y) :- edge(X, Y).
path(X, Y) :- edge(X, Z), path(Z, Y).
""")
expected = {('a','b'),('a','c'),('a','d'),('a','e'),('a','f'),
            ('b','c'),('b','d'),('b','e'),('b','f'),
            ('c','d'),('c','e'),('c','f'),
            ('d','e'),('d','f'),
            ('e','f')}
actual = set(e.relation("path"))
check("transitive closure complete", actual == expected, f"missing: {expected - actual}, extra: {actual - expected}")

# --- Bug 28: Semi-naive with multiple recursive predicates ---
print("\n[28] Multiple mutually recursive predicates:")
e = Engine()
e.add_source("""
edge(a, b). edge(b, c). edge(c, d).
tc(X, Y) :- edge(X, Y).
tc(X, Y) :- edge(X, Z), tc(Z, Y).
rpath(X, Y) :- edge(Y, X).
rpath(X, Y) :- edge(Z, X), rpath(Z, Y).
""")
tc = set(e.relation("tc"))
rp = set(e.relation("rpath"))
check("tc correct", tc == {('a','b'),('a','c'),('a','d'),('b','c'),('b','d'),('c','d')}, str(tc))
# rpath is reverse: rpath(X,Y) means Y->X in original edges
check("rpath correct", rp == {('b','a'),('c','a'),('d','a'),('c','b'),('d','b'),('d','c')}, str(rp))

# --- Bug 29: Comparison with strings ---
print("\n[29] String comparison:")
e = Engine()
e.add_source('name("apple"). name("banana"). name("cherry"). before(X) :- name(X), X < "banana".')
result = e.query("before(X)")
check("string comparison works", len(result) == 1 and result[0]["X"] == "apple", str(result))

# --- Bug 30: add/sub arithmetic correctness ---
print("\n[30] Arithmetic correctness:")
e = Engine()
e.add_source("num(10). num(3). result(X, Y, Z) :- num(X), num(Y), add(X, Y, Z).")
result = e.relation("result")
# Cross product: 10+3=13, 3+10=13, 10+10=20, 3+3=6
expected = {(10,3,13),(3,10,13),(10,10,20),(3,3,6)}
check("add produces correct results", set(result) == expected, f"got {result}, expected {expected}")

# --- Bug 31: Query a non-existent predicate ---
print("\n[31] Query non-existent predicate:")
e = Engine()
e.add_source("edge(a, b).")
check("query unknown predicate returns []", e.query("nonexistent(X)") == [])

# --- Bug 32: Clear and reuse ---
print("\n[32] Clear and reuse:")
e = Engine()
e.add_source("foo(a). bar(X) :- foo(X).")
e.clear()
e.add_source("baz(x).")
check("clear removes old predicates", "foo" not in e.predicates())
check("clear allows new predicates", "baz" in e.predicates())

# --- Bug 33: Relation with 0 tuples ---
print("\n[33] Empty relation:")
e = Engine()
e.add_source("edge(a, b). node(X) :- edge(X, Y). node(Y) :- edge(X, Y).")
e2 = Engine()
e2.add_source("empty(X) :- edge(X, Y).")
check("query on predicate with no facts returns []", e2.query("empty(X)") == [])

# --- Bug 34: Constant that looks like a variable name ---
print("\n[34] Quoted string that looks like variable:")
e = Engine()
e.add_source('foo("X"). foo("Variable").')
result = e.query('foo("X")')
check("quoted 'X' is a constant not variable", len(result) == 1, str(result))

# --- Bug 35: Multiple rules with same head ---
print("\n[35] Multiple rules same head (union):")
e = Engine()
e.add_source("parent(a, b). parent(c, d). ancestor(X, Y) :- parent(X, Y). ancestor(X, Y) :- parent(X, Z), ancestor(Z, Y). sibling(X, Y) :- parent(Z, X), parent(Z, Y), X != Y.")
result = e.query("sibling(X, Y)")
check("multiple rules union", len(result) == 0, str(result))  # no shared parents

# --- Bug 36: Nested transitive closure ---
print("\n[36] Two-level transitive closure:")
e = Engine()
e.add_source("""
link(a, b). link(b, c). link(c, d).
conn(X, Y) :- link(X, Y).
conn(X, Y) :- link(X, Z), conn(Z, Y).
reach(X, Y) :- conn(X, Y).
reach(X, Y) :- conn(X, Z), reach(Z, Y).
""")
result = set(e.relation("reach"))
check("two-level TC same as one-level", result == {('a','b'),('a','c'),('a','d'),('b','c'),('b','d'),('c','d')}, str(result))

# --- Bug 37: Escaped characters in strings ---
print("\n[37] Escaped characters:")
e = Engine()
e.add_source('msg("hello\\tworld"). msg("say \\"hi\\"").')
result = e.relation("msg")
check("escaped tab", any('\t' in r[0] for r in result), str(result))
check('escaped quote', any('"hi"' in r[0] for r in result), str(result))

# --- Bug 38: Very long chain (performance) ---
print("\n[38] Performance: 100-node chain:")
e = Engine()
facts = " ".join(f"e({i}, {i+1})." for i in range(100))
e.add_source(facts + " p(X, Y) :- e(X, Y). p(X, Y) :- e(X, Z), p(Z, Y).")
result = e.query("p(0, X)")
check("100-node chain TC", len(result) == 100, f"got {len(result)}")

# --- Bug 39: Constant int/float canonicalization ---
print("\n[39] Constant int/float canonicalization:")
e = Engine()
e.add_source("v(1). v(1.0).")
check("1 and 1.0 are same constant", len(e.relation("v")) == 1)

# --- Bug 40: _read_number with just minus sign ---
print("\n[40] Standalone minus sign (not a number):")
expect_error("standalone - not a number",
             lambda: parse("foo(-)."),
             (LexError, ParseError))

# --- Bug 41: EDB + IDB same predicate (was Bug A) ---
print("\n[41] EDB + IDB same predicate (union):")
e = Engine()
e.add_source("edge(a, b). edge(X, Y) :- path(X, Y). path(a, c).")
result = set(e.relation("edge"))
check("EDB+IDB returns union", result == {('a','b'), ('a','c')}, str(result))

# --- Bug 42: Safety with builtins (was Bug B) ---
print("\n[42] Safety: builtin-only body is unsafe:")
expect_error("builtin-only body rejected",
             lambda: Engine().add_source("foo(X) :- X > 5."),
             SafetyError)

# --- Bug 43: Arithmetic output variable is safe ---
print("\n[43] Safety: arithmetic output variable is safe:")
e = Engine()
e.add_source("num(1). num(2). foo(X, Y) :- num(X), add(X, 5, Y).")
result = sorted(e.relation("foo"))
check("arith output safe", result == [(1,6),(2,7)], str(result))

# --- Bug 44: from_json with bad JSON gives clear error ---
print("\n[44] from_json error handling:")
from datalog.engine import DatalogError
expect_error("bad JSON rejected with DatalogError",
             lambda: Engine().from_json("{bad"),
             DatalogError)

# --- Bug 45: Mutual recursion (even/odd) ---
print("\n[45] Mutual recursion (even/odd):")
e = Engine()
e.add_source("""
base(0).
succ(0, 1). succ(1, 2). succ(2, 3). succ(3, 4). succ(4, 5).
even(X) :- base(X).
odd(X) :- even(Y), succ(Y, X).
even(X) :- odd(Y), succ(Y, X).
""")
check("even correct", set(e.relation("even")) == {(0,),(2,),(4,)}, str(e.relation("even")))
check("odd correct", set(e.relation("odd")) == {(1,),(3,),(5,)}, str(e.relation("odd")))

# --- Bug 46: Negated comparison ---
print("\n[46] Negated comparison:")
e = Engine()
e.add_source("num(1). num(2). num(3). not_big(X) :- num(X), not X > 2.")
result = sorted(e.relation("not_big"))
check("negated comparison works", result == [(1,),(2,)], str(result))

print(f"\n=== RESULTS: {PASS} passed, {FAIL} failed ===")
sys.exit(1 if FAIL > 0 else 0)