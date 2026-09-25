"""Command-line demo for the spiking neuron simulator."""
from __future__ import annotations
import argparse
from .network import LIFNetwork, Stimulus


def main() -> int:
    parser = argparse.ArgumentParser(description="simulate a small LIF spiking network")
    parser.add_argument("--until", type=float, default=20.0, help="simulation horizon in milliseconds")
    args = parser.parse_args()
    net = LIFNetwork(seed=7)
    net.add_neuron("input", threshold=1.0, tau=10.0)
    net.add_neuron("output", threshold=0.8, tau=8.0)
    net.connect("input", "output", 0.55, delay=1.0)
    stimuli = [Stimulus(t, "input", 1.0) for t in (0.0, 5.0, 10.0)]
    spikes = net.stimulate(stimuli, args.until)
    print("spikes:")
    for spike in spikes:
        print(f"  {spike.time:5.1f} ms  {spike.neuron}")
    print(f"total={len(spikes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
