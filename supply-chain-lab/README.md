# Supply Chain Lab

Supply Chain Lab is for operations students and planners who want to see how reorder policies and lead times create shortages and inventory in a small, reproducible multi-echelon network—without needing a commercial planning suite. It runs offline on JSON demand traces and emits a machine-readable report.

## Model

Each node has on-hand stock, outstanding replenishment orders, a lead time, a reorder point, and an order-up-to target. At each simulated day, due orders arrive, demand propagates from the customer-facing node upstream, and periodic inventory review places orders based on inventory position. The simulator reports service shortfalls, stock-days, units ordered, and pipeline inventory per node.

## Usage

```sh
python3 main.py examples/basic.json
python3 main.py examples/basic.json --output report.json
python3 main.py examples/basic.json --format csv --output report.csv
python3 -m unittest discover -s tests -v
```

A scenario contains named nodes ordered supplier-to-customer and daily customer demand:

```json
{"seed": 17, "demand": [3, 5, 2], "nodes": [
  {"name":"warehouse", "lead_time":2, "reorder_point":4, "order_up_to":12, "stock":8},
  {"name":"store", "lead_time":1, "reorder_point":3, "order_up_to":9, "stock":5}
]}
```

The output is JSON with one daily record and one summary per node. All quantities are integer units; lead times are whole simulated days. No external dependencies or network access are required.

## Limits and assumptions

This is an educational deterministic policy model, not a demand forecaster. Input traces are finite and explicitly supplied; all supply is unconstrained at the upstream boundary. The seed is reserved for future stochastic demand modes.
