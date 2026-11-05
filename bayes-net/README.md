# Bayes Net

A dependency-free exact-inference toolkit for finite Bayesian networks with binary variables. Define a directed acyclic graph in parent-before-child order, provide a conditional probability table (CPT) for each node, then compute posterior distributions by exhaustive enumeration.

## How it works

Each full assignment receives the product of its local CPT probabilities. Inference sums those weights over assignments compatible with the supplied evidence and normalizes the requested variable's two outcomes. This is transparent and useful for small models; runtime grows exponentially with the number of unobserved variables.

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
```

Run tests with `python3 -m unittest -v` from this directory. There are no third-party dependencies.
