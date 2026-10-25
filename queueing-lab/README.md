# Queueing Lab

A standard-library, reproducible discrete-event simulator for open service networks. Useful for exploring how staffing and probabilistic rework affect waiting lines; run the example in seconds and get a JSON report.

```sh
python3 queueing_lab.py --customers 500 --seed 7
```

## How it works

Each station has one or more parallel exponential-service servers. A heap processes service completions in timestamp order; categorical routing sends each finished customer to another station or out of the network. Routing may form cycles (for example, inspection to repair and back), and the event limit prevents a runaway simulation. This is a finite batch model: all external arrivals are scheduled up front, and simulated time starts at the first arrival.

The output reports entered/completed counts, event count, makespan, and per-station visits, average queue wait, utilization, and throughput. A fixed seed makes the complete report reproducible.

## Configure a network

```python
from queueing_lab import QueueingNetwork, Route, Station

stations = [Station("counter", servers=2, mean_service=1.2)]
routes = [Route("counter", None, probability=1.0)]  # None exits the system
report = QueueingNetwork(stations, routes, seed=42).run(
    customers=100, interarrival_mean=1.5
)
print(report["stations"]["counter"])
```

Each station must have outgoing routes whose nonnegative probabilities sum to one. Service and interarrival means must be positive finite values. Limits: 64 stations, 128 servers per station, 100,000 customers and 2,000,000 processed events. No third-party dependencies or network access are required.

## Load a JSON network

The included example defines the same recirculating inspection/repair model:

```sh
python3 queueing_lab.py --network example-network.json --customers 500 --seed 7 --interarrival-mean 1.5
```

JSON files have `stations` and `routes` arrays matching the Python dataclasses; files larger than 1 MiB are rejected. Loading parses data only and never executes it.

## Tests

```sh
python3 -m unittest discover -s queueing-lab -v
```

## Novelty

Unlike a single-queue textbook demonstration, this small network models probabilistic recirculation between staffed stations and surfaces station-level utilization and waiting metrics from the same event trace.

## Author

jayis1
