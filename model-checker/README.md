# Explicit-State CTL Model Checker

A stdlib-only model checker for finite transition systems. It evaluates Computation Tree Logic (CTL) formulas by fixed-point iteration, explores reachable states, and provides shortest witness traces for reachability checks.

Intended user: a student or engineer checking small state-machine protocols without an external solver. In 60 seconds, run the included producer/receiver model and check whether delivery is possible. Reopen it to explore safety and liveness properties of your own finite systems.

## How it works

States are hashable Python values, transitions form a directed graph, and each state carries a set of atomic propositions. Reachability and witness traces use breadth-first search. `EX`/`AX` evaluate next-state predicates; `EF`/`AF` use least fixed points; `EG`/`AG` use greatest fixed points; `E[φ U ψ]` and `A[φ U ψ]` evaluate existential and universal until. Boolean operators compose formulas.

Deadlock convention: universal next-step checks are vacuously true when there are no successors, existential next-step checks are false, and the fixed-point temporal operators use that same empty-successor quantification. This explicit convention makes results deterministic for partial transition systems.

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
assert check(system, F.EU(F.neg(F.atom("delivered")), F.atom("delivered")))
```

The demo prints a finite protocol graph, liveness/safety checks, and the shortest delivery trace. Intended for small explicit-state systems; state-space growth is exponential in the number of modeled components.

## Known Issues (Resolved)

Initial and enhanced suites cover cycles, deadlocks, boolean composition, next-state checks, until formulas, and shortest traces. The dedicated bug-hunt phase records any verified findings.
