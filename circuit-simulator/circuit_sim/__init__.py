"""
circuit-simulator: A digital circuit simulator with propagation delays,
composite circuits, oscilloscope output, and a circuit description language.
"""

from .core import Signal, Wire, Bus
from .gates import (
    AndGate, OrGate, NotGate, XorGate, NandGate, NorGate, XnorGate,
    BufferGate, TriStateBuffer, MultiInputGate,
)
from .sequential import SRLatch, DLatch, DFlipFlop, JKFlipFlop, TFlipFlop, Clock
from .circuit import Circuit
from .simulator import Simulator, BreakpointHit, Stimulus
from .cdl import parse_cdl
from .scope import Oscilloscope
from .analyze import TruthTable, CircuitStats
from .presets import (
    build_sr_latch_circuit,
    build_d_flipflop_counter,
    build_alu_1bit,
    build_register,
    build_ring_oscillator,
    build_priority_encoder,
)

__version__ = "1.1.0"
__all__ = [
    "Signal", "Wire", "Bus",
    "AndGate", "OrGate", "NotGate", "XorGate", "NandGate", "NorGate", "XnorGate",
    "BufferGate", "TriStateBuffer", "MultiInputGate",
    "SRLatch", "DLatch", "DFlipFlop", "JKFlipFlop", "TFlipFlop", "Clock",
    "Circuit", "Simulator", "BreakpointHit", "Stimulus",
    "parse_cdl", "Oscilloscope",
    "TruthTable", "CircuitStats",
    "build_sr_latch_circuit", "build_d_flipflop_counter",
    "build_alu_1bit", "build_register",
    "build_ring_oscillator", "build_priority_encoder",
]