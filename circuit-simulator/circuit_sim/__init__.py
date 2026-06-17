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
from .export import (
    circuit_to_dict,
    circuit_to_json,
    circuit_from_json,
    circuit_to_dot,
    circuit_to_ascii,
)
from .waveform import compare_traces, analyze_trace, format_trace_analysis
from .config import SimConfig

__version__ = "2.0.0"
__all__ = [
    # Core
    "Signal", "Wire", "Bus",
    # Gates
    "AndGate", "OrGate", "NotGate", "XorGate", "NandGate", "NorGate", "XnorGate",
    "BufferGate", "TriStateBuffer", "MultiInputGate",
    # Sequential
    "SRLatch", "DLatch", "DFlipFlop", "JKFlipFlop", "TFlipFlop", "Clock",
    # Circuit & Simulator
    "Circuit", "Simulator", "BreakpointHit", "Stimulus",
    # CDL & Analysis
    "parse_cdl", "Oscilloscope",
    "TruthTable", "CircuitStats",
    # Presets
    "build_sr_latch_circuit", "build_d_flipflop_counter",
    "build_alu_1bit", "build_register",
    "build_ring_oscillator", "build_priority_encoder",
    # Export
    "circuit_to_dict", "circuit_to_json", "circuit_from_json",
    "circuit_to_dot", "circuit_to_ascii",
    # Waveform Analysis
    "compare_traces", "analyze_trace", "format_trace_analysis",
    # Config
    "SimConfig",
]