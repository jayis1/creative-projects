# Explicit-State CTL Model Checker

A stdlib-only model checker for finite transition systems. It evaluates Computation Tree Logic (CTL) formulas by fixed-point iteration, provides reachable-state exploration and shortest counterexample/witness traces, and includes a runnable protocol example.

Intended user: a student or engineer checking small state-machine protocols without an external solver. In 60 seconds, run the included producer/receiver model and check whether delivery is possible. Reopen it to explore safety and liveness properties of your own finite systems.

## How it works

States are hashable Python values, transitions form a directed graph, and each state carries a set of atomic propositions. Reachable states are discovered by breadth-first search. `EX`/`AX` evaluate next-state predicates; `EF`/`AF` use least fixed points; `EG`/`AG` use greatest fixed points. Boolean operators compose formulas. Deadlocks follow standard totalization-free semantics: `EX` is false and `AX`, `AF`, and `AG` are vacuously true at a deadlock; `EF`/`EG` depend on their respective fixed points.

## Usage

From this directory:

```sh
python3 -m modelcheck.cli
python3 -m unittest discover -s tests -v
```

Python 3.10+; no dependencies. Python API:

```python
from modelcheck import Formula as F, TransitionSystem, check
system = TransitionSystem.build("idle", {"idle": ["done"], "done": ["done"]},
                                {"done": ["delivered"]})
assert check(system, F.EF(F.atom("delivered")))
```

The demo prints a finite protocol graph, a liveness check, and its shortest witness trace. This implementation is intended for small explicit-state systems; state-space growth is exponential in the number of modeled components.

## Known Issues (Resolved)

Initial tests cover cycles, deadlocks, boolean composition, next-state checks, and shortest traces; the dedicated bug-hunt phase will record verified findings.
