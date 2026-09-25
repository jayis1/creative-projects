"""Phase 1 behavior tests."""
import math
import pytest
from spiking_neuron_sim import LIFNetwork, Neuron, Stimulus


def test_neuron_fires_and_resets():
    neuron = Neuron("n", threshold=1.0)
    neuron.receive(1.2)
    assert neuron.advance(0.0)
    assert neuron.potential == 0.0
    assert neuron.spikes == [0.0]


def test_network_delivers_delayed_spike():
    net = LIFNetwork()
    net.add_neuron("a")
    net.add_neuron("b", threshold=0.5)
    net.connect("a", "b", 0.6, delay=2.0)
    spikes = net.stimulate([Stimulus(0.0, "a", 1.0)], until=5.0)
    assert [(s.neuron, s.time) for s in spikes] == [("a", 0.0), ("b", 2.0)]


def test_invalid_inputs_are_rejected():
    with pytest.raises(ValueError):
        Neuron("bad", tau=0)
    with pytest.raises(ValueError):
        Stimulus(-1, "n", 1)
    with pytest.raises(ValueError):
        Stimulus(0, "n", math.inf)
