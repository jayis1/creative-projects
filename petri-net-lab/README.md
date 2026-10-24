# Petri Net Lab

A dependency-free weighted place/transition Petri-net simulator and bounded reachability explorer. Places hold integer tokens; transitions consume and produce weighted arcs. Try it with `python3 -m unittest discover -s tests -v` (from this folder): five tests should pass.

## How it works

`PetriNet` validates the net structure and represents markings as immutable tuples in declared place order. `enabled` checks input arcs; `fire` applies a transition atomically. `simulate` advances a deterministic schedule (or selects the first enabled transition in declaration order) and returns the full marking trace. Breadth-first `reachable` explores each distinct marking once.

Both simulation steps and exploration state count are bounded. Reachability also applies a per-place token cap, preventing an unbounded net from generating unbounded counts. State-bound exhaustion raises a clear error instead of returning an incomplete result.

## Example

```python
from petri_net import PetriNet, Transition

net = PetriNet(
    {"ready": 1, "working": 0},
    (Transition("start", (("ready", 1),), (("working", 1),)),
     Transition("finish", (("working", 1),), (("ready", 1),)))
)
print(net.simulate(4))
print(net.reachable())
```

Output:

```text
[(1, 0), (0, 1), (1, 0), (0, 1), (1, 0)]
{(1, 0), (0, 1)}
```

`simulate(steps, schedule=None)` accepts an optional transition-name sequence. `reachable(max_states=10000, token_cap=100)` returns a set of markings. Unknown places, duplicate arcs, invalid weights, disabled firings, malformed markings, and invalid resource limits are rejected.

The distinctive focus is bounded exhaustive state-space exploration alongside a trace simulator, rather than a GUI workflow or a general-purpose workflow engine.

## Tests

Run `python3 -m unittest discover -s tests -v` from this directory. No third-party packages or network access are required.
