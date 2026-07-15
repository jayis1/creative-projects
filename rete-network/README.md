# Rete Network — Forward-Chaining Rule Inference Engine

A from-scratch implementation of the classic **Rete algorithm** (Rete I) for
efficient pattern matching in forward-chaining production-rule systems.

## Overview

Rete (Latin for *net*) is the algorithm at the heart of production-rule
systems like CLIPS, Jess, and Drools.  Instead of re-scanning all facts every
cycle, it compiles rules into a **network** of nodes that incrementally
maintains the set of matching rule instantiations as facts are asserted and
retracted.

### Network structure

```
Fact ─▶ Alpha net (one-input) ─▶ Join / Beta net (two-input) ─▶ Production nodes
         type + field tests       variable-binding joins          (rules → agenda)
```

* **Alpha nodes** — filter single facts by type and intra-fact tests
  (constant equality, variable binding, arbitrary predicates).
* **Join nodes** — combine partial instantiations from two parents using
  inter-fact variable-consistency checks.
* **Production nodes** — leaf nodes that collect complete instantiations for
  a rule and feed the agenda.
* **Negated conditions** — supported via negated conjunctive conditions
  (NCC): a rule fires only when *no* fact matches the negated pattern.

## Features

- Pure Python, zero dependencies
- `Fact` working-memory elements with structural equality
- `Rule` definitions with ordered conditions + actions
- `Var` / `Const` pattern terms for variable binding and constant tests
- Arbitrary intra-fact predicates
- Negated conditions (`negated=True`)
- Alpha-node sharing across rules with overlapping patterns
- Incremental assertion / retraction
- Five conflict-resolution strategies: FIFO, LIFO, Priority, Recent, Refraction
- Infinite-loop detection via `max_steps`
- Agenda inspection API

## Usage

```python
from rete import Engine, Fact, Rule, Condition, Var, Const

eng = Engine()

# A simple greeting rule
eng.add_rule(Rule(
    name="greet",
    conditions=[Condition("person", name=Var("n"))],
    actions=[lambda b, e: print(f"Hello, {b['n']}!")],
))

eng.assert_fact(Fact("person", name="Alice"))
eng.assert_fact(Fact("person", name="Bob"))
eng.run()
# Hello, Alice!
# Hello, Bob!
```

### Multi-condition join

```python
# "If person ?x likes person ?y and ?y likes ?x, they are friends."
eng.add_rule(Rule(
    name="friends",
    conditions=[
        Condition("likes", a=Var("x"), b=Var("y")),
        Condition("likes", a=Var("y"), b=Var("x")),
    ],
    actions=[lambda b, e: e.assert_fact(Fact("friends", a=b["x"], b=b["y"]))],
))
```

### Negated condition

```python
# "If someone is a person and NOT banned, they can enter."
eng.add_rule(Rule(
    name="allow-entry",
    conditions=[
        Condition("person", name=Var("n")),
        Condition("banned", name=Var("n"), negated=True),
    ],
    actions=[lambda b, e: e.assert_fact(Fact("allowed", name=b["n"]))],
))
```

### Predicate tests

```python
Condition("person", age=Var("a"),
          predicate=lambda fact, b: b["a"] >= 18)
```

## Installation

```bash
cd rete-network
pip install -e .
```

## License

MIT