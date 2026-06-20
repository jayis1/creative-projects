from datalog import Engine, parse

# Test 1: transitive closure
e = Engine()
e.add_source("""
edge(a, b). edge(b, c). edge(c, d). edge(d, e).
path(X, Y) :- edge(X, Y).
path(X, Y) :- edge(X, Z), path(Z, Y).
""")
result = e.query("path(a, Y)")
print("path(a, Y):", [r["Y"] for r in result])
print("relation path:", e.relation("path"))

# Test 2: negation (stratified) — "sink" nodes with no outgoing edges
e2 = Engine()
e2.add_source("""
edge(a, b). edge(b, c). edge(c, a).
out(X) :- edge(X, Y).
sink(X) :- node(X), not out(X).
node(a). node(b). node(c). node(d).
""")
print("sink:", sorted(e2.relation("sink")))

# Test 3: built-in comparison (infix)
e3 = Engine()
e3.add_source("""
num(1). num(2). num(3). num(4). num(5).
big(X) :- num(X), X > 3.
""")
print("big:", sorted(e3.relation("big")))

# Test 4: prefix form
e4 = Engine()
e4.add_source("""
num(1). num(2). num(3). num(4). num(5).
small(X) :- num(X), <(X, 3).
""")
print("small:", sorted(e4.relation("small")))

print("ALL OK")