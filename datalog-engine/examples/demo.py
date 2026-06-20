#!/usr/bin/env python3
"""Demo script showcasing all datalog-engine features.

Run: python3 examples/demo.py
"""

import sys
import os

# Add the parent directory to the path so we can import datalog
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datalog import Engine, format_results


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def main():
    section("1. Transitive Closure (Graph Reachability)")
    e = Engine()
    e.add_source("""
        edge(a, b). edge(b, c). edge(c, d). edge(d, e).
        edge(a, c). edge(b, d).
        path(X, Y) :- edge(X, Y).
        path(X, Y) :- edge(X, Z), path(Z, Y).
    """)
    results = e.query("path(a, Y)")
    print(format_results(results, "table"))

    section("2. Stratified Negation (Sink Detection)")
    e2 = Engine()
    e2.add_source("""
        edge(a, b). edge(b, c). edge(c, a).
        out(X) :- edge(X, Y).
        sink(X) :- node(X), not out(X).
        node(a). node(b). node(c). node(d).
    """)
    print("Sinks:", e2.relation("sink"))

    section("3. Arithmetic Built-ins")
    e3 = Engine()
    e3.add_source("""
        num(1). num(2). num(3). num(4). num(5).
        doubled(X, Y) :- num(X), mul(X, 2, Y).
        squared(X, Y) :- num(X), mul(X, X, Y).
        big(X) :- num(X), X > 3.
    """)
    print("Doubled:", sorted(e3.relation("doubled")))
    print("Squared:", sorted(e3.relation("squared")))
    print("Big (>3):", sorted(e3.relation("big")))

    section("4. String Built-ins")
    e4 = Engine()
    e4.add_source("""
        name(hello). name(world).
        greeting(X, Y) :- name(X), concat(X, "!", Y).
        wordlen(X, N) :- name(X), strlen(X, 0, N).
    """)
    print("Greetings:", sorted(e4.relation("greeting")))
    print("Word lengths:", sorted(e4.relation("wordlen")))

    section("5. Type-Check Built-ins")
    e5 = Engine()
    e5.add_source("""
        val(42). val(3.14). val(hello). val(true).
        intval(X) :- val(X), is_int(X).
        strval(X) :- val(X), is_str(X).
    """)
    print("Integers:", sorted(e5.relation("intval")))
    print("Strings:", sorted(e5.relation("strval")))

    section("6. Aggregation (count, sum, min, max, avg)")
    e6 = Engine()
    e6.add_source("""
        employee(alice, eng, 90000).
        employee(bob, eng, 75000).
        employee(carol, eng, 85000).
        employee(dave, sales, 65000).
        employee(eve, sales, 70000).
    """)
    from datalog.parser import parse
    for rule_str in [
        "dept_count(Dept, N) :- employee(Name, Dept, Sal), count(Name, N).",
        "dept_total(Dept, T) :- employee(Name, Dept, Sal), sum(Sal, T).",
        "dept_min(Dept, M) :- employee(Name, Dept, Sal), min(Sal, M).",
        "dept_max(Dept, M) :- employee(Name, Dept, Sal), max(Sal, M).",
    ]:
        prog = parse(rule_str)
        e6.add_rule(prog.rules[0])

    print("Dept counts:", sorted(e6.relation("dept_count")))
    print("Dept totals:", sorted(e6.relation("dept_total")))
    print("Dept min:", sorted(e6.relation("dept_min")))
    print("Dept max:", sorted(e6.relation("dept_max")))

    section("7. JSON Export/Import")
    e7 = Engine()
    e7.add_source("""
        edge(a, b). edge(b, c).
        path(X, Y) :- edge(X, Y).
        path(X, Y) :- edge(X, Z), path(Z, Y).
    """)
    j = e7.to_json()
    print("Exported JSON (first 200 chars):")
    print(j[:200] + "...")
    e8 = Engine()
    e8.from_json(j)
    print(f"\nImported path relation: {sorted(e8.relation('path'))}")

    section("8. Introspection (explain + stats)")
    print(e7.explain("path"))
    print()
    stats = e7.stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")

    section("9. Output Formats")
    e9 = Engine()
    e9.add_source("edge(a, b). edge(a, c). edge(a, d).")
    results = e9.query("edge(a, Y)")
    print("--- binding format ---")
    print(format_results(results, "binding"))
    print("\n--- table format ---")
    print(format_results(results, "table"))
    print("\n--- json format ---")
    print(format_results(results, "json"))
    print("\n--- csv format ---")
    print(format_results(results, "csv"))

    print("\n" + "=" * 60)
    print("  Demo complete! All features working.")
    print("=" * 60)


if __name__ == "__main__":
    main()