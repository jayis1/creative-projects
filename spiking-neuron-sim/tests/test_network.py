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




def test_population_report_and_state_roundtrip():
    net = LIFNetwork(seed=3)
    cells = net.add_population("cell", 2, threshold=0.5)
    assert [cell.name for cell in cells] == ["cell-0", "cell-1"]
    assert net.connect_all_to_all(["cell-0"], ["cell-1"], 0.5, delay=1.0) == 1
    report = net.simulate([Stimulus(0, "cell-0", 1.0)], until=2)
    assert report.count == 2
    assert report.firing_rates()["cell-0"] == 500.0
    restored = LIFNetwork.from_state(net.export_state())
    assert restored.export_state() == net.export_state()


def test_invalid_inputs_are_rejected():
    with pytest.raises(ValueError):
        Neuron("bad", tau=0)
    with pytest.raises(ValueError):
        Stimulus(-1, "n", 1)
    with pytest.raises(ValueError):
        Stimulus(0, "n", math.inf)
