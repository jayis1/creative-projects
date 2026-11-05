# Bayes Net

A dependency-free exact-inference toolkit for finite Bayesian networks with binary variables. Define a directed acyclic graph in parent-before-child order, provide each node's conditional probability table (CPT), then compute posterior distributions, partial joint probabilities, or the maximum a posteriori (MAP) assignment.

## How it works

Each full assignment receives the product of its local CPT probabilities. Inference enumerates assignments compatible with evidence, sums weights and normalizes the requested variable's outcomes. `joint_probability` marginalizes unspecified variables; `map_assignment` searches for the most likely complete state. Enumeration is transparent but exponential, so inference and MAP have configurable assignment limits (default 1,000,000).

## Usage

```python
from bayes_net import BayesNet

net = BayesNet()
net.add_node("rain", [], {(): 0.2})
net.add_node("sprinkler", ["rain"], {(True,): 0.01, (False,): 0.4})
net.add_node("wet", ["rain", "sprinkler"], {
    (True, True): 0.99, (True, False): 0.8,
    (False, True): 0.9, (False, False): 0.0,
})
print(net.distribution("rain", {"wet": True}))
print(net.joint_probability({"rain": True, "wet": True}))
print(net.map_assignment({"wet": True}))
```

Inputs are validated for names, Boolean assignments, complete CPT rows, finite probabilities in [0, 1], and impossible evidence. Run tests with `python3 -m unittest -v`; no third-party dependencies are required.
