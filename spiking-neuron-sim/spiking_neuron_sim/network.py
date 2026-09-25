"""Small, deterministic event-driven spiking neural network simulator.

The simulator uses leaky integrate-and-fire neurons and a priority queue of
spike events. It is intentionally dependency-free so experiments are easy to
reproduce and inspect.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import heapq
import math
import random
from typing import Iterable


@dataclass(frozen=True)
class SimulationReport:
    """Immutable summary of one simulation run."""

    spikes: tuple[Spike, ...]
    until: float

    @property
    def count(self) -> int:
        return len(self.spikes)

    def firing_rates(self) -> dict[str, float]:
        if self.until <= 0:
            return {name: 0.0 for name in {spike.neuron for spike in self.spikes}}
        counts: dict[str, int] = {}
        for spike in self.spikes:
            counts[spike.neuron] = counts.get(spike.neuron, 0) + 1
        return {name: count * 1000.0 / self.until for name, count in counts.items()}


@dataclass(frozen=True, order=True)
class Spike:
    time: float
    neuron: str = field(compare=True)


@dataclass
class Neuron:
    name: str
    threshold: float = 1.0
    resting: float = 0.0
    reset: float = 0.0
    tau: float = 10.0
    refractory: float = 2.0
    potential: float = 0.0
    last_spike: float = -math.inf
    spikes: list[float] = field(default_factory=list)
    input_current: float = 0.0

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("neuron name must not be empty")
        if self.threshold <= self.reset or self.tau <= 0 or self.refractory < 0:
            raise ValueError("require threshold > reset, tau > 0, refractory >= 0")

    def decay(self, elapsed: float) -> None:
        if elapsed < 0:
            raise ValueError("time cannot move backwards")
        self.potential = self.resting + (self.potential - self.resting) * math.exp(-elapsed / self.tau)

    def receive(self, amount: float) -> None:
        if not math.isfinite(amount):
            raise ValueError("input must be finite")
        self.input_current += amount

    def advance(self, time: float) -> bool:
        if time < self.last_spike:
            raise ValueError("time cannot move backwards")
        if time - self.last_spike < self.refractory:
            self.input_current = 0.0
            return False
        self.decay(time - (self.last_spike if self.last_spike != -math.inf else time))
        self.potential += self.input_current
        self.input_current = 0.0
        if self.potential >= self.threshold:
            self.potential = self.reset
            self.last_spike = time
            self.spikes.append(time)
            return True
        return False


@dataclass(frozen=True)
class Connection:
    source: str
    target: str
    weight: float
    delay: float = 0.0
    plastic: bool = False

    def __post_init__(self) -> None:
        if self.delay < 0 or not math.isfinite(self.weight):
            raise ValueError("delay must be non-negative and weight finite")
        if self.source == self.target:
            raise ValueError("self-connections are not supported")


@dataclass(frozen=True)
class Stimulus:
    time: float
    neuron: str
    amount: float

    def __post_init__(self) -> None:
        if self.time < 0 or not math.isfinite(self.amount):
            raise ValueError("stimulus time must be non-negative and amount finite")


class LIFNetwork:
    """A network with reproducible simulation and optional pair-based STDP."""

    def __init__(self, *, seed: int | None = None) -> None:
        self.neurons: dict[str, Neuron] = {}
        self.connections: list[Connection] = []
        self._outgoing: dict[str, list[Connection]] = {}
        self.rng = random.Random(seed)

    def add_neuron(self, neuron: Neuron | str, **kwargs: float) -> Neuron:
        value = neuron if isinstance(neuron, Neuron) else Neuron(neuron, **kwargs)
        if value.name in self.neurons:
            raise ValueError(f"duplicate neuron: {value.name}")
        self.neurons[value.name] = value
        self._outgoing[value.name] = []
        return value

    def connect(self, source: str, target: str, weight: float, *, delay: float = 0.0, plastic: bool = False) -> Connection:
        self._require_neuron(source)
        self._require_neuron(target)
        edge = Connection(source, target, weight, delay, plastic)
        self.connections.append(edge)
        self._outgoing[source].append(edge)
        return edge

    def stimulate(self, stimuli: Iterable[Stimulus], until: float) -> list[Spike]:
        """Run until ``until`` milliseconds and return spikes in time order."""
        if until < 0 or not math.isfinite(until):
            raise ValueError("until must be a finite non-negative number")
        queue: list[tuple[float, int, str, float, str | None]] = []
        sequence = 0
        for item in stimuli:
            self._require_neuron(item.neuron)
            if item.time > until:
                continue
            heapq.heappush(queue, (item.time, sequence, item.neuron, item.amount, None))
            sequence += 1
        spikes: list[Spike] = []
        while queue:
            time, _, target, amount, source = heapq.heappop(queue)
            if time > until:
                break
            neuron = self.neurons[target]
            neuron.receive(amount)
            if neuron.advance(time):
                event = Spike(time, target)
                spikes.append(event)
                for edge in self._outgoing[target]:
                    arrival = time + edge.delay
                    if arrival <= until:
                        heapq.heappush(queue, (arrival, sequence, edge.target, edge.weight, target))
                        sequence += 1
                self._apply_stdp(target, time)
        return spikes

    def _apply_stdp(self, source: str, time: float) -> None:
        """Pair-based STDP: recent pre/post pairs adjust plastic edges."""
        for edge in self.connections:
            if not edge.plastic:
                continue
            target = self.neurons[edge.target]
            source_neuron = self.neurons[source]
            if edge.source == source and target.spikes:
                dt = target.spikes[-1] - time
                if 0 < dt <= 20:
                    object.__setattr__(edge, "weight", edge.weight - 0.01 * math.exp(-dt / 20))
            if edge.target == source and source_neuron.spikes:
                dt = time - source_neuron.spikes[-1]
                if 0 < dt <= 20:
                    object.__setattr__(edge, "weight", edge.weight + 0.01 * math.exp(-dt / 20))

    def reset(self) -> None:
        for neuron in self.neurons.values():
            neuron.potential = neuron.reset
            neuron.last_spike = -math.inf
            neuron.spikes.clear()
            neuron.input_current = 0.0

    def simulate(self, stimuli: Iterable[Stimulus], until: float) -> SimulationReport:
        """Run a simulation and return spikes plus derived metrics."""
        return SimulationReport(tuple(self.stimulate(stimuli, until)), until)

    def add_population(self, prefix: str, count: int, **kwargs: float) -> list[Neuron]:
        """Create ``count`` neurons named prefix-0, prefix-1, ..."""
        if count < 0:
            raise ValueError("population count must be non-negative")
        return [self.add_neuron(f"{prefix}-{i}", **kwargs) for i in range(count)]

    def connect_all_to_all(self, sources: Iterable[str], targets: Iterable[str], weight: float, *, delay: float = 0.0, plastic: bool = False) -> int:
        """Connect every source to every target, returning edge count."""
        source_list, target_list = list(sources), list(targets)
        created = 0
        for source in source_list:
            for target in target_list:
                if source != target:
                    self.connect(source, target, weight, delay=delay, plastic=plastic)
                    created += 1
        return created

    def export_state(self) -> dict[str, object]:
        """Return a JSON-serializable snapshot of topology and neuron state."""
        return {
            "neurons": [{"name": n.name, "threshold": n.threshold, "resting": n.resting,
                         "reset": n.reset, "tau": n.tau, "refractory": n.refractory}
                        for n in self.neurons.values()],
            "connections": [{"source": c.source, "target": c.target, "weight": c.weight,
                             "delay": c.delay, "plastic": c.plastic} for c in self.connections],
        }

    @classmethod
    def from_state(cls, state: dict[str, object], *, seed: int | None = None) -> "LIFNetwork":
        """Rebuild a network from :meth:`export_state` output with validation."""
        if not isinstance(state.get("neurons"), list) or not isinstance(state.get("connections"), list):
            raise ValueError("state must contain neuron and connection lists")
        network = cls(seed=seed)
        for item in state["neurons"]:
            if not isinstance(item, dict):
                raise ValueError("each neuron must be an object")
            data = {key: item[key] for key in ("threshold", "resting", "reset", "tau", "refractory") if key in item}
            network.add_neuron(str(item["name"]), **data)
        for item in state["connections"]:
            if not isinstance(item, dict):
                raise ValueError("each connection must be an object")
            network.connect(str(item["source"]), str(item["target"]), float(item["weight"]),
                            delay=float(item.get("delay", 0.0)), plastic=bool(item.get("plastic", False)))
        return network

    def _require_neuron(self, name: str) -> None:
        if name not in self.neurons:
            raise KeyError(f"unknown neuron: {name}")
