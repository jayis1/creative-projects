"""Enhanced smoke test for Phase 2 features."""
from datalog import Engine, parse

# Test 1: arithmetic builtins
e = Engine()
e.add_source("""
num(1). num(2). num(3). num(4). num(5).
doubled(X, Y) :- num(X), mul(X, 2, Y).
squared(X, Y) :- num(X), mul(X, X, Y).
""")
print("doubled:", sorted(e.relation("doubled")))
print("squared:", sorted(e.relation("squared")))

# Test 2: retraction
e2 = Engine()
e2.add_source("edge(a, b). edge(b, c). edge(c, d).")
print("before retract:", e2.facts("edge"))
e2.retract_fact("edge", "b", "c")
print("after retract edge(b,c):", e2.facts("edge"))
assert ("b", "c") not in e2.facts("edge")

# Test 3: explain
e3 = Engine()
e3.add_source("""
edge(a, b). edge(b, c).
path(X, Y) :- edge(X, Y).
path(X, Y) :- edge(X, Z), path(Z, Y).
""")
print("\n--- explain path ---")
print(e3.explain("path"))
print("--- explain edge ---")
print(e3.explain("edge"))

# Test 4: JSON export/import
e4 = Engine()
e4.add_source("""
foo(a, 1). foo(b, 2). foo(c, 3).
bar(X) :- foo(X, Y), Y > 1.
""")
j = e4.to_json()
print("\n--- JSON export ---")
print(j)
e5 = Engine()
e5.from_json(j)
print("bar after import:", sorted(e5.relation("bar")))

# Test 5: clear
e5.clear()
assert e5.predicates() == []
print("\nclear: OK")

# Test 6: rules listing
e6 = Engine()
e6.add_source("""
edge(a, b).
path(X, Y) :- edge(X, Y).
path(X, Y) :- edge(X, Z), path(Z, Y).
""")
rules = e6.rules()
print(f"\nrules count: {len(rules)}")
for r in rules:
    print(f"  {r}")

print("\nALL ENHANCEMENTS OK")